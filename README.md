# Agile Requirements Quality Agent: A Self-Improving DSPy Framework

An advanced, AI-driven experiment and web platform for evaluation, benchmarking, and optimization of **User Story Quality** and **Requirements Technical Debt (RTD)**. 

Leveraging **DSPy (Declarative Self-Improving Language Programs)** and large language models (LLMs), the system automates requirements refactoring according to the **Agile INVEST criteria** (Independent, Negotiable, Valuable, Estimable, Small, Testable) through a structured, multi-agent Judge-Rewriter loop. It provides a full-featured multi-user experiment system that collects subject matter expert evaluations via a randomized A/B survey interface.

---

## 🚀 Key Features

*   **Declarative Prompt Optimization (DSPy):** Bypasses brittle handwritten prompt instructions, formulating the scorer and rewriter as structured signature modules. Automates optimization passes via Bootstrap Few-Shot calibration against verified baseline examples.
*   **A/B Evaluation & Survey Management:** A robust user research portal built with Streamlit. Dynamically maps configurations using explicit unique participant tokens, presenting randomized multi-version user stories (`Version A` vs `Version B`) side-by-side alongside complete cross-lingual contextual rubrics.
*   **Dual-Engine Hybrid Grading:** Integrates deterministic lexical analytics (e.g., matching ambiguous non-verifiable keywords derived from NASA ARM / ISO 29148 standards) with fluid contextual evaluation on a calibrated 1–5 scoring spectrum.
*   **Automatic Quality Safeguards:** Implements a localized syntax role lock algorithm that prevents the LLM from mutating target actor identities (`As a <role>`), forcing refactoring optimizations to concentrate purely on system behavior boundaries, capabilities, and business metrics.
*   **Enterprise-Grade Reporting:** Generates timestamped performance summaries, computing delta shifts ($\Delta$) for each standard INVEST metric and tracking comprehensive history maps exported natively as analysis-ready tables.

---

## 📁 System Architecture & Directory Layout

```text
├── .env                  # Environment configurations (API Keys, URLs, SMTP Credentials)
├── app.py                # Main Streamlit application entry point (Survey GUI & PM Portal)
├── main.py               # Batch optimization execution pipeline runner
├── core/
│   ├── __init__.py
│   ├── assert_invest.py  # Matrix computation, threshold controls, and feedback text mappings
│   ├── comparator.py     # Aggregator analyzing metric trends before/after execution passes
│   ├── config_model.py   # Global runtime initialization for LiteLLM & DSPy backend bindings
│   ├── fuzzy_terms.py    # Text dictionary indexing banned vague descriptors
│   ├── invest_rules.py   # Complete 1-5 linguistic rubrics and parameter weights
│   ├── mailer.py         # Outbound SMTP controllers handles invitations & database dumps
│   └── pipeline.py       # Core DSPy rewriter-critic loops, calibrations, and seeding records
├── data/
│   ├── models_json/      # Shared text data sources
│   ├── survey/           # JSON files containing recorded user feedback submissions
│   └── user_project/     # Project metadata master files tracked by unique identifier
└── report/               # Target workspace folder generating CSV analysis spreadsheets
```


## 🛠️ Installation & Setup

1. Prerequisites
Ensure you have Python 3.9+ installed on your system.

2. Install Required Dependencies
Clone the repository and install the required libraries:

```
pip install streamlit dspy-ai pandas openpyxl tqdm python-dotenv
```

3. Environment Configuration (.env)
Create a .env file in the root directory of the project and specify your credentials:

```
# Core API Configurations
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o

# Application Configuration
APP_URL=http://localhost:8501
MAX_ROUNDS=3
FEWSHOT_K=4

# Outbound Mail Server (SMTP Settings for Gmail TLS/SSL)
SENDER_EMAIL=your-research-email@gmail.com
SENDER_PASSWORD=your-app-specific-password
```

## 💻 Usage Guide

Mode A: Streamlit Interactive Web Interface (Full Survey Experiment)
Launch the unified interface using Streamlit:

```
streamlit run app.py
```

This application launches two sequential operational flows:

Product Manager Portal (Setup): Upload your baseline User Story file (.xlsx or .csv), provide brief software project context, and input participant emails. The system immediately fires off background DSPy alignment procedures, generates unique tracking tokens, and pushes email invites out to your validation team.

Validator Interface (Blind A/B Survey): Participants click their unique tokenized links to access a secure scoring layout. They perform deep evaluations across all 6 INVEST dimensions guided by exhaustive multilingual reference definitions, marking hidden structural ambiguity while keeping score progress cached locally safely against page refreshes.

## Mode B: CLI Batch Execution Pipeline
To run bulk benchmarking routines directly on JSON datasets without spinning up the web interface:

```
python main.py data/models_json/your-dataset.json
```

The script will load target stories, execute iterative DSPy optimization rounds, output runtime execution reports, and output visualization files under the report/ workspace.

## 🔍 Quality Optimization Logic Deep Dive
```[Original Requirement Text]
       │
       ▼
 ┌───────────┐
 │  Scorer   │ ◄─── Calibrates metric criteria via combined LLM 
 │ Alignment │      and structural Heuristic scoring (Scale: 1-5)
 └─────┬─────┘
       │
       ▼
 ┌───────────┐
 │ Rewriter  │ ◄─── Executes optimized refactoring targeting low-score dimensions;
 │ Iteration │      injects measurable criteria into text blocks
 └─────┬─────┘
       │
       ▼
 ┌───────────┐
 │ Role Lock │ ◄─── Stringently sanitizes text via Subject-Only Role Lock;
 │ Guardrail │      restores source persona signature matching original text
 └─────┬─────┘
       │
       ▼
 ┌───────────┐
 │ Selection │ ◄─── Validates candidate score using combo metric objective:
 │ Mechanism │      Combo Score = INVEST Overall Score + (λ * Jaccard Diversity)
 └─────┬─────┘
       │
       ├───────────────── Meets Target Threshold? (No)
       ▼ (Yes)
[Production Ready User Story]

```

## 📜 Academic Attribution & License
This system was developed as part of a formal academic research initiative examining Ambiguity optimization patterns using large language model agent frameworks at the National Tsing Hua University (NTHU).
