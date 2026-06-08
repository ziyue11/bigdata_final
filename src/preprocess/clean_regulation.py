from pathlib import Path

from common import (
    clean_text,
    extract_entity,
    extract_region,
    is_invalid_record,
    make_record_id,
    non_empty_rate,
    normalize_date,
    parse_penalty_amount,
    read_csv,
    write_csv,
)


FIELDS = [
    "record_id",
    "source_type",
    "source",
    "title",
    "event_date",
    "entity_name",
    "raw_text",
    "penalty_amount",
    "agency",
    "region",
    "url",
]


def clean_regulation(raw_dir, output_path):
    raw_dir = Path(raw_dir)
    inputs = [
        raw_dir / "regulation_nfra_raw.csv",
        raw_dir / "regulation_csrc_raw.csv",
    ]
    raw_rows = []
    for path in inputs:
        raw_rows.extend(read_csv(path))

    invalid_count = 0
    cleaned = []
    seen = set()
    for row in raw_rows:
        source = clean_text(row.get("source"))
        title = clean_text(row.get("title"))
        url = clean_text(row.get("url"))
        violation_text = clean_text(row.get("violation_text"))
        penalty_text = clean_text(row.get("penalty_text"))
        raw_text = clean_text(f"{violation_text}\n{penalty_text}") if penalty_text else violation_text
        if is_invalid_record(title, raw_text, url):
            invalid_count += 1
            continue

        key = (source, title, url)
        if key in seen:
            continue
        seen.add(key)

        if source.upper() == "NFRA":
            entity_name = clean_text(row.get("punished_entity")) or extract_entity(title, raw_text)
            agency = clean_text(row.get("agency"))
        else:
            entity_name = clean_text(row.get("party")) or extract_entity(title, raw_text)
            agency = clean_text(row.get("agency")) or "中国证监会"

        cleaned.append(
            {
                "record_id": "",
                "source_type": "regulation",
                "source": source,
                "title": title,
                "event_date": normalize_date(row.get("publish_time"), row.get("crawl_time")),
                "entity_name": entity_name,
                "raw_text": raw_text,
                "penalty_amount": parse_penalty_amount(
                    row.get("penalty_amount_raw"),
                    penalty_text,
                    violation_text,
                ),
                "agency": agency,
                "region": extract_region(agency, title, raw_text),
                "url": url,
            }
        )

    for index, row in enumerate(cleaned, start=1):
        row["record_id"] = make_record_id("REG", index)

    write_csv(output_path, cleaned, FIELDS)
    parsed_penalty_count = sum(1 for row in cleaned if float(row["penalty_amount"] or 0) > 0)
    return {
        "name": "regulation_cleaned.csv",
        "input_files": [str(path) for path in inputs],
        "raw_count": len(raw_rows),
        "after_invalid_count": len(raw_rows) - invalid_count,
        "output_count": len(cleaned),
        "duplicate_removed": len(raw_rows) - invalid_count - len(cleaned),
        "invalid_removed": invalid_count,
        "fields": FIELDS,
        "event_date_non_empty_rate": non_empty_rate(cleaned, "event_date"),
        "url_non_empty_rate": non_empty_rate(cleaned, "url"),
        "text_non_empty_rate": non_empty_rate(cleaned, "raw_text"),
        "entity_non_empty_rate": non_empty_rate(cleaned, "entity_name"),
        "penalty_amount_parsed_count": parsed_penalty_count,
    }
