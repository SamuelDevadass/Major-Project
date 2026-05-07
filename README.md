# 🌿 ESG Intelligence Platform

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_AI-6639ba?style=flat)
![LLaMA3](https://img.shields.io/badge/LLaMA3--70B-Groq-f55036?style=flat)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat)

> A fully automated, five-agent AI system for corporate ESG analysis — combining structured time-series modelling, real-world news validation, greenwashing detection, and investor-grade reporting. Built entirely on free and open-source tools. **No paid APIs. No subscriptions.**

---

## 📌 Overview

The **ESG Intelligence Platform** is a locally deployed web application that automates the complete process of Environmental, Social, and Governance (ESG) analysis for publicly listed Indian companies. It accepts up to five company tickers and runs a sequential five-agent pipeline that:

1. Retrieves historical monthly ESG scores (2022–2024)
2. Models temporal trends using LOWESS smoothing and exponentially weighted regression
3. Validates projected 2025 ESG trajectories against actual observed scores
4. Cross-validates numerical ESG data against real-world news for greenwashing detection
5. Generates structured Excel reports and an interactive web dashboard

All within **15–35 seconds**, with zero reliance on paid data or API subscriptions.

```
[ Agent 1: Data Retrieval ] → [ Agent 2: News & RAG ] → [ Agent 3: Statistical Modelling ]
                                                                        ↓
                              [ Agent 5: Report Generation ] ← [ Agent 4: LLM Analysis ]
```

---

## ✨ Key Features

- **Historical ESG time-series** — monthly E, S, G, and composite scores for 700+ listed companies sourced from CRISIL ESG Ratings
- **LOWESS + exponentially weighted regression** — statistically grounded trend modelling with noise reduction
- **Adaptive forward validation** — projects 2025 ESG values from the 2022–2024 training window and compares against actual observed scores to quantify trend reliability
- **RAG-powered news intelligence** — FAISS vector search over pre-fetched Google RSS news articles using Sentence-BERT embeddings
- **Three-stage LLM credibility pipeline** — extraction → credibility scoring (0–100) → conditional investor narrative generation (Groq LLaMA3-70B)
- **Greenwashing detection** — cross-references reported ESG scores against real-world news; flags discrepancies automatically
- **Investor signals** — BUY / HOLD / CAUTION / AVOID per company based on combined score and credibility analysis
- **Automated Excel reports** — two structured workbooks with embedded matplotlib trend charts
- **Interactive web dashboard** — static HTML/CSS/JS frontend, no framework required
- **Zero paid dependencies** — Groq free tier, open-source Python libraries, local data files only

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.11) |
| Agent Orchestration | LangGraph + MCP (Model Context Protocol) |
| Statistical Modelling | statsmodels (LOWESS), NumPy, pandas |
| Vector Search / RAG | FAISS + Sentence-BERT (sentence-transformers) |
| LLM Inference | Groq API — LLaMA3-70B-8192 (free tier) |
| Report Generation | xlsxwriter + matplotlib |
| Frontend | Static HTML / CSS / JavaScript (no framework) |
| Runtime | Python 3.11+, Node.js 18+ (for MCP servers) |

---

## ⚙️ Installation

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- A free [Groq API key](https://console.groq.com)
- VS Code with the Live Server extension (for the frontend)

### 1. Clone the repository

```bash
git clone https://github.com/your-username/esg-intelligence-platform.git
cd esg-intelligence-platform
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Install MCP server dependencies

```bash
cd mcp_servers
npm install
cd ..
```

### 4. Set up environment variables

```bash
cp .env.example .env
```

Open `.env` and add your Groq API key:

```env
GROQ_API_KEY=your_groq_api_key_here
```

### 5. Verify required data files

Ensure the following files are present before starting:

```
data/
├── esg_monthly_historical.csv     # CRISIL ESG monthly scores (2022–2025)
├── kaggle_snapshot.csv            # Company ticker → name mapping
└── news/                          # Pre-fetched news JSON files
    ├── esg_today.json
    ├── reuters_sustainability.json
    └── ...
```

### 6. Start the backend

```bash
uvicorn main:app --reload --port 8000
```

### 7. Launch the frontend

Open `frontend/index.html` with VS Code Live Server, or serve it with:

```bash
cd frontend
python -m http.server 5500
```

Then navigate to `http://localhost:5500` in your browser.

---

## 🚀 Usage

1. Open the web dashboard in your browser
2. Search and select up to **5 company tickers** from the dropdown
3. Click **Run Analysis** — the six-step pipeline progress view will animate
4. View ESG trend charts, credibility scores, investor signals, and AI narratives on the dashboard
5. Download the auto-generated Excel workbooks from the Reports section

---

## 📁 Project Structure

```
esg-intelligence-platform/
├── main.py                     # FastAPI app entry point
├── agents/
│   ├── agent1_data.py          # Data retrieval agent
│   ├── agent2_news.py          # News ingestion and RAG agent
│   ├── agent3_stats.py         # Statistical modelling and validation agent
│   ├── agent4_llm.py           # LLM analysis and credibility agent
│   └── agent5_report.py        # Report generation agent
├── mcp_servers/                # MCP tool server definitions
├── data/                       # ESG datasets and news JSON files
├── frontend/                   # Static HTML/CSS/JS dashboard
├── outputs/                    # Generated Excel reports (gitignored)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 📊 Output

| Output | Description |
|---|---|
| ESG Trend Charts | LOWESS-smoothed line plots for E, S, G, and composite scores per company |
| Credibility Score | 0–100 score quantifying alignment between ESG scores and news evidence |
| Greenwashing Flag | Low / Medium / High risk classification with LLM-generated explanation |
| Investor Signal | BUY / HOLD / CAUTION / AVOID per company |
| Excel Workbook 1 | Cross-company comparative analysis with embedded charts (one sheet per year) |
| Excel Workbook 2 | Company-level deep-dive with time-series data, validation results, and narratives |
| Web Dashboard | Interactive frontend rendering all results without additional configuration |

---

## 🔬 Novel Contributions

- **Adaptive Forward Validation** — trains on 2022–2024 ESG data, projects 2025 values, and compares against actual 2025 scores to quantify trend reliability. This is not available in any existing open-source ESG tool.
- **Three-Stage Conditional LLM Pipeline** — sequential extraction → credibility scoring → tone-conditioned narrative generation (commendatory / balanced / cautionary) for cross-source greenwashing detection.
- **Open ESG Dataset** — `esg_monthly_historical.csv` covering 700+ companies from 2022–2025 on a monthly basis, freely usable for academic research without a data subscription.

---

## 📄 Citation

If you use this project or dataset in your research, please cite:

```bibtex
@misc{esg_intelligence_platform_2025,
  title   = {ESG Intelligence Platform: A Multi-Source Agentic AI System
             for Corporate Sustainability Analysis and Benchmarking},
  author  = {Samuel Arvind Devadass, Bhavesh Suresh Patil, 
             Shivam Santosh Barkule, Sanjay Shankar Kankamwar,},
  year    = {2025},
  school  = {Vishwakarma Institute of Information Technology, Pune},
  note    = {B.Tech Final Year Project, Department of Information Technology}
}
```

---

## ⚠️ Disclaimer

This platform is intended for **academic research and educational purposes only**. ESG scores, credibility ratings, and investor signals generated by this system do not constitute financial advice. Always consult a qualified financial advisor before making investment decisions.

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">Built at VIIT Pune &nbsp;·&nbsp; Department of Information Technology &nbsp;·&nbsp; 2026</p>
