# backend/config/thresholds.py
# All classification thresholds in one place.
# Change values here — no agent code needs to change.

# ── DEVIATION CLASSIFICATION (Agent 3) ───────────────────────────────────────
ON_TRACK_MAX          = 2.0   # delta < 2.0  → On Track
MODERATE_DRIFT_MAX    = 4.0   # delta 2.0–4.0 → Moderate Drift
                               # delta > 4.0  → Significant Deviation

# ── CONFIDENCE SCORE ROUTING (Agent 4) ───────────────────────────────────────
CONFIDENCE_COMMENDATORY = 70   # score >= 70  → commendatory narrative
CONFIDENCE_BALANCED     = 40   # score 40–69  → balanced narrative
                                # score < 40   → cautionary narrative

# ── INVESTOR SIGNAL MAPPING ───────────────────────────────────────────────────
# Used by Agent 4 LLM Call 3 prompt routing
SIGNAL_BUY     = "BUY"
SIGNAL_HOLD    = "HOLD"
SIGNAL_CAUTION = "CAUTION"
SIGNAL_AVOID   = "AVOID"

# ── TREND CLASSIFICATION (Agent 3) ───────────────────────────────────────────
TREND_SUSTAINED    = "Sustained"
TREND_WEAKENING    = "Weakening"
TREND_BROKE        = "Broke"
TREND_ACCELERATING = "Accelerating"

# ── LOWESS PARAMETERS (Agent 3) ──────────────────────────────────────────────
LOWESS_FRAC            = 0.3
REGRESSION_EXP_WEIGHT  = 0.5   # w_t = exp(REGRESSION_EXP_WEIGHT * (t - t_min))
MIN_MONTHS_FOR_LOWESS  = 12    # fallback to simple regression if fewer points
