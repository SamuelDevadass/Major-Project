# backend/services/company_service.py
# Reads cleaned_data.xlsx at startup.
# Stores both ticker (uppercase_with_underscores) and company_name (display).
# Frontend shows company_name, sends ticker to POST /analyze.

from pathlib import Path
import pandas as pd

BASE_DIR      = Path(__file__).parent.parent
DATA_DIR      = BASE_DIR.parent / "data"
CLEANED_EXCEL = DATA_DIR / "cleaned_data.xlsx"

_companies_list: list[dict] = []
_valid_tickers:  set[str]   = set()


def load_companies() -> None:
    """
    Called at app startup via lifespan.
    Reads all sheets from cleaned_data.xlsx, deduplicates companies,
    and caches the list in memory.
    """
    global _companies_list, _valid_tickers

    if not CLEANED_EXCEL.exists():
        raise RuntimeError(
            f"Required file missing: {CLEANED_EXCEL}\n"
            f"Run scripts/clean_esg_data.py first."
        )

    xl = pd.ExcelFile(CLEANED_EXCEL)
    seen    = {}  # ticker for row dict, keep latest year

    for sheet in xl.sheet_names:
        try:
            yr = int(sheet)
        except ValueError:
            continue

        df = xl.parse(sheet)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        if "company_name" not in df.columns:
            continue

        # Ensure ticker column exists
        if "ticker" not in df.columns:
            df["ticker"] = (
                df["company_name"]
                .astype(str).str.strip().str.upper()
                .str.replace(" ", "_")
            )

        # Find sector column
        sector_col = next(
            (c for c in ["sector_classification", "sector", "industry"] if c in df.columns),
            None
        )

        for _, row in df.iterrows():
            ticker = str(row["ticker"]).strip().upper()
            name   = str(row["company_name"]).strip()
            sector = str(row[sector_col]).strip() if sector_col else "Unknown"

            if not ticker or ticker == "NAN":
                continue

            # Keep latest year's data per ticker
            if ticker not in seen or yr > seen[ticker]["_year"]:
                seen[ticker] = {
                    "ticker":       ticker,
                    "company_name": name,
                    "sector":       sector,
                    "_year":        yr,
                }

    # Build final list sorted by company_name
    records = sorted(
        [{"ticker": v["ticker"], "company_name": v["company_name"], "sector": v["sector"]}
         for v in seen.values()],
        key=lambda x: x["company_name"]
    )

    _companies_list = records
    _valid_tickers  = {r["ticker"] for r in records}


def get_companies_list() -> list[dict]:
    """Returns list of { ticker, company_name, sector } for frontend dropdown."""
    return _companies_list


def get_valid_tickers() -> set[str]:
    """Returns set of valid uppercase ticker strings for input validation."""
    return _valid_tickers