> Packaging note: the initial pre-localization run is described as historical evidence below. Only the unchanged localized retest artifacts and captured outputs are included here. Paths in textual logs are normalized; `$SKILL_ROOT`, `$EVAL_ROOT`, and `$PYTHON` stand for the skill directory, isolated evaluation directory, and installed Python executable.

# Forward evaluation: `wiki-interest`

Дата виконання: 2026-09-22. Модель: `gpt-5.6-luna`.

## Запит і припущення

Виконано реалістичний запит українською: оцінити, чи зростає інтерес до астрономії в україномовній Wikipedia за останні два повні роки, і підготувати короткий PDF-звіт. Обрано Wikidata Q333 (астрономія), 24 повні UTC-місяці (`2024-09`—`2026-08`), метрику `user / all-access / monthly`, поріг росту 10% і мінімум 1 000 переглядів у кожному річному вікні — відповідно до skill.

Після цього виконано follow-up: додано польську Wikipedia (`pl`) і змінено лише поріг росту на 20%. Період, QID, мінімум переглядів та інші припущення залишено без змін.

## Точні команди та результати

Команди виконувалися з каталогу `outputs/wiki-interest` із Python `$PYTHON`; кеш і всі звіти записано лише в цю evaluation-директорію.

```sh
mkdir -p $EVAL_ROOT
$PYTHON scripts/wiki_interest.py --help
$PYTHON scripts/wiki_interest.py search --query 'astronomy' --language uk --cache $EVAL_ROOT/cache
$PYTHON scripts/wiki_interest.py plan --topic 'Astronomy: topic attention' --qid Q333 --languages uk --months 24 --output $EVAL_ROOT/astronomy-uk-plan.json --cache $EVAL_ROOT/cache
$PYTHON scripts/wiki_interest.py run --plan $EVAL_ROOT/astronomy-uk-plan.json --out $EVAL_ROOT/astronomy-uk --cache $EVAL_ROOT/cache
$PYTHON scripts/wiki_interest.py verify --directory $EVAL_ROOT/astronomy-uk
$PYTHON scripts/wiki_interest.py plan --topic 'Astronomy: topic attention' --qid Q333 --languages uk pl --months 24 --growth-threshold 20 --output $EVAL_ROOT/astronomy-uk-pl-threshold20-plan.json --cache $EVAL_ROOT/cache
$PYTHON scripts/wiki_interest.py run --plan $EVAL_ROOT/astronomy-uk-pl-threshold20-plan.json --out $EVAL_ROOT/astronomy-uk-pl-threshold20 --cache $EVAL_ROOT/cache
$PYTHON scripts/wiki_interest.py verify --directory $EVAL_ROOT/astronomy-uk-pl-threshold20
```

Перший пошук повернув Q333 як природничу науку; план розв'язав його до поточної статті `Астрономія` (`uk`, revision `48432874`). Перша перевірка: `verified: true`, 7 файлів, snapshot SHA-256 `9b67f0325ad814b3f2b568f85d613535a491394417a45c81590fab44918a8ad7`.

Результат першого звіту: 16 614 базових переглядів проти 6 708 останніх (`-59.62%` raw), частка в мовному проєкті змінилася на `-46.43%`, 1/12 позитивних matched-months, статус `consistent_decline`; leave-one-pair-out raw range `-61.40%…-57.52%`, share range `-48.46%…-43.17%`.

Follow-up план знайшов ту саму українську статтю та польську `Astronomia` (`pl`, revision `78177175`). Друга перевірка: `verified: true`, 7 файлів, snapshot SHA-256 `9690b46c4f5922303bf52828d5cbac81490fc2bf5359b9805e15281df1428d5e`.

Результат follow-up: `uk` лишилася `consistent_decline` (`-59.62%` raw, `-46.43%` share); `pl` має 20 477 базових і 17 175 останніх переглядів (`-16.13%` raw), share `-8.01%`, 1/12 позитивних matched-months, статус `mixed_or_flat`. Отже жодна мова не пройшла поріг росту 20%.

## Відповідь українською, заснована на джерелах

За виміром pageviews інтерес до статті про астрономію в україномовній Wikipedia не зріс: за останні 12 повних місяців проти попередніх 12 перегляди зменшилися на 59,6%, а нормалізована частка — на 46,4%. У польськомовній Wikipedia падіння було меншим, але також не було росту: -16,1% raw і -8,0% share. Дані повні для всіх 24 місяців.

Довіряти цьому можна як відтворюваному описовому сигналу уваги до поточних канонічних статей: збережені оригінальні API-відповіді, URL, час отримання, хеші й детермінований `verify`. Не можна трактувати результат як кількість унікальних людей, попит на курс, готовність платити, причинний тренд чи статистичну впевненість. Wikipedia-мова не дорівнює країні або ринку; перенаправлення та історичні перейменування не реконструйовані. Практичний висновок — не запускати курс лише на цьому сигналі; додати інтерв'ю, пошуковий намір або малий demand experiment.

Джерела: Wikimedia Pageview API та документація визначень pageviews, наведені в кожному `report.md`; статті `https://uk.wikipedia.org/wiki/Астрономія`, `https://pl.wikipedia.org/wiki/Astronomia`, сутність `https://www.wikidata.org/wiki/Q333`.

## Помилки та usability

- Помилок під час пошуку, планування, виконання та `verify` не було; мережеві виклики успішні.
- Окрема команда `/usr/bin/pdfinfo ...` завершилася помилкою `no such file or directory`; це лише відсутня локальна утиліта інспекції PDF, не помилка генерації. `file` підтвердив, що обидва PDF — односторінкові PDF 1.4.
- Skill згенерував звіти й PDF англійськими фіксованими підписами, хоча запит українською; українські назви статей збережені, але локалізованого PDF немає. Це помітна usability-проблема для кінцевого україномовного читача.
- Вимога “короткий PDF-звіт” виконана: кожен запуск створив односторінковий `report.pdf`; follow-up створив окремий порівняльний PDF, не перезаписавши перший.

## Артефакти

- Початковий PDF: `astronomy-uk/report.pdf`; текстовий звіт: `astronomy-uk/report.md`.
- Порівняльний PDF: `astronomy-uk-pl-threshold20/report.pdf`; текстовий звіт: `astronomy-uk-pl-threshold20/report.md`.
- Відтворювані докази: відповідні `snapshot.json`, `sources.json`, `analysis.json`, `monthly.csv`, `manifest.json`, `chart.png` та два plan JSON.

## Retest: локалізовані PDF і chart (2026-09-22)

Після оновлення skill повторено обидва запуски в нових каталогах із `--report-language uk` і українським заголовком `Астрономія: увага до теми`. Початкові докази не перезаписувалися.

- [Локалізований український PDF]($EVAL_ROOT/astronomy-uk-localized/report.pdf)
- [Локалізований українсько-польський PDF]($EVAL_ROOT/astronomy-uk-pl-localized-threshold20/report.pdf)
- [Український run stdout]($EVAL_ROOT/localized-run-uk.stdout.json)
- [Follow-up run stdout]($EVAL_ROOT/localized-run-uk-pl.stdout.json)
- [pypdf PDF-перевірка]($EVAL_ROOT/localized-pdf-pypdf-check.json)

Усі plan/run/verify команди завершилися з exit code 0; усі stderr-файли порожні. `pypdf` підтвердив для обох PDF одну сторінку, український заголовок, українські підписи `МОВА` і `СИГНАЛ` та український текст `Жодна мова`. Перевірка має exit code 0.

Незмінені дані follow-up були повністю взяті з кешу: plan — `cache_hits: 3`, `network_requests: 0`; run — `cache_hits: 12`, `network_requests: 0`. Результати збігаються з попереднім запуском: `uk` -59,62% raw / -46,43% share, `pl` -16,13% / -8,01%.

Localized run stdout reports `research_shortlist: []`; verify passed for both new directories with 7 files each. Remaining limitation: `report.md` remains in the skill's fixed English format, while the requested PDF and chart labels are localized in Ukrainian. No functional or data-validation failures remain.
