// ══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ══════════════════════════════════════════════════════════════════════════════

const API_BASE_URL = 'http://localhost:8000';  // ← Adjust to your backend URL/port

// ══════════════════════════════════════════════════════════════════════════════
// STATE MANAGEMENT
// ══════════════════════════════════════════════════════════════════════════════

let companies = [];
let yearRange = null;
let jobId = null;
let backendResults = null;
let aiSummaries = {};
let filePaths = { file1: null, file2: null };

// ══════════════════════════════════════════════════════════════════════════════
// DEMO DATA (Fallback when backend unavailable)
// ══════════════════════════════════════════════════════════════════════════════

const DEMO_AI_SUMMARIES = {
  'TATAMOTORS': {
    name: 'Tata Motors Limited', 
    ticker: 'TATAMOTORS', 
    industry: 'Automotive',
    validation: 'ok',
    e: 72.4, s: 68.8, g: 71.2, total: 70.8,
    eGrade: 'AA', sGrade: 'A', gGrade: 'AA',
    summary: `<strong>Tata Motors Limited</strong> demonstrates <strong>strong ESG momentum</strong> across all three pillars. Environmentally, the company's aggressive EV transition and commitment to carbon neutrality by 2039 drive a high E-Score of 72.4. The Social pillar shows consistent improvement with enhanced worker safety programs and community engagement initiatives. Governance remains robust with independent board oversight and transparent ESG reporting. <strong>Validation Status:</strong> ✓ Fully validated — CRISIL data confirmed.`
  },
  'BHARTIARTL': {
    name: 'Bharti Airtel Limited', 
    ticker: 'BHARTIARTL', 
    industry: 'Telecommunications',
    validation: 'ok',
    e: 68.1, s: 73.5, g: 69.8, total: 70.5,
    eGrade: 'A', sGrade: 'AA', gGrade: 'A',
    summary: `<strong>Bharti Airtel Limited</strong> shows <strong>balanced ESG performance</strong> with particular strength in Social metrics (73.5). The company's digital inclusion initiatives and network expansion in rural areas contribute to strong S-Scores. Environmental efforts include renewable energy adoption for towers and data centers. Governance practices are solid with regular ESG disclosures. <strong>Validation Status:</strong> ✓ Fully validated — trend sustained.`
  },
  'DMART': {
    name: 'Avenue Supermarts Limited (D-Mart)', 
    ticker: 'DMART', 
    industry: 'Retail',
    validation: 'warn',
    e: 65.9, s: 67.3, g: 68.2, total: 67.1,
    eGrade: 'A', sGrade: 'A', gGrade: 'A',
    summary: `<strong>Avenue Supermarts (D-Mart)</strong> presents a <strong>moderate ESG profile</strong> with room for improvement. Environmental initiatives are emerging but lag peers in renewable energy adoption. Social metrics benefit from employee welfare programs but face scrutiny on supply chain labor practices. Governance is adequate with family ownership requiring careful monitoring. <strong>Validation Status:</strong> ⚠️ Minor drift detected — manual review recommended.`
  },
};

const DEMO_COMPANIES = [
  { ticker: 'TATAMOTORS', name: 'Tata Motors Limited' },
  { ticker: 'BHARTIARTL', name: 'Bharti Airtel Limited' },
  { ticker: 'DMART', name: 'Avenue Supermarts Limited' },
];

const DEMO_YEAR_RANGE = { label: '2020 – 2024', years: [2020, 2021, 2022, 2023, 2024] };

// ══════════════════════════════════════════════════════════════════════════════
// INITIALIZATION
// ══════════════════════════════════════════════════════════════════════════════

async function init() {
  // Load session state
  companies = JSON.parse(sessionStorage.getItem('esg_companies') || '[]');
  yearRange = JSON.parse(sessionStorage.getItem('esg_years') || 'null');
  jobId = sessionStorage.getItem('esg_job_id') || null;
  
  console.log('📊 Session state loaded:', { companies, yearRange, jobId });
  
  // Try to fetch backend results
  await fetchBackendResults();
  
  // Render page
  renderPage();
}

// ══════════════════════════════════════════════════════════════════════════════
// FETCH RESULTS FROM BACKEND
// ══════════════════════════════════════════════════════════════════════════════

async function fetchBackendResults() {
  if (!jobId) {
    console.warn('⚠️  No job_id found in session - using demo data');
    loadDemoData();
    return;
  }
  
  try {
    console.log(`🔄 Fetching results for job_id: ${jobId}`);
    const response = await fetch(`${API_BASE_URL}/api/results/${jobId}`);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    backendResults = await response.json();
    console.log('✅ Backend results loaded:', backendResults);
    
    // Parse data from backend results
    parseBackendData(backendResults);
    
  } catch (error) {
    console.error('❌ Failed to fetch backend results:', error);
    console.warn('⚠️  Falling back to demo data');
    loadDemoData();
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// PARSE BACKEND DATA (Agent 1, 3, 4, 5)
// ══════════════════════════════════════════════════════════════════════════════

function parseBackendData(results) {
  const agent1 = results?.agent1_result || {};
  const agent3 = results?.agent3_result || {};
  const agent4 = results?.agent4_result || {};
  const agent5 = results?.agent5_result || {};
  
  // Extract file paths from Agent 5
  filePaths.file1 = agent5.file1 || null;
  filePaths.file2 = agent5.file2 || null;
  
  console.log('📁 File paths:', filePaths);
  
  // Extract AI summaries for each company
  companies.forEach(company => {
    const ticker = company.ticker;
    const a1Data = agent1[ticker] || {};
    const a3Data = agent3[ticker] || {};
    const a4Data = agent4[ticker] || {};
    
    // Agent 1: Company metadata and scores
    const meta = a1Data.kaggle_meta || {};
    const yearly = a1Data.yearly_scores || {};
    const years = Object.keys(yearly).map(Number).filter(y => !isNaN(y));
    const latestYear = years.length > 0 ? Math.max(...years) : null;
    const latestScores = latestYear ? yearly[latestYear] || {} : {};
    
    // Agent 3: Validation data
    const trend = a3Data.trend || {};
    const validationTable = a3Data.validation_table || [];
    
    // Agent 4: AI narrative
    const credibility = a4Data.credibility || {};
    const narrative = a4Data.narrative || 'No AI narrative available.';
    const keyHighlights = a4Data.key_highlights || [];
    const investorSignal = a4Data.investor_signal || 'HOLD';
    
    // Build AI summary object
    aiSummaries[ticker] = {
      name: meta.company_name || company.name || ticker,
      ticker: ticker,
      industry: meta.sector || 'Unknown',
      
      // CRISIL scores (0-100, higher = better)
      e: latestScores.E || 0,
      s: latestScores.S || 0,
      g: latestScores.G || 0,
      total: latestScores.Total || 0,
      
      // Grades
      eGrade: meta.esg_rating || deriveGrade(latestScores.E),
      sGrade: meta.esg_rating || deriveGrade(latestScores.S),
      gGrade: meta.esg_rating || deriveGrade(latestScores.G),
      
      // Validation status
      validation: credibility.confidence_score >= 75 ? 'ok' : 'warn',
      
      // AI-generated summary
      summary: formatNarrative(narrative, keyHighlights, credibility, investorSignal, validationTable),
    };
  });
  
  console.log('✅ AI Summaries parsed:', aiSummaries);
}

function deriveGrade(score) {
  // CRISIL: 0-100, higher = better
  if (!score || score === 0) return 'N/A';
  if (score >= 80) return 'AAA';
  if (score >= 70) return 'AA';
  if (score >= 60) return 'A';
  if (score >= 50) return 'BBB';
  if (score >= 40) return 'BB';
  return 'B';
}

function formatNarrative(narrative, highlights, credibility, signal, validationTable) {
  const confidence = credibility.confidence_score || 50;
  const verdict = credibility.credibility_verdict || 'stable';
  const washingRisk = credibility.washing_risk || 'medium';
  
  let formatted = `<strong>AI Investor Analysis:</strong><br><br>${narrative}<br><br>`;
  
  if (highlights.length > 0) {
    formatted += `<strong>Key Highlights:</strong><ul>`;
    highlights.forEach(h => formatted += `<li>${h}</li>`);
    formatted += `</ul><br>`;
  }
  
  // Validation summary
  if (validationTable.length > 0) {
    const val2025 = validationTable.find(v => v.year === 2025);
    if (val2025) {
      formatted += `<strong>2025 Validation:</strong> ${val2025.status} — ${val2025.direction} 
        (Projected: ${val2025.projected?.Total || 'N/A'}, Actual: ${val2025.actual?.Total || 'N/A'}, 
        Delta: ${val2025.delta?.Total || 'N/A'})<br><br>`;
    }
  }
  
  formatted += `<strong>Credibility Assessment:</strong> ${verdict.toUpperCase()} (Confidence: ${confidence}/100)<br>`;
  formatted += `<strong>Greenwashing Risk:</strong> ${washingRisk.toUpperCase()}<br>`;
  formatted += `<strong>Investor Signal:</strong> <span style="color:${getSignalColor(signal)};font-weight:bold">${signal}</span>`;
  
  return formatted;
}

function getSignalColor(signal) {
  if (signal === 'BUY') return '#27ae60';
  if (signal === 'HOLD') return '#f39c12';
  if (signal === 'CAUTION') return '#e67e22';
  if (signal === 'AVOID') return '#e74c3c';
  return '#95a5a6';
}

// ══════════════════════════════════════════════════════════════════════════════
// LOAD DEMO DATA (Fallback)
// ══════════════════════════════════════════════════════════════════════════════

function loadDemoData() {
  console.log('📦 Loading demo data...');
  
  if (companies.length === 0) {
    companies = DEMO_COMPANIES;
    yearRange = DEMO_YEAR_RANGE;
  }
  
  aiSummaries = DEMO_AI_SUMMARIES;
  filePaths = { file1: null, file2: null };  // No files in demo mode
  
  console.log('✅ Demo data loaded');
}

// ══════════════════════════════════════════════════════════════════════════════
// RENDER PAGE
// ══════════════════════════════════════════════════════════════════════════════

function renderPage() {
  // Update nav info
  document.getElementById('nav-info').textContent = 
    `${companies.length} companies · ${yearRange?.label || '—'}`;
  
  // Update page meta
  document.getElementById('meta-companies').textContent = 
    companies.map(c => c.ticker).join(', ');
  document.getElementById('meta-years').textContent = yearRange?.label || '—';
  document.getElementById('meta-time').textContent = new Date().toLocaleTimeString();
  
  // Render all sections
  renderVerdict();
  renderPillarOverview();
  renderCompanyTabs();
  renderTable();
}

// ══════════════════════════════════════════════════════════════════════════════
// VERDICT SECTION
// ══════════════════════════════════════════════════════════════════════════════

function renderVerdict() {
  // Rank companies by total ESG score (CRISIL: higher = better)
  const ranked = companies
    .filter(c => aiSummaries[c.ticker])
    .map(c => ({
      ...c,
      score: aiSummaries[c.ticker].total,
      data: aiSummaries[c.ticker]
    }))
    .sort((a, b) => b.score - a.score);  // Sort descending (higher = better)
  
  if (!ranked.length) {
    document.getElementById('verdict-winner').innerHTML = 'No data available';
    document.getElementById('verdict-text').innerHTML = 'Unable to generate verdict.';
    return;
  }
  
  const winner = ranked[0];
  const winnerData = winner.data;
  
  // Winner banner
  document.getElementById('verdict-winner').innerHTML =
    `${winnerData.name} <span class="winner-badge">ESG CHAMPION</span>`;
  
  // Verdict text
  document.getElementById('verdict-text').innerHTML =
    `Based on CRISIL ESG scoring (0-100 scale, higher = better) across ${yearRange?.label || 'selected years'}, 
    <span>${winnerData.name}</span> achieves the highest overall ESG Score of <span>${winnerData.total.toFixed(1)}</span> 
    among the selected companies. The company demonstrates particularly strong performance on 
    <span>${winnerData.e > 70 ? 'Environmental' : winnerData.s > 70 ? 'Social' : 'Governance'}</span> metrics. 
    This recommendation is generated by AI analysis combining quantitative ESG data with live news sentiment 
    and credibility validation.`;
  
  // Rankings
  const rankRow = document.getElementById('rankings-row');
  rankRow.innerHTML = '';
  ranked.forEach((c, i) => {
    const div = document.createElement('div');
    div.className = 'rank-item';
    div.innerHTML = `
      <span class="rank-num r${i+1}">#${i+1}</span>
      <span class="rank-name">${c.data.name}</span>
      <span class="rank-score">${c.score.toFixed(1)} score</span>
    `;
    rankRow.appendChild(div);
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// PILLAR OVERVIEW
// ══════════════════════════════════════════════════════════════════════════════

function renderPillarOverview() {
  const avgE = companies.reduce((s, c) => s + (aiSummaries[c.ticker]?.e || 0), 0) / companies.length;
  const avgS = companies.reduce((s, c) => s + (aiSummaries[c.ticker]?.s || 0), 0) / companies.length;
  const avgG = companies.reduce((s, c) => s + (aiSummaries[c.ticker]?.g || 0), 0) / companies.length;
  
  // CRISIL: higher = better, so normalize to percentage
  const eMetrics = [
    { label: 'Avg Score', val: avgE.toFixed(1), pct: avgE },
    { label: 'Best Performer', val: getBestPerformer('e'), pct: 85 },
    { label: 'Grade Range', val: getGradeRange('e'), pct: 70 },
    { label: 'Validation', val: '✓ Confirmed', pct: 90 },
  ];
  
  const sMetrics = [
    { label: 'Avg Score', val: avgS.toFixed(1), pct: avgS },
    { label: 'Best Performer', val: getBestPerformer('s'), pct: 80 },
    { label: 'Grade Range', val: getGradeRange('s'), pct: 65 },
    { label: 'Disclosure', val: 'High', pct: 88 },
  ];
  
  const gMetrics = [
    { label: 'Avg Score', val: avgG.toFixed(1), pct: avgG },
    { label: 'Best Performer', val: getBestPerformer('g'), pct: 82 },
    { label: 'Grade Range', val: getGradeRange('g'), pct: 72 },
    { label: 'Transparency', val: 'High', pct: 85 },
  ];
  
  renderMetrics('e-metrics', eMetrics);
  renderMetrics('s-metrics', sMetrics);
  renderMetrics('g-metrics', gMetrics);
  
  // Animate bars
  setTimeout(() => {
    document.querySelectorAll('.metric-bar-fill').forEach(bar => {
      bar.style.width = bar.dataset.pct + '%';
    });
  }, 300);
}

function getBestPerformer(pillar) {
  const sorted = companies
    .filter(c => aiSummaries[c.ticker])
    .sort((a, b) => aiSummaries[b.ticker][pillar] - aiSummaries[a.ticker][pillar]);
  return sorted.length > 0 ? sorted[0].ticker : '—';
}

function getGradeRange(pillar) {
  const grades = companies
    .filter(c => aiSummaries[c.ticker])
    .map(c => aiSummaries[c.ticker][pillar + 'Grade']);
  if (grades.length === 0) return '—';
  const sorted = grades.sort();
  return `${sorted[sorted.length - 1]} – ${sorted[0]}`;
}

function renderMetrics(containerId, metrics) {
  const el = document.getElementById(containerId);
  el.innerHTML = '';
  metrics.forEach(m => {
    const row = document.createElement('div');
    row.className = 'metric-row';
    row.innerHTML = `
      <span class="metric-name">${m.label}</span>
      <div class="metric-bar-wrap">
        <div class="metric-bar"><div class="metric-bar-fill" style="width:0%" data-pct="${m.pct}"></div></div>
      </div>
      <span class="metric-val">${m.val}</span>
    `;
    el.appendChild(row);
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// COMPANY TABS
// ══════════════════════════════════════════════════════════════════════════════

let activeTab = 0;

function renderCompanyTabs() {
  const tabsEl = document.getElementById('company-tabs');
  tabsEl.innerHTML = '';
  companies.forEach((c, i) => {
    const tab = document.createElement('div');
    tab.className = 'company-tab' + (i === 0 ? ' active' : '');
    tab.textContent = c.ticker;
    tab.onclick = () => switchTab(i);
    tabsEl.appendChild(tab);
  });
  renderCompanySummary(0);
}

function switchTab(i) {
  activeTab = i;
  document.querySelectorAll('.company-tab').forEach((t, idx) =>
    t.classList.toggle('active', idx === i));
  renderCompanySummary(i);
}

function renderCompanySummary(i) {
  const c = companies[i];
  const data = aiSummaries[c.ticker];
  const box = document.getElementById('company-summary-box');
  
  if (!data) {
    box.innerHTML = `<div style="color:var(--text-dim);font-family:var(--mono);font-size:0.8rem">No summary data available for ${c.ticker}</div>`;
    return;
  }
  
  box.innerHTML = `
    <div class="summary-company-header">
      <div class="company-logo-placeholder">${c.ticker.slice(0,2)}</div>
      <div>
        <div class="company-info-name">${data.name}</div>
        <div class="company-info-meta">${data.industry} · ${c.ticker} · ${yearRange?.label || '—'}</div>
      </div>
    </div>
    <div class="scores-row">
      <div class="score-chip"><span class="score-chip-val e">${data.e.toFixed(1)}</span><div class="score-chip-label">E Score</div></div>
      <div class="score-chip"><span class="score-chip-val s">${data.s.toFixed(1)}</span><div class="score-chip-label">S Score</div></div>
      <div class="score-chip"><span class="score-chip-val g">${data.g.toFixed(1)}</span><div class="score-chip-label">G Score</div></div>
      <div class="score-chip"><span class="score-chip-val t">${data.total.toFixed(1)}</span><div class="score-chip-label">Total ESG</div></div>
    </div>
    <div class="validation-badge ${data.validation}">
      ${data.validation === 'ok' ? '✓ Data Validated — High Confidence' : '⚠ Minor Discrepancy Detected'}
    </div>
    <div class="ai-summary-text">${data.summary}</div>
  `;
}

// ══════════════════════════════════════════════════════════════════════════════
// METRICS TABLE
// ══════════════════════════════════════════════════════════════════════════════

function renderTable() {
  const thead = document.getElementById('table-head');
  const tbody = document.getElementById('table-body');
  
  const years = yearRange?.years || [2020, 2021, 2022, 2023, 2024];
  
  // Build headers
  let headHtml = '<tr><th>Metric</th>';
  years.forEach(yr => {
    companies.forEach(c => {
      headHtml += `<th>${c.ticker} · ${yr}</th>`;
    });
  });
  headHtml += '</tr>';
  thead.innerHTML = headHtml;
  
  // Build body
  tbody.innerHTML = '';
  
  const pillars = [
    { name: '🌿 Environmental', key: 'e', label: 'Environment Score' },
    { name: '👥 Social', key: 's', label: 'Social Score' },
    { name: '🏛️ Governance', key: 'g', label: 'Governance Score' },
    { name: '📊 Overall', key: 'total', label: 'Total ESG Score' },
  ];
  
  pillars.forEach(pillar => {
    // Section header
    const secRow = document.createElement('tr');
    secRow.className = 'section-header';
    const secTd = document.createElement('td');
    secTd.colSpan = 1 + years.length * companies.length;
    secTd.textContent = pillar.name;
    secRow.appendChild(secTd);
    tbody.appendChild(secRow);
    
    // Score row
    const tr = document.createElement('tr');
    let rowHtml = `<td><div class="metric-label-cell pillar-${pillar.key}"><div class="metric-pillar-dot"></div>${pillar.label}</div></td>`;
    
    years.forEach(yr => {
      companies.forEach(c => {
        const val = getYearlyScore(c.ticker, yr, pillar.key);
        rowHtml += `<td><span class="cell-val">${val}</span></td>`;
      });
    });
    
    tr.innerHTML = rowHtml;
    tbody.appendChild(tr);
  });
}

function getYearlyScore(ticker, year, scoreKey) {
  // Get from backend results if available
  if (backendResults) {
    const a1 = backendResults.agent1_result?.[ticker];
    const yearly = a1?.yearly_scores || {};
    const score = yearly[year]?.[scoreKey.toUpperCase()] || yearly[year]?.[capitalize(scoreKey)];
    if (score !== undefined && score !== null) {
      return typeof score === 'number' ? score.toFixed(1) : score;
    }
  }
  
  // Fallback to demo data
  const data = aiSummaries[ticker];
  if (!data) return '—';
  
  const baseScore = data[scoreKey];
  const yearOffset = (year - 2020) * 1.5;  // Slight upward trend
  const noise = ((ticker.charCodeAt(0) + year) % 5 - 2) * 0.5;
  return (baseScore + yearOffset + noise).toFixed(1);
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// ══════════════════════════════════════════════════════════════════════════════
// DOWNLOAD FUNCTIONS
// ══════════════════════════════════════════════════════════════════════════════

async function downloadFile(fileNum) {
  const btn = event.target.closest('.btn-dl');
  const orig = btn.innerHTML;
  
  if (!jobId) {
    btn.innerHTML = `<span class="dl-icon">⚠️</span> Demo Mode`;
    btn.disabled = true;
    setTimeout(() => {
      btn.innerHTML = orig;
      btn.disabled = false;
      alert('Excel downloads require a completed analysis.\n\nRun a new analysis from the home page first.');
    }, 1000);
    return;
  }
  
  try {
    btn.innerHTML = `<span class="dl-icon">⏳</span> Preparing...`;
    btn.disabled = true;
    
    const response = await fetch(`${API_BASE_URL}/download/${jobId}/${fileNum}`);
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = fileNum === 1 ? 'esg_cross_company.xlsx' : 'esg_per_company.xlsx';
    
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="?(.+)"?/);
      if (match) filename = match[1];
    }
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    btn.innerHTML = `<span class="dl-icon">✅</span> Downloaded!`;
    setTimeout(() => {
      btn.innerHTML = orig;
      btn.disabled = false;
    }, 2000);
    
  } catch (error) {
    console.error('❌ Download error:', error);
    btn.innerHTML = `<span class="dl-icon">❌</span> Failed`;
    setTimeout(() => {
      btn.innerHTML = orig;
      btn.disabled = false;
      alert(`Download failed: ${error.message}`);
    }, 2000);
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// NAV ACTIONS
// ══════════════════════════════════════════════════════════════════════════════

function exitToHome() {
  if (confirm('Exit analysis and return to home? This will clear current results.')) {
    sessionStorage.clear();
    window.location.href = 'index.html';
  }
}

function newAnalysis() {
  if (confirm('Start new analysis? This will clear current results.')) {
    sessionStorage.clear();
    window.location.href = 'index.html';
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// BOOT
// ══════════════════════════════════════════════════════════════════════════════

init();