from pathlib import Path

from common import (
    clean_text,
    extract_entity,
    is_invalid_record,
    make_record_id,
    non_empty_rate,
    normalize_date,
    parse_number,
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
    "read_count",
    "comment_count",
    "url",
]


def clean_comment(raw_dir, output_path):
    input_path = Path(raw_dir) / "comment_raw.csv"
    raw_rows = read_csv(input_path)
    invalid_count = 0
    cleaned = []
    seen = set()
    for row in raw_rows:
        title = clean_text(row.get("title"))
        content = clean_text(row.get("content")) or title
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
                "source_type": "comment",
                "source": clean_text(row.get("source")),
                "title": title,
                "event_date": normalize_date(row.get("publish_time"), row.get("crawl_time")),
                "content": content,
                "mentioned_entity": clean_text(row.get("stock_or_entity")) or extract_entity(title, content),
                "read_count": parse_number(row.get("read_count")),
                "comment_count": parse_number(row.get("comment_count")),
                "url": url,
            }
        )

    for index, row in enumerate(cleaned, start=1):
        row["record_id"] = make_record_id("COMM", index)

    write_csv(output_path, cleaned, FIELDS)
    return {
        "name": "comment_cleaned.csv",
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
