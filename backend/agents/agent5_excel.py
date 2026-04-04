# backend/agents/agent5_excel.py
# Agent 5 — Excel Export + Matplotlib Chart Generation
# NOTE: CRISIL ESG scores 0-100, higher = better
# Generates matplotlib trend charts per company (BytesIO, base64-encoded).
# File 1: esg_cross_company.xlsx (3 year sheets + charts sheet)
# File 2: esg_per_company.xlsx (1 sheet per company)

import base64,json
import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xlsxwriter

BASE_DIR    = Path(__file__).parent.parent
OUTPUTS_DIR = BASE_DIR / "outputs"

# ── COLOURS ───────────────────────────────────────────────────────────────────
TEAL       = "#0D6E6E"
TEAL_LIGHT = "#D0EBEB"
VAL_BLUE   = "#D6EAF8"
GRAY       = "#F2F2F2"
WHITE      = "#FFFFFF"
DARK       = "#1A1A2E"

SCORE_COLORS = {"E": "#27AE60", "S": "#2980B9", "G": "#8E44AD", "Total": TEAL}
SCORE_LABELS = {"E": "Environment Score", "S": "Social Score", "G": "Governance Score", "Total": "Total ESG Score"}

# CRISIL only provides E, S, G, Total — no sub-parameters
METRICS = [
    ("Environmental", [("Environment Score", "E")]),
    ("Social",        [("Social Score",       "S")]),
    ("Governance",    [("Governance Score",   "G")]),
    ("Overall",       [("Total ESG Score",    "Total")]),
]


class ExcelAgent:
    """
    Agent 5 — matplotlib charts + two Excel workbooks.

    Input:
        job_id, agent1_result, agent3_result, agent4_result

    Output:
        { file1: path, file2: path, charts_base64: {ticker: base64} }
    """

    def run(self, job_id, agent1_result, agent3_result, agent4_result):
        job_dir = OUTPUTS_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        meta             = agent1_result.get("_meta", {})
        year_range       = meta.get("year_range", [])
        validation_years = meta.get("validation_years", [])
        companies        = [k for k in agent1_result if k != "_meta" and agent1_result[k].get("found")]

        # ── GENERATE CHARTS ───────────────────────────────────────────────────
        charts_base64 = {}
        charts_bytes  = {}
        for ticker in companies:
            b64, img_bytes = self._generate_chart(
                ticker,
                agent1_result[ticker],
                agent3_result.get(ticker, {}),
                year_range,
                validation_years,
            )
            charts_base64[ticker] = b64
            charts_bytes[ticker]  = img_bytes

        # ── FILE 1 ────────────────────────────────────────────────────────────
        file1_path = job_dir / "esg_cross_company.xlsx"
        self._write_file1(file1_path, companies, agent1_result, year_range, validation_years, charts_bytes)

        # ── FILE 2 ────────────────────────────────────────────────────────────
        file2_path = job_dir / "esg_per_company.xlsx"
        self._write_file2(file2_path, companies, agent1_result, agent3_result,
                          agent4_result, year_range, validation_years, charts_bytes)

        return {
            "file1":         str(file1_path),
            "file2":         str(file2_path),
            "charts_base64": charts_base64,
        }

    # ── CHART GENERATION ──────────────────────────────────────────────────────

    def _generate_chart(self, ticker, a1, a3, year_range, validation_years):
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.set_facecolor("#F8F9FA")
        fig.patch.set_facecolor(WHITE)

        yearly     = a1.get("yearly_scores", {})
        val_table  = a3.get("validation_table", [])
        regression = a3.get("regression_coeffs", {})

        train_years = [yr for yr in sorted(yearly.keys()) if yr in year_range]
        val_years   = validation_years

        for key in ["E", "S", "G", "Total"]:
            color = SCORE_COLORS[key]
            label = SCORE_LABELS[key]

            # Training actuals — solid line
            t_y_valid = [(yr, yearly[yr][key]) for yr in train_years
                         if yearly.get(yr, {}).get(key) is not None]
            if t_y_valid:
                xs, ys = zip(*t_y_valid)
                ax.plot(xs, ys, color=color, linewidth=2, label=label, zorder=3)
                ax.scatter(xs, ys, color=color, s=40, zorder=4)

            # Projected scores — dashed line
            if regression and key in regression:
                c          = regression[key]
                proj_years = ([train_years[-1]] if train_years else []) + list(val_years)
                proj_vals  = [c["slope"] * (yr - c["t_min"]) + c["intercept"] for yr in proj_years]
                if len(proj_years) > 1:
                    ax.plot(proj_years, proj_vals, color=color, linewidth=1.5,
                            linestyle="--", alpha=0.7, zorder=2)

            # Actual validation scores — filled markers
            for row in val_table:
                act = row.get("actual", {}).get(key)
                if act is not None:
                    ax.scatter([row["year"]], [act], color=color, s=80,
                               marker="o", edgecolors="white", linewidth=1.5, zorder=5)

        # Vertical separator
        if train_years and val_years:
            sep_x = train_years[-1] + 0.5
            ax.axvline(x=sep_x, color="#AAAAAA", linestyle=":", linewidth=1.2, zorder=1)
            ax.text(sep_x + 0.05, ax.get_ylim()[1] * 0.98, "Validation →",
                    fontsize=8, color="#888888", va="top")

        company_name = a1.get("kaggle_meta", {}).get("company_name", ticker)
        ax.set_title(f"{company_name} ({ticker}) — CRISIL ESG Trend",
                     fontsize=13, fontweight="bold", color=DARK, pad=10)
        ax.set_xlabel("Year", fontsize=10, color=DARK)
        ax.set_ylabel("CRISIL ESG Score (0–100, higher = better)", fontsize=10, color=DARK)
        ax.tick_params(colors=DARK, labelsize=9)
        ax.set_ylim(0, 100)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(fontsize=9, loc="best", framealpha=0.8)
        ax.grid(axis="y", alpha=0.3, color="#CCCCCC")
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        img_bytes = buf.read()
        b64 = "data:image/png;base64," + base64.b64encode(img_bytes).decode("utf-8")
        return b64, img_bytes

    # ── FILE 1: CROSS-COMPANY ─────────────────────────────────────────────────

    def _write_file1(self, path, companies, agent1_result, year_range, validation_years, charts_bytes):        
        wb = xlsxwriter.Workbook(str(path))
        hdr_fmt  = wb.add_format({"bold": True, "bg_color": TEAL, "font_color": WHITE,
                                   "border": 1, "align": "center", "font_name": "Arial", "font_size": 11})
        cell_fmt = wb.add_format({"border": 1, "font_name": "Arial", "font_size": 10})
        gray_fmt = wb.add_format({"border": 1, "bg_color": GRAY, "font_name": "Arial", "font_size": 10})
        sect_fmt = wb.add_format({"bold": True, "bg_color": TEAL_LIGHT, "font_name": "Arial",
                                   "font_size": 11, "border": 1})

        all_years = list(year_range) + list(validation_years)
        for yr in all_years:
            ws = wb.add_worksheet(str(yr))
            ws.freeze_panes(1, 1)
            ws.set_column(0, 0, 25)

            # Header
            ws.write(0, 0, "Metric", hdr_fmt)
            for col_idx, ticker in enumerate(companies):
                name = agent1_result[ticker].get("kaggle_meta", {}).get("company_name", ticker)
                ws.write(0, col_idx + 1, f"{name}\n({ticker})", hdr_fmt)
                ws.set_column(col_idx + 1, col_idx + 1, 22)

            row = 1
            for pillar_name, metrics in METRICS:
                ws.merge_range(row, 0, row, len(companies), pillar_name, sect_fmt)
                row += 1
                for metric_name, score_key in metrics:
                    fmt = gray_fmt if row % 2 == 0 else cell_fmt
                    ws.write(row, 0, metric_name, fmt)
                    for col_idx, ticker in enumerate(companies):
                        yearly = agent1_result[ticker].get("yearly_scores", {})
                        val    = yearly.get(yr, {}).get(score_key)
                        ws.write(row, col_idx + 1, val if val is not None else "N/A", fmt)
                    row += 1

        # Sheet 4: Charts
        """chart_ws = wb.add_worksheet("ESG Charts")
        chart_ws.write(0, 0, "CRISIL ESG Trajectory Charts", hdr_fmt)
        row_offset = 2
        for ticker in companies:
            img = charts_bytes.get(ticker)
            if img:
                chart_ws.insert_image(row_offset, 0, f"chart_{ticker}.png",
                                      {"image_data": io.BytesIO(img), "x_scale": 0.75, "y_scale": 0.75})
                row_offset += 22"""

        wb.close()

    # ── FILE 2: PER-COMPANY ───────────────────────────────────────────────────

    def _write_file2(self, path, companies, agent1_result, agent3_result,
                     agent4_result, year_range, validation_years, charts_bytes):
        wb = xlsxwriter.Workbook(str(path))

        ref_file = BASE_DIR / "reference_list.json"
        if ref_file.exists():
            with open(ref_file, "r", encoding="utf-8") as f:
                reference_data = json.load(f)
        else:
            reference_data = {}

        hdr_fmt   = wb.add_format({"bold": True, "bg_color": TEAL, "font_color": WHITE,
                                    "border": 1, "align": "center", "font_name": "Arial", "font_size": 11})
        train_fmt = wb.add_format({"border": 1, "bg_color": WHITE,    "font_name": "Arial", "font_size": 10})
        val_fmt   = wb.add_format({"border": 1, "bg_color": VAL_BLUE, "font_name": "Arial", "font_size": 10})
        sect_fmt  = wb.add_format({"bold": True, "bg_color": TEAL_LIGHT, "font_name": "Arial",
                                    "font_size": 11, "border": 1})
        narr_fmt  = wb.add_format({"font_name": "Arial", "font_size": 10, "text_wrap": True})
        bold_fmt  = wb.add_format({"bold": True, "font_name": "Arial", "font_size": 11})

        all_years = list(year_range) + list(validation_years)

        for ticker in companies:
            a1   = agent1_result.get(ticker, {})
            a3   = agent3_result.get(ticker, {})
            a4   = agent4_result.get(ticker, {})
            meta = a1.get("kaggle_meta", {})

            ws = wb.add_worksheet(ticker[:31])
            ws.freeze_panes(2, 1)
            ws.set_column(0, 0, 25)

            # Legend
            ws.write(0, 0,
                     "CRISIL ESG Scores (0-100, higher=better) | "
                     "White = Training | Blue = Validation", narr_fmt)

            # Year headers
            ws.write(1, 0, "Metric", hdr_fmt)
            for c_idx, yr in enumerate(all_years):
                ws.write(1, c_idx + 1, str(yr), hdr_fmt)
                ws.set_column(c_idx + 1, c_idx + 1, 14)

            # Score rows
            yearly = a1.get("yearly_scores", {})
            row    = 2
            for pillar_name, metrics in METRICS:
                ws.merge_range(row, 0, row, len(all_years), pillar_name, sect_fmt)
                row += 1
                for metric_name, score_key in metrics:
                    ws.write(row, 0, metric_name, bold_fmt)
                    for c_idx, yr in enumerate(all_years):
                        val = yearly.get(yr, {}).get(score_key)
                        fmt = val_fmt if yr in validation_years else train_fmt
                        ws.write(row, c_idx + 1, val if val is not None else "N/A", fmt)
                    row += 1

            row += 1

            # Validation table
            ws.write(row, 0, "Adaptive Validation Summary (Training: 2022-2024 | Validation: 2025)", bold_fmt)
            row += 1
            for h, label in enumerate(["Year", "Projected Total", "Actual Total",
                                        "Delta", "Status", "Direction"]):
                ws.write(row, h, label, hdr_fmt)
            row += 1
            for val_row in a3.get("validation_table", []):
                ws.write(row, 0, val_row["year"],                                      train_fmt)
                ws.write(row, 1, val_row.get("projected", {}).get("Total", "N/A"),    train_fmt)
                ws.write(row, 2, val_row.get("actual",    {}).get("Total", "N/A"),    train_fmt)
                ws.write(row, 3, val_row.get("delta",     {}).get("Total", "N/A"),    train_fmt)
                ws.write(row, 4, val_row.get("status",    "N/A"),                     train_fmt)
                ws.write(row, 5, val_row.get("direction", "N/A"),                     train_fmt)
                row += 1

            row += 1

            # Embedded chart
            img = charts_bytes.get(ticker)
            if img:
                ws.insert_image(row, 0, f"chart_{ticker}.png",
                                {"image_data": io.BytesIO(img), "x_scale": 0.75, "y_scale": 0.75})
                row += 22

            row += 1

            # --- AI Narrative ---
            ws.write(row, 0, "AI Investor Narrative", bold_fmt)
            row += 1
            narrative = a4.get("narrative", "No narrative generated.")
            
            # Narrative box (11 rows high)
            ws.merge_range(row, 0, row + 10, len(all_years), narrative, narr_fmt)
            row += 11 # Move below the narrative

            # --- NEW: SOURCE REFERENCES ---
            row += 1 # Small gap
            ws.write(row, 0, "Source References", bold_fmt)
            row += 1
            
            # Fetch the map we passed through Agent 4
            # --- SOURCE REFERENCES FROM JSON ---
            company_refs = reference_data.get(ticker, {})

            if company_refs:
                for key, value in company_refs.items():
                    ws.write(row, 0, str(key), bold_fmt)
                    
                    # If it's a real URL make clickable
                    if isinstance(value, str) and value.startswith("http"):
                        ws.write_url(row, 1, value, string="Open Link")
                    else:
                        # Otherwise just write text
                        ws.write(row, 1, str(value))
                    
                    row += 1
            else:
                ws.write(row, 0, "No references found.", narr_fmt)
            
            # Update row counter for next company sheet loop if needed
            row += 2

        wb.close()