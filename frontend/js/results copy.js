// ── DUMMY DATA GENERATORS ────────────────────────────────────────────────────
    const AI_SUMMARIES = {
      'AAPL': {
        name: 'Apple Inc.', ticker: 'AAPL', industry: 'Technology',
        validation: 'ok',
        e: 12.4, s: 9.8, g: 7.2, total: 29.4,
        eGrade: 'A', sGrade: 'AA', gGrade: 'A',
        summary: `<strong>Apple Inc.</strong> demonstrates consistently <strong>strong ESG performance</strong> across all three pillars over the selected period. Environmentally, Apple has committed to <strong>100% renewable energy</strong> across its global operations and maintains a relatively low Environment Risk Score of 12.4. The company's carbon neutrality pledges and supply chain sustainability initiatives are reflected in above-average peer percentiles. Socially, Apple scores exceptionally well on Human Capital metrics, driven by competitive employee benefits and diversity programs. Governance remains a slight area of concern with executive pay ratios drawing occasional scrutiny, but overall board independence is strong. <strong>Validation Status:</strong> Kaggle data aligns closely with Yahoo Finance Sustainalytics scores (delta &lt; 1.2 pts).`
      },
      'MSFT': {
        name: 'Microsoft Corp.', ticker: 'MSFT', industry: 'Technology',
        validation: 'ok',
        e: 11.1, s: 8.5, g: 6.8, total: 26.4,
        eGrade: 'AA', sGrade: 'AA', gGrade: 'AA',
        summary: `<strong>Microsoft Corp.</strong> is the <strong>top-ranked ESG performer</strong> in this analysis with the lowest overall risk score of 26.4. Microsoft's carbon-negative pledges, paired with aggressive clean energy procurement, push its Environmental score to a class-leading 11.1. Socially, the company leads on workplace inclusion benchmarks and has maintained zero major labour controversies. Governance is exceptional — Microsoft's board independence exceeds 85% and ESG disclosure scores are among the highest in the sector. Its consistent year-over-year improvement across all three pillars makes it a benchmark ESG investment. <strong>Validation Status:</strong> Fully validated — delta 0.9 pts against Sustainalytics live data.`
      },
      'TSLA': {
        name: 'Tesla Inc.', ticker: 'TSLA', industry: 'Automotive',
        validation: 'warn',
        e: 8.9, s: 24.3, g: 18.2, total: 51.4,
        eGrade: 'AAA', sGrade: 'C', gGrade: 'B',
        summary: `<strong>Tesla Inc.</strong> presents a <strong>highly polarised ESG profile</strong>. On Environmental metrics, Tesla is unmatched — its core EV product mandate earns the lowest E-Score (8.9) in this group, with exceptional environmental impact and carbon displacement value. However, Social and Governance scores drag the overall rating significantly. Labour disputes, safety incident records, and governance controversies around board independence pull the S-Score to 24.3 and G-Score to 18.2. While Tesla's environmental mission is laudable, investors with balanced ESG mandates should note the elevated Social risk. <strong>Validation Status:</strong> ⚠️ Minor discrepancy detected — S-Score delta of 2.8 pts vs Yahoo Finance.`
      },
      'GOOGL': {
        name: 'Alphabet Inc.', ticker: 'GOOGL', industry: 'Technology',
        validation: 'ok',
        e: 13.8, s: 11.2, g: 10.4, total: 35.4,
        eGrade: 'A', sGrade: 'A', gGrade: 'A',
        summary: `<strong>Alphabet Inc.</strong> maintains a <strong>balanced and improving ESG trajectory</strong> over the analysis period. Environmental operations are aided by large-scale renewable energy investments and data centre efficiency programmes. Social metrics are generally positive, though emerging regulatory scrutiny around content moderation introduces modest Social risk. Governance remains an area of monitoring — Alphabet's dual-class share structure limits minority shareholder influence, which is reflected in governance percentile scores below tech sector average. <strong>Validation Status:</strong> Fully validated — delta 1.1 pts.`
      },
      'AMZN': {
        name: 'Amazon.com Inc.', ticker: 'AMZN', industry: 'Consumer Discretionary',
        validation: 'ok',
        e: 17.6, s: 19.8, g: 12.3, total: 49.7,
        eGrade: 'B', sGrade: 'B', gGrade: 'A',
        summary: `<strong>Amazon.com Inc.</strong> shows <strong>moderate ESG risk</strong> with notable variation across pillars. The Climate Pledge and renewable energy investments have improved environmental scores, but the sheer scale of Amazon's logistics and packaging footprint keeps the E-Score elevated at 17.6. Social risks remain the most significant concern — warehouse working conditions, labour organising efforts, and high workforce turnover contribute to an S-Score of 19.8. Governance is the strongest pillar, with solid board oversight and increasingly transparent ESG reporting. <strong>Validation Status:</strong> Fully validated — delta 1.6 pts.`
      },
      'META': {
        name: 'Meta Platforms Inc.', ticker: 'META', industry: 'Technology',
        validation: 'warn',
        e: 14.2, s: 28.7, g: 21.4, total: 64.3,
        eGrade: 'A', sGrade: 'D', gGrade: 'C',
        summary: `<strong>Meta Platforms Inc.</strong> carries the <strong>highest overall ESG risk score</strong> (64.3) in this analysis, driven primarily by severe Social and Governance concerns. Environmental performance is surprisingly solid with 100% renewable energy and net-zero commitments. However, ongoing regulatory challenges, data privacy controversies, and misinformation concerns push the Social score to 28.7 — the highest in this group. Governance risk is compounded by Mark Zuckerberg's controlling voting stake. ESG-focused investors should approach Meta with caution. <strong>Validation Status:</strong> ⚠️ G-Score discrepancy of 3.1 pts detected vs Yahoo Finance.`
      },
    };

    const METRICS_DEF = [
      { pillar: 'E', key: 'environment_score',  label: 'Environment Risk Score',     unit: '', lowGood: true },
      { pillar: 'E', key: 'env_level',           label: 'Environment Level',          unit: '', lowGood: false },
      { pillar: 'E', key: 'env_grade',           label: 'Environment Grade',          unit: '', lowGood: false },
      { pillar: 'E', key: 'env_percentile',      label: 'Env. Percentile vs Peers',   unit: '%', lowGood: false },
      { pillar: 'S', key: 'social_score',        label: 'Social Risk Score',          unit: '', lowGood: true },
      { pillar: 'S', key: 'social_level',        label: 'Social Level',               unit: '', lowGood: false },
      { pillar: 'S', key: 'social_grade',        label: 'Social Grade',               unit: '', lowGood: false },
      { pillar: 'S', key: 'social_percentile',   label: 'Social Percentile vs Peers', unit: '%', lowGood: false },
      { pillar: 'G', key: 'governance_score',    label: 'Governance Risk Score',      unit: '', lowGood: true },
      { pillar: 'G', key: 'governance_level',    label: 'Governance Level',           unit: '', lowGood: false },
      { pillar: 'G', key: 'governance_grade',    label: 'Governance Grade',           unit: '', lowGood: false },
      { pillar: 'G', key: 'total_score',         label: 'Total ESG Risk Score',       unit: '', lowGood: true },
    ];

    // ── LOAD STATE ───────────────────────────────────────────────────────────────
    let companies = JSON.parse(sessionStorage.getItem('esg_companies') || '[]');
    let yearRange = JSON.parse(sessionStorage.getItem('esg_years') || 'null');

    // Fallback demo data
    if (!companies.length) {
      companies = [
        { ticker: 'MSFT', name: 'Microsoft Corp.' },
        { ticker: 'AAPL', name: 'Apple Inc.' },
        { ticker: 'TSLA', name: 'Tesla Inc.' },
      ];
      yearRange = { label: '2021 – 2023', years: [2021, 2022, 2023] };
    }

    // ── GENERATE DUMMY METRIC DATA ───────────────────────────────────────────────
    function genMetricValue(ticker, key, year) {
      const base = AI_SUMMARIES[ticker];
      const yearOffset = (year - 2021) * 0.05;
      const seed = ticker.charCodeAt(0) + key.length;
      const noise = ((seed * 1.618 + year) % 7 - 3.5) * 0.4;
      if (key === 'environment_score') return (base?.e || 15) + noise - yearOffset;
      if (key === 'social_score')      return (base?.s || 18) + noise;
      if (key === 'governance_score')  return (base?.g || 12) + noise;
      if (key === 'total_score')       return (base?.total || 45) + noise * 2;
      if (key.includes('grade'))       return base ? (key.includes('env') ? base.eGrade : key.includes('social') ? base.sGrade : base.gGrade) : 'A';
      if (key.includes('level'))       return ['Low','Medium','Negligible','Low'][seed % 4];
      if (key.includes('percentile'))  return Math.round(40 + seed % 45 + yearOffset * 5);
      return '—';
    }

    function fmtVal(val) {
      if (typeof val === 'number') return val.toFixed(1);
      return val;
    }

    // ── RENDER PAGE ──────────────────────────────────────────────────────────────
    function renderPage() {
      // nav + meta
      document.getElementById('nav-info').textContent = `${companies.length} companies · ${yearRange?.label || '—'}`;
      document.getElementById('meta-companies').textContent = companies.map(c => c.ticker).join(', ');
      document.getElementById('meta-years').textContent = yearRange?.label || '—';
      document.getElementById('meta-time').textContent = new Date().toLocaleTimeString();

      renderVerdict();
      renderPillarOverview();
      renderCompanyTabs();
      renderTable();
    }

    // ── VERDICT ──────────────────────────────────────────────────────────────────
    function renderVerdict() {
      // compute winner (lowest total_score)
      const ranked = companies
        .filter(c => AI_SUMMARIES[c.ticker])
        .map(c => ({
          ...c,
          score: AI_SUMMARIES[c.ticker].total,
          normalized: Math.max(0, 100 - AI_SUMMARIES[c.ticker].total)
        }))
        .sort((a, b) => a.score - b.score);

      if (!ranked.length) return;
      const winner = ranked[0];
      const winnerData = AI_SUMMARIES[winner.ticker];

      document.getElementById('verdict-winner').innerHTML =
        `${winnerData.name} <span class="winner-badge">ESG CHAMPION</span>`;

      document.getElementById('verdict-text').innerHTML =
        `Based on equal-weighted ESG analysis (E: 33.3% · S: 33.3% · G: 33.3%) across ${yearRange?.label || 'selected years'}, 
        <span>${winnerData.name}</span> achieves the lowest overall ESG Risk Score of <span>${winnerData.total}</span> among the selected companies. 
        The company demonstrates particularly strong performance on <span>${winnerData.e < 12 ? 'Environmental' : winnerData.g < 9 ? 'Governance' : 'Social'}</span> metrics 
        and maintains validated, consistent data quality across all measured periods. This recommendation is generated by Groq LLaMA3-70B 
        synthesizing Kaggle dataset metrics cross-validated against Yahoo Finance / Sustainalytics live scores.`;

      const rankRow = document.getElementById('rankings-row');
      rankRow.innerHTML = '';
      ranked.forEach((c, i) => {
        const div = document.createElement('div');
        div.className = 'rank-item';
        div.innerHTML = `
          <span class="rank-num r${i+1}">#${i+1}</span>
          <span class="rank-name">${AI_SUMMARIES[c.ticker]?.name || c.name}</span>
          <span class="rank-score">${c.score.toFixed(1)} risk</span>
        `;
        rankRow.appendChild(div);
      });
    }

    // ── PILLAR OVERVIEW ──────────────────────────────────────────────────────────
    function renderPillarOverview() {
      const avgE = companies.reduce((s, c) => s + (AI_SUMMARIES[c.ticker]?.e || 15), 0) / companies.length;
      const avgS = companies.reduce((s, c) => s + (AI_SUMMARIES[c.ticker]?.s || 18), 0) / companies.length;
      const avgG = companies.reduce((s, c) => s + (AI_SUMMARIES[c.ticker]?.g || 12), 0) / companies.length;

      const eMetrics = [
        { label: 'Risk Score (avg)', val: avgE.toFixed(1), pct: Math.max(5, 100 - avgE * 4) },
        { label: 'Best Performer', val: companies.filter(c => AI_SUMMARIES[c.ticker]).sort((a,b) => AI_SUMMARIES[a.ticker].e - AI_SUMMARIES[b.ticker].e)[0]?.ticker || '—', pct: 80 },
        { label: 'Grade Range', val: 'A – AAA', pct: 70 },
        { label: 'Validation', val: '✓ Confirmed', pct: 90 },
      ];

      const sMetrics = [
        { label: 'Risk Score (avg)', val: avgS.toFixed(1), pct: Math.max(5, 100 - avgS * 3) },
        { label: 'Best Performer', val: companies.filter(c => AI_SUMMARIES[c.ticker]).sort((a,b) => AI_SUMMARIES[a.ticker].s - AI_SUMMARIES[b.ticker].s)[0]?.ticker || '—', pct: 75 },
        { label: 'Grade Range', val: 'A – AA', pct: 65 },
        { label: 'Controversy Avg', val: 'Low', pct: 80 },
      ];

      const gMetrics = [
        { label: 'Risk Score (avg)', val: avgG.toFixed(1), pct: Math.max(5, 100 - avgG * 5) },
        { label: 'Best Performer', val: companies.filter(c => AI_SUMMARIES[c.ticker]).sort((a,b) => AI_SUMMARIES[a.ticker].g - AI_SUMMARIES[b.ticker].g)[0]?.ticker || '—', pct: 85 },
        { label: 'Grade Range', val: 'A – AA', pct: 72 },
        { label: 'Disclosure Score', val: 'High', pct: 88 },
      ];

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

      renderMetrics('e-metrics', eMetrics);
      renderMetrics('s-metrics', sMetrics);
      renderMetrics('g-metrics', gMetrics);

      // animate bars
      setTimeout(() => {
        document.querySelectorAll('.metric-bar-fill').forEach(bar => {
          bar.style.width = bar.dataset.pct + '%';
        });
      }, 300);
    }

    // ── COMPANY TABS ─────────────────────────────────────────────────────────────
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
      const data = AI_SUMMARIES[c.ticker];
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
          ${data.validation === 'ok' ? '✓ Data Validated — Yahoo Finance delta &lt; 1.5 pts' : '⚠ Minor Discrepancy — delta &gt; 2.5 pts detected'}
        </div>
        <div class="ai-summary-text">${data.summary}</div>
      `;
    }

    // ── METRICS TABLE ─────────────────────────────────────────────────────────────
    function renderTable() {
      const thead = document.getElementById('table-head');
      const tbody = document.getElementById('table-body');

      // Build year-company headers
      const years = yearRange?.years || [2021, 2022, 2023];
      let headHtml = '<tr><th>Metric</th>';
      years.forEach(yr => {
        companies.forEach(c => {
          headHtml += `<th>${c.ticker} · ${yr}</th>`;
        });
      });
      headHtml += '</tr>';
      thead.innerHTML = headHtml;

      // Group metrics by pillar
      const pillars = ['E', 'S', 'G'];
      const pillarLabels = { E: '🌿 Environmental', S: '👥 Social', G: '🏛️ Governance' };

      tbody.innerHTML = '';

      pillars.forEach(pillar => {
        // Section header
        const secRow = document.createElement('tr');
        secRow.className = 'section-header';
        const secTd = document.createElement('td');
        secTd.colSpan = 1 + years.length * companies.length;
        secTd.textContent = pillarLabels[pillar];
        secRow.appendChild(secTd);
        tbody.appendChild(secRow);

        // Metric rows
        METRICS_DEF.filter(m => m.pillar === pillar).forEach(metric => {
          const tr = document.createElement('tr');
          let rowHtml = `<td><div class="metric-label-cell pillar-${pillar}"><div class="metric-pillar-dot"></div>${metric.label}</div></td>`;

          years.forEach(yr => {
            companies.forEach(c => {
              const val = genMetricValue(c.ticker, metric.key, yr);
              const fv = fmtVal(val);
              if (metric.key.includes('grade')) {
                rowHtml += `<td><span class="grade-badge grade-${fv}">${fv}</span></td>`;
              } else {
                rowHtml += `<td><span class="cell-val">${fv}${metric.unit}</span></td>`;
              }
            });
          });

          tr.innerHTML = rowHtml;
          tbody.appendChild(tr);
        });
      });
    }

    // ── DOWNLOAD (DUMMY) ─────────────────────────────────────────────────────────
    function downloadFile(num) {
      const btn = event.target.closest('.btn-dl');
      const orig = btn.innerHTML;
      btn.innerHTML = `<span class="dl-icon">⏳</span> Preparing...`;
      btn.disabled = true;
      setTimeout(() => {
        btn.innerHTML = `<span class="dl-icon">✅</span> Downloaded!`;
        setTimeout(() => {
          btn.innerHTML = orig;
          btn.disabled = false;
        }, 2000);
      }, 1500);
    }

    // ── NAV ACTIONS ──────────────────────────────────────────────────────────────
    function exitToHome() {
      sessionStorage.clear();
      window.location.href = 'index.html';
    }

    function newAnalysis() {
      window.location.href = 'index.html';
    }

    // ── BOOT ─────────────────────────────────────────────────────────────────────
    renderPage();