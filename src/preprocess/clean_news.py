from pathlib import Path

from common import (
    clean_text,
    extract_entity,
    is_invalid_record,
    make_record_id,
    non_empty_rate,
    normalize_date,
    read_csv,
    write_csv,
)


FIELDS = [
    "record_id",
    "source_type",
    "source",
    "title",
    "event_date",
    "content",
    "mentioned_entity",
    "channel",
    "url",
]


def clean_news(raw_dir, output_path):
    raw_dir = Path(raw_dir)
    input_path = raw_dir / "medical_news_raw.csv"
    if not input_path.exists():
        input_path = raw_dir / "news_raw.csv"
    raw_rows = read_csv(input_path)
    invalid_count = 0
    cleaned = []
    seen = set()
    for row in raw_rows:
        title = clean_text(row.get("title"))
        content = clean_text(row.get("content"))
        url = clean_text(row.get("url"))
        if is_invalid_record(title, content, url):
            invalid_count += 1
            continue

        key = (title, url)
        if key in seen:
            continue
        seen.add(key)

        cleaned.append(
            {
                "record_id": "",
                "source_type": "news",
                "source": clean_text(row.get("source")),
                "title": title,
                "event_date": normalize_date(row.get("publish_time"), row.get("crawl_time")),
                "content": content,
                "mentioned_entity": extract_entity(title, content),
                "channel": clean_text(row.get("channel")),
                "url": url,
            }
        )

    for index, row in enumerate(cleaned, start=1):
        row["record_id"] = make_record_id("NEWS", index)

    write_csv(output_path, cleaned, FIELDS)
    return {
        "name": "news_cleaned.csv",
        "input_files": [str(input_path)],
        "raw_count": len(raw_rows),
        "after_invalid_count": len(raw_rows) - invalid_count,
        "output_count": len(cleaned),
        "duplicate_removed": len(raw_rows) - invalid_count - len(cleaned),
        "invalid_removed": invalid_count,
        "fields": FIELDS,
        "event_date_non_empty_rate": non_empty_rate(cleaned, "event_date"),
        "url_non_empty_rate": non_empty_rate(cleaned, "url"),
        "text_non_empty_rate": non_empty_rate(cleaned, "content"),
        "entity_non_empty_rate": non_empty_rate(cleaned, "mentioned_entity"),
        "penalty_amount_parsed_count": "",
    }
