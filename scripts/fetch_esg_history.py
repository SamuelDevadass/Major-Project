import sys
from pathlib import Path
import pandas as pd
import re

BASE_DIR    = Path(__file__).parent.parent
DATA_DIR    = BASE_DIR / "data"
INPUT_EXCEL = DATA_DIR / "data.xlsx"
OUTPUT_EXCEL = DATA_DIR / "cleaned_data.xlsx"

YEARS = ["2022", "2023", "2024","2025"]


def normalise_col_name(col: str) -> str:
    return col.strip().lower().replace(" ", "_")


def normalise_company_name(name: str) -> str:
    return str(name).strip().upper().replace(" ", "_")


def clean_sheet(sheet_name: str) -> pd.DataFrame:
    print(f"\nCleaning sheet: {sheet_name}")

    df = pd.read_excel(INPUT_EXCEL, sheet_name=sheet_name)

    ## REMOVE EXTRA WHITESPACES
    df = df.apply(lambda col: col.map(lambda x: x.strip() if isinstance(x, str) else x))

    # CHANGE COLUMN NAMES TO HAVE _
    df.columns = [normalise_col_name(c) for c in df.columns]

    ## ELIMINATE NAN ROWS
    if "company_name" in df.columns:
        df["company_name"] = df["company_name"].astype(str)
        df = df[df["company_name"].str.strip() != ""]

    df = df[~df["company_name"].str.startswith("-", na=False)]

    df = df.dropna(how="all")

    df = df[df["company_name"].str.len() > 2]

    ## CREATE A COLUMN TICKER AS THE SEARCH KEY
    if "company_name" in df.columns:
        df["ticker"] = df["company_name"].apply(normalise_company_name)

    ## CLEAN NUMERIC COLUMNS
    for col in ["environment_score", "social_score", "governance_score","esg_rating","esg"]:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: (
                    float(re.search(r"\d{1,3}", str(x)).group())
                    if re.search(r"\d{1,3}", str(x))
                    else pd.NA))
    return df


def main():
    if not INPUT_EXCEL.exists():
        print(f"File not found: {INPUT_EXCEL}")
        sys.exit(1)

    with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
        for sheet in YEARS:
            df_clean = clean_sheet(sheet)
            print("INPUT DATAFRAME SHAPE: ",df_clean.shape)
            df_clean.to_excel(writer, sheet_name=sheet, index=False)
            print("OUTPUT DATAFRAME SHAPE: ",df_clean.shape)

    print(f"\nCleaned file saved to: {OUTPUT_EXCEL}")


if __name__ == "__main__":
    main()