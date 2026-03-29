#CRISIL ESG scores are 0-100 where HIGHER = BETTER ESG performance.

NEWS_INTELLIGENCE_PROMPT = """
You are an ESG analyst. Analyze the following news article excerpts about {company_name} ({ticker}),
a company in the {industry} sector.

NEWS EXCERPTS:
{rag_chunks}

RECENT CRISIL ESG SCORES (scale 0-100, higher = better ESG performance):
- Environment Score: {e_score}
- Social Score: {s_score}
- Governance Score: {g_score}
- Total ESG Score: {total_score}

Return ONLY a valid JSON object with exactly these keys:
{{
  "positive_findings": ["<finding 1>", "<finding 2>"],
  "negative_findings": ["<finding 1>", "<finding 2>"],
  "governance_flags": ["<flag 1>"],
  "overall_news_sentiment": "<positive|mixed|negative|insufficient_data>"
}}

Rules:
- positive_findings: max 5 items, each under 30 words
- negative_findings: max 5 items, each under 30 words
- governance_flags: max 3 items, each under 20 words
- overall_news_sentiment: must be exactly one of the four options
- Return JSON only. No preamble, no explanation, no markdown.
"""

CREDIBILITY_VALIDATION_PROMPT = """
You are an ESG credibility analyst. Assess whether {company_name} ({ticker})'s CRISIL ESG scores
are credible based on quantitative trends and qualitative news evidence.

IMPORTANT: CRISIL scores are on a scale of 0-100 where HIGHER scores mean BETTER ESG performance.
A positive regression slope means ESG performance is IMPROVING.

YEARLY CRISIL ESG SCORES (0-100, higher = better):
{yearly_scores}

REGRESSION ANALYSIS (positive slope = improving trend):
{regression_summary}

ADAPTIVE FORWARD VALIDATION:
{validation_table}

CRISIL RATING AND CATEGORY:
{crisil_rating}

NEWS INTELLIGENCE (from previous analysis):
- Positive Findings: {positive_findings}
- Negative Findings: {negative_findings}
- Governance Flags: {governance_flags}
- Overall Sentiment: {overall_news_sentiment}

Return ONLY a valid JSON object with exactly these keys:
{{
  "confidence_score": <integer 0-100>,
  "credibility_verdict": "<good|stable|bad|washing>",
  "supporting_evidence": ["<evidence 1>", "<evidence 2>"],
  "contradicting_evidence": ["<evidence 1>", "<evidence 2>"],
  "washing_risk": "<low|medium|high>"
}}

Rules:
- confidence_score: 0 = completely untrustworthy, 100 = fully credible
- credibility_verdict: good = scores supported by news, stable = neutral, bad = scores not supported by news, washing = likely greenwashing
- supporting_evidence: max 3 items
- contradicting_evidence: max 3 items
- washing_risk: low/medium/high — high if company claims high ESG scores but news shows controversies
- Return JSON only. No preamble, no explanation, no markdown.
"""

# ── LLM CALL 3A — COMMENDATORY NARRATIVE (confidence >= 70) ──────────────────

NARRATIVE_COMMENDATORY_PROMPT = """
You are writing an investor ESG report section for {company_name} ({ticker}).
This company has a HIGH credibility score of {confidence_score}/100, indicating strong
alignment between its reported CRISIL ESG scores and real-world evidence.

CRISIL ESG SUMMARY (0-100 scale, higher = better):
{esg_summary}

TREND: {trend_classification}
KEY POSITIVE FINDINGS: {positive_findings}
INVESTOR SIGNAL: {investor_signal}

Write a commendatory but factual 2-3 paragraph investor narrative (150-400 words).
Highlight genuine ESG achievements, validate the positive trend, and explain why the signal is {investor_signal}.
Be analytical, not promotional. Reference specific CRISIL scores where relevant.

Return ONLY a valid JSON object:
{{
  "narrative": "<2-3 paragraphs>",
  "key_highlights": ["<highlight 1>", "<highlight 2>", "<highlight 3>"],
  "investor_signal": "{investor_signal}"
}}

Rules:
- narrative: 150-400 words, 2-3 paragraphs
- key_highlights: exactly 3 items, each under 20 words
- investor_signal: must be exactly {investor_signal}
- Return JSON only. No preamble, no markdown.
"""

# ── LLM CALL 3B — BALANCED NARRATIVE (confidence 40-69) ──────────────────────

NARRATIVE_BALANCED_PROMPT = """
You are writing an investor ESG report section for {company_name} ({ticker}).
This company has a MODERATE credibility score of {confidence_score}/100, indicating
partial alignment between its reported CRISIL ESG scores and real-world evidence.

CRISIL ESG SUMMARY (0-100 scale, higher = better):
{esg_summary}

TREND: {trend_classification}
POSITIVE FINDINGS: {positive_findings}
NEGATIVE FINDINGS: {negative_findings}
INVESTOR SIGNAL: {investor_signal}

Write a balanced, objective 2-3 paragraph investor narrative (150-400 words).
Acknowledge both strengths and areas of concern. Be neutral and analytical.
Reference specific CRISIL scores and news findings.

Return ONLY a valid JSON object:
{{
  "narrative": "<2-3 paragraphs>",
  "key_highlights": ["<highlight 1>", "<highlight 2>", "<highlight 3>"],
  "investor_signal": "{investor_signal}"
}}

Rules:
- narrative: 150-400 words, 2-3 paragraphs
- key_highlights: exactly 3 items, each under 20 words
- investor_signal: must be exactly {investor_signal}
- Return JSON only. No preamble, no markdown.
"""

# ── LLM CALL 3C — CAUTIONARY NARRATIVE (confidence < 40) ─────────────────────

NARRATIVE_CAUTIONARY_PROMPT = """
You are writing an investor ESG report section for {company_name} ({ticker}).
This company has a LOW credibility score of {confidence_score}/100, indicating
significant gaps or contradictions between reported CRISIL ESG scores and real-world evidence.

CRISIL ESG SUMMARY (0-100 scale, higher = better):
{esg_summary}

TREND: {trend_classification}
NEGATIVE FINDINGS: {negative_findings}
GOVERNANCE FLAGS: {governance_flags}
WASHING RISK: {washing_risk}
INVESTOR SIGNAL: {investor_signal}

Write a cautionary but professional 2-3 paragraph investor narrative (150-400 words).
Flag specific ESG concerns, note the credibility gap between reported scores and news evidence,
and explain the {investor_signal} signal clearly. Do not be alarmist — be analytical and evidence-based.

Return ONLY a valid JSON object:
{{
  "narrative": "<2-3 paragraphs>",
  "key_highlights": ["<highlight 1>", "<highlight 2>", "<highlight 3>"],
  "investor_signal": "{investor_signal}"
}}

Rules:
- narrative: 150-400 words, 2-3 paragraphs
- key_highlights: exactly 3 items, each under 20 words
- investor_signal: must be exactly {investor_signal}
- Return JSON only. No preamble, no markdown.
"""

# ── LLM CALL 4 — SYNTHESIS VERDICT ───────────────────────────────────────────

SYNTHESIS_VERDICT_PROMPT = """
You are producing the final comparative ESG verdict for an analysis of {num_companies} Indian companies
rated by CRISIL ESG (scale 0-100, higher = better ESG performance).

COMPANY SUMMARIES:
{company_summaries}

Based on CRISIL ESG scores (higher = better), confidence scores, investor signals,
and trend classifications, produce a final comparative verdict.

Return ONLY a valid JSON object:
{{
  "winner": "<ticker>",
  "winner_name": "<company name>",
  "rankings": ["<ticker 1>", "<ticker 2>", ...],
  "verdict_text": "<3-4 sentence comparative summary>",
  "most_improved": "<ticker>",
  "biggest_risk": "<ticker>"
}}

Rules:
- winner: ticker of company with best overall CRISIL ESG profile (highest score + improving trend)
- rankings: ordered from best to worst ESG performance (highest CRISIL score first)
- verdict_text: 3-4 sentences maximum, factual and comparative
- most_improved: ticker showing strongest positive trend (biggest score increase)
- biggest_risk: ticker with lowest CRISIL score or lowest credibility
- Return JSON only. No preamble, no markdown.
"""