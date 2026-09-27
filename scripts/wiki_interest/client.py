"""Bounded, cached, read-only Wikimedia HTTP access."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


class ResearchError(Exception):
    """An actionable user-facing error, without a traceback by default."""


def utc_now():
    return datetime.now(UTC).isoformat()


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def write_json(path: Path, value):
    """Atomic replace also makes concurrent independent cache readers safe."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".writing-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def validate_url(url):
    parsed = urlparse(url)
    host = parsed.hostname or ""
    allowed = host in {"wikimedia.org", "www.wikidata.org"} or re.fullmatch(
        r"[a-z][a-z0-9-]{0,24}\.wikipedia\.org", host
    )
    if parsed.scheme != "https" or not allowed or parsed.port not in (None, 443):
        raise ResearchError("Only HTTPS requests to Wikimedia data hosts are allowed")
    if parsed.username or parsed.password:
        raise ResearchError("Credentials in source URLs are not allowed")


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Client:
    def __init__(self, cache: Path, *, offline=False, refresh=False, ttl=86400):
        if offline and refresh:
            raise ResearchError("--offline and --refresh cannot be combined")
        self.cache = cache
        self.offline = offline
        self.refresh = refresh
        self.ttl = ttl
        self.sources = {}
        self.hits = 0
        self.requests = 0
        self._last_request = 0.0
        self._opener = build_opener(SafeRedirect())

    def get(self, url, *, allow_not_found=False):
        validate_url(url)
        key = hashlib.sha256(url.encode()).hexdigest()
        path = self.cache / f"{key}.json"
        envelope = None
        if path.exists() and not self.refresh:
            try:
                candidate = json.loads(path.read_text(encoding="utf-8"))
                valid = (
                    candidate["url"] == url
                    and digest(candidate["data"]) == candidate["sha256"]
                    and candidate["status"] in (200, 404)
                )
                age = time.time() - datetime.fromisoformat(candidate["fetched_at"]).timestamp()
                if valid and (self.offline or 0 <= age < self.ttl):
                    envelope = candidate
                    self.hits += 1
            except (ValueError, KeyError, TypeError):
                pass
        if envelope is None:
            if self.offline:
                raise ResearchError(f"Offline cache missing or corrupt: {url}")
            data, status = self._fetch(url, allow_not_found=allow_not_found)
            envelope = dict(
                url=url, fetched_at=utc_now(), sha256=digest(data), status=status, data=data
            )
            write_json(path, envelope)
        if envelope["status"] == 404 and not allow_not_found:
            raise ResearchError(f"Source returned HTTP 404: {url}")
        self.sources[key] = envelope
        return envelope["data"]

    def _fetch(self, url, *, allow_not_found):
        user_agent = os.environ.get(
            "WIKI_INTEREST_USER_AGENT", "WikiInterestSkill/1.0 (research; Python urllib)"
        )
        for attempt in range(4):
            time.sleep(max(0, 0.15 - (time.monotonic() - self._last_request)))
            self._last_request = time.monotonic()
            self.requests += 1
            retry_after = None
            try:
                request = Request(
                    url, headers={"User-Agent": user_agent, "Accept": "application/json"}
                )
                with self._opener.open(request, timeout=25) as response:
                    raw = response.read(8_000_001)
                if len(raw) > 8_000_000:
                    raise ResearchError("Source response exceeds 8 MB limit")
                try:
                    data = json.loads(raw)
                except (ValueError, UnicodeError) as exc:
                    raise ResearchError("Source returned invalid JSON") from exc
                if not isinstance(data, dict):
                    raise ResearchError("Source returned an unexpected JSON structure")
                if "error" in data:
                    raise ResearchError(
                        f"Wikimedia API error: {data['error'].get('code', 'unknown')}"
                    )
                return data, 200
            except HTTPError as exc:
                if exc.code == 404 and allow_not_found:
                    return {"items": []}, 404
                if exc.code not in (429, 500, 502, 503, 504):
                    raise ResearchError(f"Source HTTP {exc.code}: {url}") from exc
                retry_after = exc.headers.get("Retry-After")
                error = f"HTTP {exc.code}"
            except (URLError, TimeoutError, OSError) as exc:
                error = type(exc).__name__
            if attempt == 3:
                raise ResearchError(f"Source unavailable after 4 attempts ({error}): {url}")
            delay = 2**attempt
            if retry_after:
                try:
                    delay = float(retry_after)
                except ValueError:
                    try:
                        delay = parsedate_to_datetime(retry_after).timestamp() - time.time()
                    except (ValueError, TypeError, OverflowError):
                        delay = 2**attempt
                if delay > 30:
                    raise ResearchError(f"Source requested Retry-After {delay:.0f}s; retry later")
            time.sleep(max(0, delay))
        raise AssertionError("unreachable")

    def api(self, wiki_language=None, **params):
        host = f"{wiki_language}.wikipedia.org" if wiki_language else "www.wikidata.org"
        params.update(format="json", formatversion=2)
        return self.get(f"https://{host}/w/api.php?{urlencode(sorted(params.items()))}")
