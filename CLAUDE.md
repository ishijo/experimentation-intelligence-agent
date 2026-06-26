# CLAUDE.md — Project Context for Claude Code

## Project Identity
- **Name:** Experimentation Intelligence Agent
- **What it is:** An agentic RAG system for querying, synthesizing, and learning from a corpus of historical A/B test results in natural language, with built-in bias detection.
- **Type of system:** Agentic AI system (multi-node reasoning graph, not a single retrieval+answer step).
- **Primary deployment target:** Hugging Face Spaces.

## Tech Stack (use these exact tools)
- Agent graph: LangGraph
- Ingestion / indexing: LlamaIndex
- Vector store: ChromaDB (local persistence)
- LLM (primary): Ollama running Llama 3, locally on Apple Silicon
- LLM (fallback for quality-sensitive synthesis): Anthropic Claude API
- Embeddings: sentence-transformers (`all-mpnet-base-v2`) unless we explicitly switch
- API serving: FastAPI + Uvicorn
- Optional pipeline layer (stretch): dbt + Airflow
- Frontend / demo: Hugging Face Space (Gradio or simple HTML interface)
- MCP integration (stretch): custom MCP tool layer exposing search / validity-check / synthesis

## Architecture (5-node LangGraph reasoning pipeline)
1. **Intent Classification** — routes queries into: specific lookup / cross-experiment pattern / validity analysis.
2. **Retrieval** — semantic search over ChromaDB; filters on metadata where relevant.
3. **Synthesis** — reasons across retrieved experiments to identify patterns / contradictions.
4. **Bias & Validity Check** — analyzes for design flaws and surfaces structured flags.
5. **Answer Generation** — final natural-language response with citations + bias flags.

## Repository Structure
```
experimentation-intelligence-agent/
├── scripts/
│   └── generate_experiments.py    # synthetic dataset generator
├── src/
│   ├── ingestion/                 # LlamaIndex → ChromaDB pipeline
│   ├── agent/                     # LangGraph nodes + graph definition
│   ├── api/                       # FastAPI endpoints
│   └── utils/
├── data/                          # generated artifacts (gitignored)
├── tests/
├── docs/                          # gitignored reference notes
├── requirements.txt
├── README.md
└── CLAUDE.md
```

## Data Schema (key fields in each experiment record)
- `test_id` — 5-digit numeric string
- `product_line`, `page`, `feature_tested`
- `test_overview` → hypothesis, problem_statement, critical_questions, success_metrics
- `recipes` → list with Control + Recipe B/C/D, each with visitors/visits/hits
- `lifecycle` → assignment / SQA / go-live / end / deepdive / OM presentation dates
- `stakeholders` → OMs, Developers, Analysts, Focal Points
- `statistical_summary` → 10% confidence level, p-value, power, outcome
- `analysis.desktop` and `analysis.mobile` → per-device metric_results and story
- `test_summary` → recommendation ("Retain Control" or "Adopt Recipe X") + rationale
- `bias_flags` → list of structured flags with type, detail, severity

## Conventions
- **Confidence level: 10% (p < 0.10)** for declaring significance. Do not silently switch to 5%.
- **Recipe naming:** "Control" (never "Recipe A"), then "Recipe B", "Recipe C", "Recipe D".
- **Metric direction language:** Increased / Decreased / Flat.
- **Analytics granularity:** Visitors > Visits > Hits (three distinct levels).
- **Final recommendation phrasing:** "Retain Control" or "Adopt Recipe <X>".

## Critical Rules (DO NOT VIOLATE)
- **Never mention any prior employer anywhere** — in code, comments, commit messages, docs, READMEs, or PR descriptions. This is a public portfolio project. The terminology is realistic enterprise vocabulary; attribution to any specific company must not appear.
- Do not introduce prior-employer references, named executives, or claims that this recreates a specific internal company tool.
- Do not commit `data/experiments.json` or anything under `data/` — it is a generated artifact. The generator script is the source of truth.
- Do not commit `docs/` — internal reference material.
- Pin all dependency versions in `requirements.txt`. Apple Silicon environments break easily with floating versions of scipy, torch, and transformers.
- Bias flags are core to the value proposition — never silently weaken or remove the validity check node.
- Same-model evaluation (using the same LLM as judge and generator) introduces bias; if evals are added, acknowledge this explicitly.

## Coding Style
- Python 3.11+
- Type hints on all public functions
- Black formatting, isort, ruff
- Docstrings on every module and public function
- Prefer dataclasses or Pydantic models over dict-juggling

## Current Status
- ✅ Synthetic dataset generation (200 experiments)
- 🚧 ChromaDB ingestion pipeline — next up
- ⏳ LangGraph agent skeleton
- ⏳ FastAPI endpoint
- ⏳ Hugging Face Space deployment
- ⏳ Bias detection node (full implementation)
- ⏳ Local LLM benchmarking (Ollama vs Claude API)
- ⏳ Optional: dbt + Airflow layer
- ⏳ Optional: MCP tool layer

## Project Mantras
- **Deploy first, extend later.** A working Hugging Face Space beats a more complete local pipeline every time.
- **Single highest-leverage project > many partial ones.** Don't fragment effort.
- **FastAPI as connective tissue.** Every component should be wrappable behind a clean API.
- **Bias detection is the differentiator.** It's what makes this an "experimentation intelligence" agent and not just RAG-on-spreadsheets.
