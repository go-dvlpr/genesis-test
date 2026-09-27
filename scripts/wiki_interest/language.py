"""Human-facing brief labels. Machine-readable fields stay stable in English."""

TEXT = {
    "en": {
        "badge": "WIKI INTEREST  /  RESEARCH BRIEF",
        "period": "Complete UTC months",
        "headings": ["LANG", "12M VIEWS", "RAW YoY", "SHARE YoY", "SIGNAL"],
        "chart_titles": ["Article attention", "Share of language-section traffic"],
        "chart_labels": ["Average views / day", "Article views / million project views"],
        "shortlist": "Research next: {languages}. These meet the stated growth screen. Validate learning intent and willingness to pay with interviews and a small demand test.",
        "empty": "No language has a confirmed growth signal under the stated screen. Do not prioritize a launch from these pageviews alone. Review article scope and combine this evidence with user interviews or a small demand test.",
        "criteria": "Growth screen: raw and share growth >= {threshold}%; at least 9 positive matched months; annual volume >= {volume}; direction survives each month-pair exclusion. These are screening rules, not confidence levels.",
        "scope": "Scope",
        "sensitivity": "Raw annual change when each matched month pair is excluded",
        "missing": "no linked article",
        "basket": "{count} topics; full list in report.md",
        "caveat": "Pageviews are attention, not customers. Languages are not countries. Current titles exclude redirect and historical-title traffic; article scope may differ. Recognized bots are filtered, but human-only traffic is not guaranteed. Missing data remain missing. See report.md for all warnings and sensitivity ranges.",
        "source": "Wikimedia Analytics + Wikidata | Retrieved {date} | Exact sources: sources.json",
        "statuses": [
            "Consistent growth",
            "Consistent decline",
            "Mixed / flat",
            "Sensitive to a month",
            "Low volume",
            "Insufficient data",
        ],
    },
    "uk": {
        "badge": "WIKI INTEREST  /  ДОСЛІДНИЦЬКИЙ ЗВІТ",
        "period": "Повні місяці UTC",
        "headings": ["МОВА", "ЗА 12 МІС.", "ПЕРЕГЛЯДИ", "ЧАСТКА", "СИГНАЛ"],
        "chart_titles": ["Увага до статей", "Частка трафіку мовного розділу"],
        "chart_labels": ["Переглядів за день, у середньому", "Переглядів на мільйон у розділі"],
        "shortlist": "Дослідити далі: {languages}. Ці мови відповідають заданим критеріям росту. Перевірте намір навчатися та готовність платити через інтерв'ю і невеликий тест попиту.",
        "empty": "Немає підтвердженого сигналу росту за заданими критеріями. Цих переглядів недостатньо, щоб обрати запуск. Перевірте добір статей і доповніть аналіз інтерв'ю або невеликим тестом попиту.",
        "criteria": "Критерії росту: перегляди й частка +{threshold}% або більше; мінімум 9 позитивних пар місяців; за рік >= {volume} переглядів; вилучення будь-якої пари не змінює напрям. Це правила відбору, не рівні статистичної довіри. Зміни: останні 12 місяців до попередніх 12.",
        "scope": "Статті",
        "sensitivity": "Річна зміна переглядів після вилучення кожної пари місяців",
        "missing": "немає пов'язаної статті",
        "basket": "тем: {count}; повний список у report.md",
        "caveat": "Перегляди не дорівнюють покупцям, а мови - країнам. Враховано поточні назви без історичних перейменувань і перенаправлень. Обсяг статей може різнитися. Фільтр ботів не гарантує лише людський трафік. Пропуски не замінено нулями. Детальні обмеження й діапазони чутливості - у report.md.",
        "source": "Wikimedia Analytics + Wikidata | Отримано {date} | Точні джерела: sources.json",
        "statuses": [
            "Стійкий ріст",
            "Стійкий спад",
            "Змішаний / рівний",
            "Чутливий до місяця",
            "Мало переглядів",
            "Бракує даних",
        ],
    },
    "ru": {
        "badge": "WIKI INTEREST  /  ИССЛЕДОВАТЕЛЬСКИЙ ОТЧЁТ",
        "period": "Полные месяцы UTC",
        "headings": ["ЯЗЫК", "ЗА 12 МЕС.", "ПРОСМОТРЫ", "ДОЛЯ", "СИГНАЛ"],
        "chart_titles": ["Внимание к статьям", "Доля трафика языкового раздела"],
        "chart_labels": ["Просмотров за день, в среднем", "Просмотров на миллион в разделе"],
        "shortlist": "Исследовать дальше: {languages}. Эти языки отвечают заданным критериям роста. Проверьте намерение учиться и готовность платить через интервью и небольшой тест спроса.",
        "empty": "Нет подтверждённого сигнала роста по заданным критериям. Этих просмотров недостаточно для выбора запуска. Проверьте подбор статей и дополните анализ интервью или небольшим тестом спроса.",
        "criteria": "Критерии роста: просмотры и доля +{threshold}% или больше; минимум 9 положительных пар месяцев; за год >= {volume} просмотров; исключение любой пары сохраняет направление. Это правила отбора, не уровни статистической уверенности. Изменения: последние 12 месяцев к предыдущим 12.",
        "scope": "Статьи",
        "sensitivity": "Годовое изменение просмотров при исключении каждой пары месяцев",
        "missing": "нет связанной статьи",
        "basket": "тем: {count}; полный список в report.md",
        "caveat": "Просмотры не равны покупателям, а языки - странам. Учтены текущие названия без исторических переименований и перенаправлений. Объём статей может различаться. Фильтр ботов не гарантирует только человеческий трафик. Пропуски не заменены нулями. Все ограничения и диапазоны чувствительности - в report.md.",
        "source": "Wikimedia Analytics + Wikidata | Получено {date} | Точные источники: sources.json",
        "statuses": [
            "Устойчивый рост",
            "Устойчивый спад",
            "Смешанный / ровный",
            "Зависит от месяца",
            "Мало просмотров",
            "Мало данных",
        ],
    },
}
STATUS_KEYS = [
    "consistent_growth",
    "consistent_decline",
    "mixed_or_flat",
    "sensitive",
    "low_volume",
    "insufficient_data",
]


def brief_text(result):
    return TEXT[result.get("report_language", "en")]


def brief_recommendation(result):
    text = brief_text(result)
    if result["research_shortlist"]:
        return text["shortlist"].format(languages=", ".join(result["research_shortlist"]))
    return text["empty"]
