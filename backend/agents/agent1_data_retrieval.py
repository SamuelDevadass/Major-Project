# Agent 1 — Data Retrieval
# Reads data/cleaned_data.xlsx (output of clean_esg_data.py)
# Each sheet is a year: 2022, 2023, 2024, 2025
# Matches companies by company_name (exact, uppercase)
# Builds monthly time series, yearly averages, validation split

import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR      = Path(__file__).parent.parent
DATA_DIR      = BASE_DIR.parent / "data"
CLEANED_EXCEL = DATA_DIR / "cleaned_data.xlsx"

SCORE_COLS = ["environment_score", "social_score", "governance_score"]

# Training window 2022-2024, validation = 2025
VALIDATION_MAP = {
    2022: [2025],
    2023: [2025],
    2024: [2025],
}


class DataRetrievalAgent:
    """
    Agent 1 — loads CRISIL ESG data from cleaned Excel.

    Input:
        companies  : list of company_name strings (uppercase with _)
        year_range : [2022, 2023, 2024]

    Output dict (one key per company_name, plus "_meta"):
        {
            "RELIANCE_INDUSTRIES_LIMITED": {
                "found":              True,
                "monthly_training":   DataFrame,
                "monthly_validation": DataFrame,
                "yearly_scores":      {2022: {E, S, G, Total}, ...},
                "kaggle_meta":        {company_name, sector, esg_rating, category},
                "data_quality_flags": {nan_filled, has_2025_data, pct_rows_available},
            },
            "_meta": {
                "year_range":       [2022, 2023, 2024],
                "validation_years": [2025],
            }
        }
    """

    def run(self, companies: list[str], year_range: list[int]) -> dict:
        train_start      = year_range[0]
        train_end        = year_range[-1]
        validation_years = VALIDATION_MAP.get(train_start, [2025])

        # Load all sheets from cleaned Excel
        all_data = self._load_all_sheets()

        result = {}
        for company in companies:
            result[company] = self._process_company(
                company, all_data, train_start, train_end, validation_years
            )

        result["_meta"] = {
            "year_range":       year_range,
            "validation_years": validation_years,
        }
        return result

    ## LOAD DATA 

    def _load_all_sheets(self) -> dict[int, pd.DataFrame]:
        """Load all year sheets from cleaned_data.xlsx. Returns {year: DataFrame}."""
        xl     = pd.ExcelFile(CLEANED_EXCEL)
        sheets = {}
        for sheet in xl.sheet_names:
            try:
                yr = int(sheet)
            except ValueError:
                continue
            df = xl.parse(sheet)
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
            # Ensure ticker column exists (generated from company_name)
            if "ticker" not in df.columns and "company_name" in df.columns:
                df["ticker"] = df["company_name"].str.strip().str.upper().str.replace(" ", "_")
            df["year"] = yr
            sheets[yr] = df
        return sheets

    ## PROCESS A SINGLE COMPANY 

    def _process_company(
        self,
        company: str,
        all_data: dict[int, pd.DataFrame],
        train_start: int,
        train_end: int,
        validation_years: list[int],
    ) -> dict:
        """Extract and process data for one company across all years."""

        # Collect annual rows for this company
        annual_rows = []
        for yr, df in all_data.items():
            match = df[df["ticker"] == company]
            if not match.empty:
                # Catch all occurrences
                for _, row_data in match.iterrows():  # ← Iterate directly over rows
                    row = row_data.to_dict()
                    row["year"] = yr
                    annual_rows.append(row)

        if not annual_rows:
            return {"found": False}

        # Build a clean annual DataFrame
        annual_df = pd.DataFrame(annual_rows)

        # Resolve score column names — handle both "environment_score" and "esg" variants
        e_col     = self._find_col(annual_df, ["environment_score", "e_score", "e"])
        s_col     = self._find_col(annual_df, ["social_score",      "s_score", "s"])
        g_col     = self._find_col(annual_df, ["governance_score",  "g_score", "g"])
        name_col  = self._find_col(annual_df, ["company_name"])
        sector_col= self._find_col(annual_df, ["sector_classification", "sector", "industry"])
        rating_col= self._find_col(annual_df, ["esg_rating", "esg"])
        cat_col   = self._find_col(annual_df, ["category"])

        if not e_col:
            return {"found": False}

        # Compute total score
        annual_df["E_Score"]     = pd.to_numeric(annual_df[e_col], errors="coerce")
        annual_df["S_Score"]     = pd.to_numeric(annual_df[s_col], errors="coerce") if s_col else np.nan
        annual_df["G_Score"]     = pd.to_numeric(annual_df[g_col], errors="coerce") if g_col else np.nan
        annual_df["Total_Score"] = annual_df[["E_Score","S_Score","G_Score"]].mean(axis=1)

        # NaN fill
        nan_before = annual_df[["E_Score","S_Score","G_Score","Total_Score"]].isna().sum().sum()
        annual_df[["E_Score","S_Score","G_Score","Total_Score"]] = (
            annual_df[["E_Score","S_Score","G_Score","Total_Score"]]
            .interpolate(method="linear", limit_direction="both")
        )
        nan_filled = int(nan_before - annual_df[["E_Score","S_Score","G_Score","Total_Score"]].isna().sum().sum())

        # Expand annual 12 monthly rows per year
        monthly_rows = []
        for _, row in annual_df.iterrows():
            yr = int(row["year"])
            for month in range(1, 13):
                monthly_rows.append({
                    "date":        pd.Timestamp(f"{yr}-{month:02d}-01"),
                    "ticker":      company,
                    "E_Score":     row["E_Score"],
                    "S_Score":     row["S_Score"],
                    "G_Score":     row["G_Score"],
                    "Total_Score": row["Total_Score"],
                })

        monthly_df = pd.DataFrame(monthly_rows).sort_values("date").reset_index(drop=True)

        # Split training / validation
        train_mask = (monthly_df["date"].dt.year >= train_start) & \
                     (monthly_df["date"].dt.year <= train_end)
        val_mask   = monthly_df["date"].dt.year.isin(validation_years)

        monthly_training   = monthly_df[train_mask].copy().reset_index(drop=True)
        monthly_validation = monthly_df[val_mask].copy().reset_index(drop=True)

        # Yearly averages
        all_years    = list(range(train_start, train_end + 1)) + validation_years
        yearly_scores = self._compute_yearly_averages(monthly_df, all_years)

        # Metadata from most recent row
        latest = annual_df.sort_values("year", ascending=False).iloc[0]
        meta = {
            "company_name": str(latest.get(name_col,  company)) if name_col  else company,
            "sector":       str(latest.get(sector_col,"Unknown")) if sector_col else "Unknown",
            "industry":     str(latest.get(sector_col,"Unknown")) if sector_col else "Unknown",
            "esg_rating":   str(latest.get(rating_col,"N/A"))    if rating_col else "N/A",
            "category":     str(latest.get(cat_col,   "N/A"))    if cat_col    else "N/A",
        }

        has_2025 = 2025 in annual_df["year"].values

        return {
            "found":              True,
            "monthly_training":   monthly_training,
            "monthly_validation": monthly_validation,
            "yearly_scores":      yearly_scores,
            "kaggle_meta":        meta,
            "data_quality_flags": {
                "nan_filled":         nan_filled,
                "has_2025_data":      bool(has_2025),
                "pct_rows_available": round(len(monthly_training) / max((train_end - train_start + 1) * 12, 1) * 100, 1),
            },
        }

    def _find_col(self, df: pd.DataFrame, variants: list[str]) -> str | None:
        """Find a column by exact name match from a list of variants."""
        for v in variants:
            if v in df.columns:
                return v
        return None

    def _compute_yearly_averages(self, df: pd.DataFrame, years: list[int]) -> dict:
        yearly = {}
        for yr in years:
            yr_df = df[df["date"].dt.year == yr]
            if yr_df.empty:
                continue
            yearly[yr] = {
                "E":     round(float(yr_df["E_Score"].mean()),     2),
                "S":     round(float(yr_df["S_Score"].mean()),     2),
                "G":     round(float(yr_df["G_Score"].mean()),     2),
                "Total": round(float(yr_df["Total_Score"].mean()), 2),
            }
        return yearly