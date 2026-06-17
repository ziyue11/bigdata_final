from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def normalize_industry(industry: str) -> str:
    value = (industry or "economy").strip().lower()
    if value == "finance":
        return "economy"
    return value


def data_dir(industry: str) -> Path:
    return ROOT / "data" / normalize_industry(industry)


def output_dir(industry: str) -> Path:
    return ROOT / "outputs" / normalize_industry(industry)


def report_dir(industry: str) -> Path:
    return ROOT / "docs" / normalize_industry(industry) / "report"


def raw_dir(industry: str) -> Path:
    return data_dir(industry) / "raw"


def processed_dir(industry: str) -> Path:
    return data_dir(industry) / "processed"


def analysis_dir(industry: str) -> Path:
    return data_dir(industry) / "analysis"
