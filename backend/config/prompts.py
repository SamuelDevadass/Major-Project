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
# --- AGENT 2: BRSR EXTRACTION PROMPT ---
# Goal: Reduce 50+ pages of Docling Markdown into a high-density JSON fact sheet.
BRSR_EXTRACTION_PROMPT = """
You are a specialized ESG Data Extractor. 
Your task is to extract specific regulatory data from the provided BRSR Markdown text.

INSTRUCTIONS:
1. Extract the following metrics: 
   - Scope 1 and Scope 2 Emissions (MTCO2e).
   - Energy Intensity (per rupee of turnover).
   - Water consumption and recycling %.
   - Employee Gender Diversity (Workforce and Board).
   - Safety: Number of fatalities or high-consequence injuries.
2. Use the source tag [B1] for EVERY value extracted.
3. If a value is missing, write "Not Disclosed".
4. Return the output in a clean, structured JSON format.

CONTEXT FROM BRSR [B1]:
{context}

RETURN ONLY JSON.
"""

CREDIBILITY_VALIDATION_PROMPT = """
You are an ESG credibility analyst. Assess whether {company_name} ({ticker})'s CRISIL ESG scores
are credible based on quantitative trends, official BRSR disclosures, and qualitative news.

IMPORTANT: 
- CRISIL scores (0-100): Higher = Better.
- BRSR Data [B1]: Official regulatory disclosures (High Truth).
- News Intelligence [N1, N2...]: Public sentiment and controversies (High Recency).

YEARLY CRISIL ESG SCORES: {yearly_scores}
REGRESSION SUMMARY: {regression_summary}

OFFICIAL BRSR AUDIT [B1]: 
{official_fact_sheet}

NEWS INTELLIGENCE:
- Findings: {positive_findings} | {negative_findings}
- Governance Flags: {governance_flags}

Return ONLY a valid JSON object:
{{
  "confidence_score": <0-100>,
  "credibility_verdict": "<good|stable|bad|washing>",
  "supporting_evidence": ["<evidence with [B1] or [N1]>"],
  "contradicting_evidence": ["<evidence with [B1] or [N1]>"],
  "washing_risk": "<low|medium|high>"
}}

Rules:
- High confidence requires alignment between [B1] (Official) and [N1] (News).
- 'washing' verdict applies if CRISIL/BRSR scores are high but News [N1] shows active controversies.
- Every evidence item MUST cite [B1] or [Nx].
"""

# ── LLM CALL 3A — COMMENDATORY NARRATIVE (confidence >= 70) ──────────────────

NARRATIVE_COMMENDATORY_PROMPT = """
You are writing a high-confidence ESG Investor Report for {company_name} ({ticker}).
Confidence Score: {confidence_score}/100. (High alignment between scores and evidence).

DATA ASSETS:
- Official BRSR Audit [B1]: {official_fact_sheet}
- News Intelligence [N1, N2...]: {positive_findings}
- CRISIL Trend: {trend_classification} ({esg_summary})

TASK:
Write 2-3 paragraphs (150-400 words) validating this company's ESG leadership.
1. Highlight how official disclosures [B1] confirm the strong CRISIL scores.
2. Reference positive real-world evidence [N1] that reinforces the [B1] data.
3. Explain why the signal is {investor_signal} based on this dual-verification.
4. REQUIREMENT: You MUST use [B1] for official data and [N1, N2...] for news.

Return ONLY JSON:
{{
  "narrative": "<text with citations [B1][N1]>",
  "key_highlights": ["<highlight citing [B1] or [N1]>"],
  "investor_signal": "{investor_signal}"
}}
"""

# ── LLM CALL 3B — BALANCED NARRATIVE (confidence 40-69) ──────────────────────

NARRATIVE_BALANCED_PROMPT = """
You are writing a professional investor report for {company_name} ({ticker}).
Credibility Score: {confidence_score}/100.

DATA SOURCES:
- Official BRSR Highlights: {official_fact_sheet}
- News Highlights: {positive_findings}, {negative_findings}

Write a 2-3 paragraph narrative (150-400 words).
1. Analyze the CRISIL trend vs official BRSR data [B1].
2. Contrast with real-world news findings [N1, N2...].
3. You MUST include the bracketed citations [B1] and [Nx] in the text.

Return JSON:
{{
  "narrative": "<text with citations [B1][N1]>",
  "key_highlights": ["<highlight 1>", "<highlight 2>", "<highlight 3>"],
  "investor_signal": "{investor_signal}"
}}
"""

# ── LLM CALL 3C — CAUTIONARY NARRATIVE (confidence < 40) ─────────────────────

NARRATIVE_CAUTIONARY_PROMPT = """
You are writing a cautionary ESG Audit for {company_name} ({ticker}).
Confidence Score: {confidence_score}/100. (Significant contradictions detected).

DATA ASSETS:
- Official BRSR Audit [B1]: {official_fact_sheet}
- News/Controversies [N1, N2...]: {negative_findings}
- Governance Flags: {governance_flags}
- Washing Risk: {washing_risk}

TASK:
Write 2-3 professional, cautionary paragraphs (150-400 words).
1. Flag the discrepancy between the reported CRISIL trend and the news evidence [N1].
2. Identify specific gaps in the official BRSR disclosure [B1] vs. external reality.
3. Explain the {investor_signal} signal as a result of these unverified claims.
4. REQUIREMENT: You MUST use [B1] and [N1, N2...] to anchor your warnings.

Return ONLY JSON:
{{
  "narrative": "<text with citations [B1][N1]>",
  "key_highlights": ["<highlight citing the controversy source>"],
  "investor_signal": "{investor_signal}"
}}
"""

# ── LLM CALL 4 — SYNTHESIS VERDICT ───────────────────────────────────────────

SYNTHESIS_VERDICT_PROMPT = """
Analyze {num_companies} companies. Compare their CRISIL scores and the 
reliability of their official [B1] vs. news [N1] data.

COMPANY SUMMARIES:
{company_summaries}

Return ONLY JSON:
{{
  "winner": "<ticker>",
  "winner_reason": "Highest CRISIL score verified by strong [B1] alignment.",
  "rankings": ["<ticker 1>", "<ticker 2>"],
  "verdict_text": "<3-4 sentences comparing official [B1] vs news [N1] across the group.>",
  "biggest_risk": "<ticker with most [N1] controversies vs high [B1] claims>"
}}
"""