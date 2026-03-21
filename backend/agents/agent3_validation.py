# backend/agents/agent3_validation.py
# Agent 3 — LOWESS Smoothing + Exponentially Weighted Regression + Adaptive Validation
# NOTE: CRISIL ESG scores are 0-100 where HIGHER = BETTER
# (opposite of Sustainalytics where lower = better risk)

import numpy as np
import pandas as pd
from statsmodels.nonparametric.smoothers_lowess import lowess

from config.thresholds import (
    LOWESS_FRAC, REGRESSION_EXP_WEIGHT, MIN_MONTHS_FOR_LOWESS,
    ON_TRACK_MAX, MODERATE_DRIFT_MAX,
    TREND_SUSTAINED, TREND_WEAKENING, TREND_BROKE, TREND_ACCELERATING,
)

SCORE_COLS = ["E_Score", "S_Score", "G_Score", "Total_Score"]
SCORE_KEYS = ["E", "S", "G", "Total"]


class ValidationAgent:
    """
    Agent 3 — LOWESS + weighted regression + adaptive forward validation.

    CRISIL scoring: 0-100, higher = better ESG performance.

    Input:  agent1_result dict from Agent 1
    Output: dict keyed by ticker with trend, validation_table, lowess_yearly
    """

    def run(self, agent1_result: dict) -> dict:
        result           = {}
        meta             = agent1_result.get("_meta", {})
        year_range       = meta.get("year_range", [])
        validation_years = meta.get("validation_years", [])

        for ticker, data in agent1_result.items():
            if ticker == "_meta" or not data.get("found", False):
                continue
            result[ticker] = self._process_ticker(
                ticker, data, year_range, validation_years
            )
        return result

    def _process_ticker(self, ticker, data, year_range, validation_years):
        monthly_df = data["monthly_training"]
        val_df     = data["monthly_validation"]
        yearly_raw = data["yearly_scores"]

        use_fallback = len(monthly_df) < MIN_MONTHS_FOR_LOWESS

        lowess_yearly, _ = self._apply_lowess(monthly_df, year_range, use_fallback)
        regression_coeffs = self._fit_regression(lowess_yearly, year_range)
        trend = self._build_trend_summary(regression_coeffs, lowess_yearly, year_range, use_fallback)

        validation_table = self._run_validation(
            validation_years, regression_coeffs, lowess_yearly, val_df, yearly_raw
        )

        trend["trend_classification"] = self._classify_trend(validation_table)
        trend["fallback_regression"]  = use_fallback

        return {
            "trend":             trend,
            "validation_table":  validation_table,
            "lowess_yearly":     lowess_yearly,
            "regression_coeffs": regression_coeffs,
        }

    def _apply_lowess(self, df, year_range, use_fallback):
        if df.empty:
            return {yr: {k: None for k in SCORE_KEYS} for yr in year_range}, {}

        df = df.copy()
        df["t"] = df["date"].dt.year + (df["date"].dt.month - 1) / 12

        smoothed_series = {}
        lowess_yearly   = {yr: {} for yr in year_range}

        for col, key in zip(SCORE_COLS, SCORE_KEYS):
            vals = df[col].values
            t    = df["t"].values

            if use_fallback or len(vals) < MIN_MONTHS_FOR_LOWESS:
                smoothed = vals
            else:
                smoothed = lowess(vals, t, frac=LOWESS_FRAC, return_sorted=False)

            smoothed_series[key]       = smoothed
            df[f"_smoothed_{key}"]     = smoothed

            for yr in year_range:
                yr_vals = df.loc[df["date"].dt.year == yr, f"_smoothed_{key}"].values
                lowess_yearly[yr][key] = round(float(np.mean(yr_vals)), 4) if len(yr_vals) > 0 else None

        return lowess_yearly, smoothed_series

    def _fit_regression(self, lowess_yearly, year_range):
        coeffs = {}
        years  = sorted([yr for yr in year_range if yr in lowess_yearly])

        if len(years) < 2:
            return {key: {"slope": 0.0, "intercept": 0.0, "t_min": years[0] if years else 0} for key in SCORE_KEYS}

        t_min   = years[0]
        t_arr   = np.array([yr - t_min for yr in years], dtype=float)
        weights = np.exp(REGRESSION_EXP_WEIGHT * t_arr)

        for key in SCORE_KEYS:
            y_vals, valid_t, valid_w = [], [], []
            for i, yr in enumerate(years):
                val = lowess_yearly.get(yr, {}).get(key)
                if val is not None:
                    y_vals.append(val)
                    valid_t.append(t_arr[i])
                    valid_w.append(weights[i])

            if len(y_vals) < 2:
                coeffs[key] = {"slope": 0.0, "intercept": float(y_vals[0]) if y_vals else 0.0, "t_min": t_min}
                continue

            poly = np.polyfit(np.array(valid_t), np.array(y_vals), 1, w=np.array(valid_w))
            coeffs[key] = {"slope": round(float(poly[0]), 6), "intercept": round(float(poly[1]), 4), "t_min": t_min}

        return coeffs

    def _compute_r2(self, lowess_yearly, year_range, key, coeffs):
        years  = sorted([yr for yr in year_range if yr in lowess_yearly])
        y_true = [lowess_yearly[yr].get(key) for yr in years if lowess_yearly[yr].get(key) is not None]
        if len(y_true) < 2:
            return 0.0
        t_min  = coeffs.get("t_min", years[0])
        t_arr  = np.array([yr - t_min for yr in years if lowess_yearly[yr].get(key) is not None])
        y_pred = coeffs["slope"] * t_arr + coeffs["intercept"]
        y_true = np.array(y_true)
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        return round(float(1 - ss_res / ss_tot), 4) if ss_tot != 0 else 1.0

    def _build_trend_summary(self, regression_coeffs, lowess_yearly, year_range, use_fallback):
        trend = {}
        for key, c in regression_coeffs.items():
            slope = c["slope"]
            r2    = self._compute_r2(lowess_yearly, year_range, key, c)
            trend[key] = {
                "slope":     round(slope, 4),
                "r2":        r2,
                # CRISIL: higher = better, so positive slope = improving
                "direction": "improving" if slope > 0 else "worsening",
            }
        return trend

    def _project_score(self, year, key, coeffs):
        if key not in coeffs:
            return None
        c = coeffs[key]
        return round(float(c["slope"] * (year - c["t_min"]) + c["intercept"]), 2)

    def _run_validation(self, validation_years, regression_coeffs, lowess_yearly, val_df, yearly_raw):
        table = []

        for yr in validation_years:
            projected, actual, delta, statuses = {}, {}, {}, []

            for key in SCORE_KEYS:
                proj = self._project_score(yr, key, regression_coeffs)
                projected[key] = proj

                act = yearly_raw.get(yr, {}).get(key) if yr in yearly_raw else None
                if act is None and not val_df.empty:
                    col_map = {"E": "E_Score", "S": "S_Score", "G": "G_Score", "Total": "Total_Score"}
                    yr_vals = val_df[val_df["date"].dt.year == yr][col_map[key]].values
                    if len(yr_vals) > 0:
                        act = round(float(np.mean(yr_vals)), 2)
                actual[key] = act

                if proj is not None and act is not None:
                    d = round(abs(proj - act), 2)
                    delta[key] = d
                    statuses.append(self._classify_deviation(d))
                else:
                    delta[key] = None

            if all(v is None for v in actual.values()):
                continue

            table.append({
                "year":      yr,
                "projected": projected,
                "actual":    actual,
                "delta":     delta,
                "status":    self._worst_status(statuses),
                # CRISIL: higher = better, so actual > projected = outperforming
                "direction": self._classify_direction(projected.get("Total"), actual.get("Total")),
            })

        return table

    def _classify_deviation(self, delta):
        if delta < ON_TRACK_MAX:
            return "On Track"
        elif delta < MODERATE_DRIFT_MAX:
            return "Moderate Drift"
        return "Significant Deviation"

    def _worst_status(self, statuses):
        if "Significant Deviation" in statuses: return "Significant Deviation"
        if "Moderate Drift"        in statuses: return "Moderate Drift"
        if "On Track"              in statuses: return "On Track"
        return "N/A"

    def _classify_direction(self, projected, actual):
        if projected is None or actual is None:
            return "N/A"
        # CRISIL: higher score = better, so actual > projected = outperforming
        if actual > projected:
            return "Outperforming"
        elif actual < projected:
            return "Underperforming"
        return "On Track"

    def _classify_trend(self, validation_table):
        if not validation_table:
            return TREND_SUSTAINED
        statuses   = [r["status"]    for r in validation_table]
        directions = [r["direction"] for r in validation_table]
        if all(s == "On Track"             for s in statuses):   return TREND_SUSTAINED
        if all(s == "Significant Deviation" for s in statuses):  return TREND_BROKE
        if directions.count("Outperforming") > len(directions)/2: return TREND_ACCELERATING
        return TREND_WEAKENING