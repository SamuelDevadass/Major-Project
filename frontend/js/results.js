// ══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ══════════════════════════════════════════════════════════════════════════════

const API_BASE_URL = 'http://localhost:8000'; 

// ══════════════════════════════════════════════════════════════════════════════
// STATE MANAGEMENT
// ══════════════════════════════════════════════════════════════════════════════

let companies = [];
let yearRange = null;
let jobId = null;
let backendResults = null;
let aiSummaries = {};

// ══════════════════════════════════════════════════════════════════════════════
// INITIALIZATION
// ══════════════════════════════════════════════════════════════════════════════

async function init() {
  // Load session state from index.js
  companies = JSON.parse(sessionStorage.getItem('esg_companies') || '[]');
  yearRange = JSON.parse(sessionStorage.getItem('esg_years') || 'null');
  jobId = sessionStorage.getItem('esg_job_id') || null;
  
  console.log('📊 Session state loaded:', { companies, yearRange, jobId });
  
  if (!jobId) {
    console.warn('⚠️ No job_id found - showing demo data');
    loadDemoData();
  } else {
    await fetchBackendResults();
  }
  
  renderPage();
}

// ══════════════════════════════════════════════════════════════════════════════
// FETCH RESULTS (Route Adjusted to match standard FastAPI status/results)
// ══════════════════════════════════════════════════════════════════════════════

async function fetchBackendResults() {
  try {
    // Note: Adjusted path to /results/${jobId} to match typical backend patterns
    const response = await fetch(`${API_BASE_URL}/results/${jobId}`);
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    
    backendResults = await response.json();
    parseBackendData(backendResults);
    
  } catch (error) {
    console.error('❌ Fetch failed:', error);
    loadDemoData();
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// PARSE AGENT DATA
// ══════════════════════════════════════════════════════════════════════════════

function parseBackendData(data) {
  // 1. Update the Global AI Verdict (The Synthesis)
  if (data.verdict) {
    const v = data.verdict;
    // Assuming you have these IDs in your HTML for the comparative summary
    const verdictEl = document.getElementById('ai-verdict-text');
    const winnerEl = document.getElementById('winner-name');
    
    if (verdictEl) verdictEl.innerText = v.verdict_text || "Comparative analysis complete.";
    if (winnerEl) winnerEl.innerText = v.winner_name || "N/A";
  }

  // 2. Process each company using the 'per_company' map from Python
  const perCompany = data.per_company || {};

  companies.forEach(company => {
    const ticker = company.ticker;
    const details = perCompany[ticker] || {};
    
    // In your orchestrator, you mapped actual_scores to "yearly_scores"
    const scores = details.yearly_scores || { E: 0, S: 0, G: 0, Total: 0 };
    const meta = details.kaggle_meta || {};

    // 3. Build the summary object for the UI
    aiSummaries[ticker] = {
      name: meta.company_name || company.name,
      ticker: ticker,
      industry: meta.sector || 'Industrial',
      e: parseFloat(scores.E || 0),
      s: parseFloat(scores.S || 0),
      g: parseFloat(scores.G || 0),
      total: parseFloat(scores.Total || 0),
      // Use the logic you defined in Agent 4
      validation: (details.credibility?.confidence_score > 70) ? 'ok' : 'warn',
      // Pass the narrative data to your formatter
      summary: formatNarrative(
        details.narrative, 
        details.key_highlights, 
        details.credibility, 
        details.investor_signal
      )
    };
  });
}

function formatNarrative(narrative, highlights, credibility, signal) {
  let html = `<p>${narrative || 'Analysis pending...'}</p>`;
  if (highlights?.length) {
    html += `<strong>Key Highlights:</strong><ul>${highlights.map(h => `<li>${h}</li>`).join('')}</ul>`;
  }
  html += `<br><strong>Investor Signal:</strong> <span style="color:${getSignalColor(signal)}">${signal || 'HOLD'}</span>`;
  return html;
}

function getSignalColor(signal) {
  const colors = { 'BUY': '#27ae60', 'HOLD': '#f39c12', 'CAUTION': '#e67e22', 'AVOID': '#e74c3c' };
  return colors[signal] || '#95a5a6';
}

// ══════════════════════════════════════════════════════════════════════════════
// RENDER ENGINE
// ══════════════════════════════════════════════════════════════════════════════

function renderPage() {
  const navInfo = document.getElementById('nav-info');
  if(navInfo) navInfo.textContent = `${companies.length} Companies Analyzed`;

  renderVerdict();
  renderPillarOverview();
  renderCompanyTabs();
  renderTable();
}

function renderVerdict() {
  const ranked = Object.values(aiSummaries).sort((a, b) => b.total - a.total);
  if (!ranked.length) return;

  const winner = ranked[0];
  document.getElementById('verdict-winner').innerHTML = `${winner.name} <span class="winner-badge">ESG LEADER</span>`;
  document.getElementById('verdict-text').textContent = `${winner.name} outperforms peers with a composite score of ${winner.total.toFixed(1)}.`;

  const rankRow = document.getElementById('rankings-row');
  rankRow.innerHTML = ranked.map((c, i) => `
    <div class="rank-item">
      <span class="rank-num">#${i+1}</span>
      <span class="rank-name">${c.ticker}</span>
      <span class="rank-score">${c.total.toFixed(1)}</span>
    </div>
  `).join('');
}

function renderPillarOverview() {
  // Logic to update the bars based on averages
  const avg = (pillar) => (Object.values(aiSummaries).reduce((acc, c) => acc + c[pillar], 0) / companies.length) || 0;
  
  updateMetricBar('e-metrics', avg('e'));
  updateMetricBar('s-metrics', avg('s'));
  updateMetricBar('g-metrics', avg('g'));
}

function updateMetricBar(id, value) {
  const container = document.getElementById(id);
  if(!container) return;
  container.innerHTML = `
    <div class="metric-row">
      <span class="metric-name">Average Score</span>
      <div class="metric-bar-wrap">
        <div class="metric-bar"><div class="metric-bar-fill" style="width: ${value}%"></div></div>
      </div>
      <span class="metric-val">${value.toFixed(1)}</span>
    </div>
  `;
}

function renderCompanyTabs() {
  const tabsEl = document.getElementById('company-tabs');
  tabsEl.innerHTML = companies.map((c, i) => `
    <div class="company-tab ${i === 0 ? 'active' : ''}" onclick="switchTab(${i}, this)">${c.ticker}</div>
  `).join('');
  renderCompanySummary(0);
}

window.switchTab = function(i, el) {
  document.querySelectorAll('.company-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  renderCompanySummary(i);
};

function renderCompanySummary(i) {
  const c = companies[i];
  const data = aiSummaries[c.ticker];
  const box = document.getElementById('company-summary-box');
  
  if (!data) return;
  
  box.innerHTML = `
    <div class="summary-company-header">
      <h3>${data.name} (${data.ticker})</h3>
      <p>${data.industry}</p>
    </div>
    <div class="scores-row" style="display:flex; gap:20px; margin: 20px 0;">
      <div class="score-chip"><strong>E:</strong> ${data.e.toFixed(1)}</div>
      <div class="score-chip"><strong>S:</strong> ${data.s.toFixed(1)}</div>
      <div class="score-chip"><strong>G:</strong> ${data.g.toFixed(1)}</div>
      <div class="score-chip"><strong>Total:</strong> ${data.total.toFixed(1)}</div>
    </div>
    <div class="ai-summary-text">${data.summary}</div>
  `;
}

function renderTable() {
    const tbody = document.getElementById('table-body');
    if(!tbody) return;
    
    tbody.innerHTML = companies.map(c => {
        const data = aiSummaries[c.ticker];
        return `
            <tr>
                <td><strong>${c.ticker}</strong></td>
                <td>${data?.e.toFixed(1) || '—'}</td>
                <td>${data?.s.toFixed(1) || '—'}</td>
                <td>${data?.g.toFixed(1) || '—'}</td>
                <td>${data?.total.toFixed(1) || '—'}</td>
            </tr>
        `;
    }).join('');
}

// ══════════════════════════════════════════════════════════════════════════════
// DOWNLOADS (Fixed Event & Logic)
// ══════════════════════════════════════════════════════════════════════════════

window.downloadFile = async function(fileNum, event) { // Catch the event here
    const btn = event.currentTarget; // Now this won't be undefined
    const originalText = btn.innerHTML;
    
    const fileMap = {
        1: "esg_cross_company.xlsx",
        2: "esg_per_company.xlsx"
    };
    const targetFile = fileMap[fileNum];

    try {
        btn.innerHTML = "⏳ Fetching...";
        btn.disabled = true;

        const response = await fetch(`${API_BASE_URL}/outputs/${jobId}/${targetFile}`);
        
        if (!response.ok) throw new Error("File not found on server");

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = targetFile; 
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        
        btn.innerHTML = "✅ Done";
    } catch (err) {
        console.error(err);
        btn.innerHTML = "❌ Error";
    } finally {
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }, 2000);
    }
};

// ══════════════════════════════════════════════════════════════════════════════
// DEMO FALLBACK
// ══════════════════════════════════════════════════════════════════════════════

function loadDemoData() {
  companies = [{ ticker: 'TATA', name: 'Tata Motors' }, { ticker: 'RELI', name: 'Reliance' }];
  aiSummaries = {
    'TATA': { name: 'Tata Motors', ticker: 'TATA', industry: 'Auto', e: 80, s: 75, g: 85, total: 80, summary: 'Demo analysis.' },
    'RELI': { name: 'Reliance', ticker: 'RELI', industry: 'Energy', e: 70, s: 80, g: 75, total: 75, summary: 'Demo analysis.' }
  };
}

// ══════════════════════════════════════════════════════════════════════════════
// NAV
// ══════════════════════════════════════════════════════════════════════════════

window.newAnalysis = () => {
  sessionStorage.clear();
  window.location.href = 'index.html';
};

init();