const API_BASE = "http://localhost:8000";

// ── YEAR RANGES ─────────────────────────────────────────────────────────────
const YEAR_RANGES = [
  { label: '2022 – 2024\n Validates for: 2025', years: [2022, 2023, 2024] },
];

// ── STATE ───────────────────────────────────────────────────────────────────
let selectedCompanies = [];   // [{ ticker, name }]
let selectedYearRange = null;
let analysisComplete  = false;
let currentJobId      = null;
let pollInterval      = null;

// ── INIT DROPDOWNS ──────────────────────────────────────────────────────────
async function initDropdowns() {
  // ── COMPANIES (from API) ──────────────────────────────────────────────────
  const opts = document.getElementById('company-options');
  try {
    const res       = await fetch(`${API_BASE}/companies`);
    const companies = await res.json();

    opts.innerHTML = ''; // Clear loading message
    companies.forEach(c => {
      const div       = document.createElement('div');
      div.className   = 'dropdown-option';
      div.dataset.ticker = c.ticker;
      div.dataset.name   = c.company_name.toLowerCase();
      div.innerHTML   = `<span>${c.company_name}</span><span class="opt-ticker">${c.sector || ''}</span>`;
      div.onclick     = () => toggleCompany(c.ticker, c.company_name, div);
      opts.appendChild(div);
    });
  } catch (err) {
    opts.innerHTML = `<div style="padding:12px;color:var(--red)">Failed to load companies — is the backend running?</div>`;
  }

  // ── YEAR RANGES ───────────────────────────────────────────────────────────
  const yopts = document.getElementById('year-options');
  yopts.innerHTML = ''; // Clear
  YEAR_RANGES.forEach((r, i) => {
    const div       = document.createElement('div');
    div.className   = 'dropdown-option';
    div.dataset.idx = i;
    div.innerHTML   = `<span>${r.label}</span><span class="opt-ticker">${r.years.join(', ')}</span>`;
    div.onclick     = () => selectYearRange(i, div);
    yopts.appendChild(div);
  });
}

// ── DROPDOWN TOGGLE ─────────────────────────────────────────────────────────
function toggleDropdown(type) {
  const dd      = document.getElementById(`${type}-dropdown`);
  const trigger = document.getElementById(`${type}-trigger`);
  
  if (!dd || !trigger) return;

  const isOpen  = dd.classList.contains('open');
  
  // Close all others
  document.querySelectorAll('.multiselect-dropdown').forEach(d => d.classList.remove('open'));
  document.querySelectorAll('.multiselect-trigger').forEach(t => t.classList.remove('open'));
  
  if (!isOpen) {
    dd.classList.add('open');
    trigger.classList.add('open');
    if (type === 'company') {
        const search = document.getElementById('company-search');
        if(search) search.focus();
    }
  }
}

// Close when clicking outside
document.addEventListener('click', e => {
  if (!e.target.closest('.multiselect-wrapper')) {
    document.querySelectorAll('.multiselect-dropdown').forEach(d => d.classList.remove('open'));
    document.querySelectorAll('.multiselect-trigger').forEach(t => t.classList.remove('open'));
  }
});

// ── COMPANY SELECTION ───────────────────────────────────────────────────────
function toggleCompany(ticker, name, el) {
  const idx = selectedCompanies.findIndex(c => c.ticker === ticker);
  if (idx > -1) {
    selectedCompanies.splice(idx, 1);
    el.classList.remove('selected');
  } else {
    if (selectedCompanies.length >= 5) return;
    selectedCompanies.push({ ticker, name });
    el.classList.add('selected');
  }
  
  document.querySelectorAll('#company-options .dropdown-option').forEach(opt => {
    if (!opt.classList.contains('selected')) {
      opt.classList.toggle('disabled', selectedCompanies.length >= 5);
    }
  });
  
  renderCompanyTags();
  updateSummary();
  updateRunButton();
}

function renderCompanyTags() {
  const container   = document.getElementById('company-tags');
  const placeholder = document.getElementById('company-placeholder');
  if(!container) return;
  
  container.innerHTML = '';
  if (selectedCompanies.length === 0) {
    if(placeholder) {
        container.appendChild(placeholder);
        placeholder.style.display = '';
    }
    return;
  }
  if(placeholder) placeholder.style.display = 'none';
  
  selectedCompanies.forEach(c => {
    const tag       = document.createElement('div');
    tag.className   = 'tag';
    tag.innerHTML   = `${c.name} <span class="tag-remove" onclick="removeCompany('${c.ticker}', event)">×</span>`;
    container.appendChild(tag);
  });
}

function removeCompany(ticker, event) {
  if(event) event.stopPropagation();
  const el  = document.querySelector(`#company-options .dropdown-option[data-ticker="${ticker}"]`);
  const idx = selectedCompanies.findIndex(c => c.ticker === ticker);
  if (idx > -1) selectedCompanies.splice(idx, 1);
  if (el) el.classList.remove('selected');
  
  document.querySelectorAll('#company-options .dropdown-option').forEach(opt => {
    if (!opt.classList.contains('selected')) opt.classList.remove('disabled');
  });
  
  renderCompanyTags();
  updateSummary();
  updateRunButton();
}

// ── YEAR SELECTION ──────────────────────────────────────────────────────────
function selectYearRange(idx, el) {
  selectedYearRange = YEAR_RANGES[idx];
  document.querySelectorAll('#year-options .dropdown-option').forEach(o => o.classList.remove('selected'));
  el.classList.add('selected');

  const container   = document.getElementById('year-tags');
  const placeholder = document.getElementById('year-placeholder');
  
  container.innerHTML     = '';
  if(placeholder) placeholder.style.display = 'none';
  
  const tag     = document.createElement('div');
  tag.className = 'tag';
  tag.innerHTML = `${selectedYearRange.label} <span class="tag-remove" onclick="clearYear(event)">×</span>`;
  container.appendChild(tag);

  document.getElementById('year-dropdown').classList.remove('open');
  document.getElementById('year-trigger').classList.remove('open');

  updateSummary();
  updateRunButton();
}

function clearYear(event) {
  if(event) event.stopPropagation();
  selectedYearRange = null;
  document.querySelectorAll('#year-options .dropdown-option').forEach(o => o.classList.remove('selected'));
  const container   = document.getElementById('year-tags');
  const placeholder = document.getElementById('year-placeholder');
  
  container.innerHTML = '';
  if(placeholder) {
    container.appendChild(placeholder);
    placeholder.style.display = '';
  }
  updateSummary();
  updateRunButton();
}

// ── FILTER SEARCH ───────────────────────────────────────────────────────────
function filterOptions(type) {
  const q = document.getElementById(`${type}-search`).value.toLowerCase();
  document.querySelectorAll(`#${type}-options .dropdown-option`).forEach(opt => {
    const name = opt.dataset.name || "";
    const ticker = opt.dataset.ticker || "";
    const match = name.includes(q) || ticker.toLowerCase().includes(q);
    opt.style.display = match ? '' : 'none';
  });
}

// ── SUMMARY ─────────────────────────────────────────────────────────────────
function updateSummary() {
  const el = document.getElementById('selection-summary');
  if(!el) return;

  if (selectedCompanies.length === 0 && !selectedYearRange) {
    el.innerHTML = `<span class="summary-prefix">awaiting selection —</span> <span style="color:var(--text-dim);font-size:0.75rem;font-family:var(--mono)">choose companies and year range to begin</span>`;
    return;
  }
  let html = `<span class="summary-prefix">Analyzing</span> `;
  html += selectedCompanies.length > 0
    ? selectedCompanies.map(c => `<span class="summary-item">${c.name}</span>`).join(' ')
    : `<span style="color:var(--text-dim)">no companies</span>`;
  html += ` <span class="summary-sep">|</span> `;
  html += selectedYearRange
    ? selectedYearRange.years.map(y => `<span class="summary-item">${y}</span>`).join(' ')
    : `<span style="color:var(--text-dim)">no range</span>`;
  el.innerHTML = html;
}

function updateRunButton() {
  const btn = document.getElementById('btn-run');
  if(btn) btn.disabled = !(selectedCompanies.length >= 1 && selectedYearRange);
}

// ── STEP UI HELPERS ──────────────────────────────────────────────────────────
const STEPS = [
  { id: 1, badge: 'RUNNING',    doneBadge: 'DONE', detail: () => `Orchestrator initialized — session started` },
  { id: 2, badge: 'FETCHING',   doneBadge: 'DONE', detail: () => `Loading CRISIL ESG data` },
  { id: 3, badge: 'INDEXING',   doneBadge: 'DONE', detail: () => `Fetching live news + building FAISS index` },
  { id: 4, badge: 'COMPUTING',  doneBadge: 'DONE', detail: () => `LOWESS smoothing + adaptive forward validation` },
  { id: 5, badge: 'GENERATING', doneBadge: 'DONE', detail: () => `LLM Processing — Agent Narratives` },
  { id: 6, badge: 'BUILDING',   doneBadge: 'DONE', detail: () => `Generating Excel workbooks + charts` },
];

function log(msg, type = 'info') {
  const terminal = document.getElementById('terminal-log');
  if(!terminal) return;
  const now      = new Date();
  const time     = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;
  const line     = document.createElement('div');
  line.className = 'log-line';
  line.innerHTML = `<span class="log-time">${time}</span><span class="log-msg ${type}">${msg}</span>`;
  terminal.appendChild(line);
  terminal.scrollTop = terminal.scrollHeight;
}

function activateStep(stepNum, progress) {
  const el       = document.getElementById(`step-${stepNum}`);
  const badge    = document.getElementById(`step-${stepNum}-badge`);
  const detail   = document.getElementById(`step-${stepNum}-detail`);
  const stepData = STEPS[stepNum - 1];
  if (!el || !badge) return;
  el.classList.add('active');
  badge.textContent         = stepData.badge;
  badge.style.borderColor   = 'var(--amber)';
  badge.style.color         = 'var(--amber)';
  if(detail) detail.innerHTML = stepData.detail();
  const fill = document.getElementById('progress-fill');
  if(fill) fill.style.width = progress + '%';
}

function completeStep(stepNum) {
  const el       = document.getElementById(`step-${stepNum}`);
  const badge    = document.getElementById(`step-${stepNum}-badge`);
  if (!el || !badge) return;
  el.classList.remove('active');
  el.classList.add('done');
  badge.textContent       = 'DONE';
  badge.style.borderColor = 'var(--green-dim)';
  badge.style.color       = 'var(--green)';
}

// ── ANALYSIS PIPELINE ────────────────────────────────────────────────────────
async function startAnalysis() {
  document.getElementById('input-panel').style.display = 'none';
  const section = document.getElementById('analysis-section');
  section.style.display = 'block';
  document.getElementById('terminal-log').innerHTML = '';
  log('Analysis pipeline starting...', 'info');
  setTimeout(() => section.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);

  let job_id;
  try {
    const res  = await fetch(`${API_BASE}/analyze`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        companies:  selectedCompanies.map(c => c.ticker),
        year_range: selectedYearRange.years,
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      log(`[ERROR] ${JSON.stringify(err.detail)}`, 'error');
      showError('Failed to start analysis.');
      return;
    }

    const data = await res.json();
    job_id     = data.job_id;
    currentJobId = job_id;
    log(`[MCP] Job started — ID: ${job_id}`, 'ok');
  } catch (err) {
    log(`[ERROR] Cannot reach backend: ${err.message}`, 'error');
    showError('Backend unreachable.');
    return;
  }

  let frontendStep = 0;
  let backendDone = false;
  
  // Custom terminal messages for better UX
  const customMessages = {
    1: ['Initializing orchestrator...', 'Validating session parameters...', 'Agent pipeline ready'],
    2: ['Connecting to CRISIL database...', 'Fetching ESG scores...', 'Loading historical metrics...'],
    3: ['Scraping live news articles...', 'Building FAISS vector index...', 'Indexing — 450+ articles to be processed ....',"Building the Vector DB ...."],
    4: ['Running LOWESS smoothing algorithm...', 'Computing adaptive forward validation...', 'Statistical models calibrated'],
    5: ['Initializing LLM agents (Groq + LLaMA3)...', 'Generating per-company narratives...', 'AI analysis in progress...'],
    6: ['Building Excel workbooks...', 'Rendering charts and visualizations...', 'Exporting final reports...']
  };

  // Function to show one step completely before moving to next
  async function showStep(stepNum) {
    const progressMap = { 1: 10, 2: 25, 3: 45, 4: 62, 5: 80, 6: 93 };
    activateStep(stepNum, progressMap[stepNum] || 0);
    
    // Show custom terminal messages for this step
    if (customMessages[stepNum]) {
      for (let msg of customMessages[stepNum]) {
        log(msg, 'info');
        await new Promise(resolve => setTimeout(resolve, 800));
      }
    }
    
    // Wait before completing this step
    await new Promise(resolve => setTimeout(resolve, 1500));
    completeStep(stepNum);
  }

  pollInterval = setInterval(async () => {
    try {
      const res    = await fetch(`${API_BASE}/status/${job_id}`);
      const status = await res.json();

      // Show steps sequentially until we catch up to backend
      while (frontendStep < status.step && frontendStep < 6) {
        frontendStep++;
        await showStep(frontendStep);
      }

      // If backend is done, show remaining steps
      if (status.status === 'done' && !backendDone) {
        backendDone = true;
        
        while (frontendStep < 6) {
          frontendStep++;
          await showStep(frontendStep);
        }
        
        clearInterval(pollInterval);
        document.getElementById('progress-fill').style.width = '100%';
        document.getElementById('status-dot').className      = 'status-dot done';
        document.getElementById('status-text').textContent   = 'Analysis Complete';
        document.getElementById('btn-results').disabled      = false;
        
        sessionStorage.setItem('esg_job_id', job_id);
        sessionStorage.setItem('esg_companies', JSON.stringify(selectedCompanies));
        sessionStorage.setItem('esg_years', JSON.stringify(selectedYearRange));
        log('[DONE] Analysis complete — reports ready', 'ok');
      }

      if (status.status === 'error') {
        clearInterval(pollInterval);
        showError(status.error_msg || 'Pipeline failed');
      }
    } catch (err) {
      console.error('Polling failed');
    }
  }, 2000);
}

function showError(msg) {
  const dot = document.getElementById('status-dot');
  const txt = document.getElementById('status-text');
  if(dot) dot.className = 'status-dot error';
  if(txt) {
    txt.textContent = 'Error';
    txt.style.color = 'var(--red)';
  }
  log(`[ERROR] ${msg}`, 'error');
}

function goToResults() {
  window.location.href = 'results.html';
}

// Start
initDropdowns();