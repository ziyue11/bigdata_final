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
    medical_inputs = [
        raw_dir / "medical_regulation_raw.csv",
        raw_dir / "medical_insurance_raw.csv",
        raw_dir / "medical_drug_device_raw.csv",
    ]
    existing_medical_inputs = [path for path in medical_inputs if path.exists()]
    if existing_medical_inputs:
        inputs = existing_medical_inputs
    elif (raw_dir / "medical_news_raw.csv").exists():
        inputs = []
    else:
        inputs = sorted(raw_dir.glob("regulation_*_raw.csv"))
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
        violation_text = clean_text(row.get("violation_text") or row.get("raw_text"))
        penalty_text = clean_text(row.get("penalty_text"))
        raw_text = clean_text(f"{violation_text}\n{penalty_text}") if penalty_text else violation_text
        if is_invalid_record(title, raw_text, url):
            invalid_count += 1
            continue

        key = (source, title, url)
        if key in seen:
            continue
        seen.add(key)

        entity_name = (
            clean_text(row.get("punished_entity"))
            or clean_text(row.get("party"))
            or clean_text(row.get("entity_name"))
            or extract_entity(title, raw_text)
        )
        agency = clean_text(row.get("agency"))

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
