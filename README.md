# Experimentation Intelligence Agent

**A conversational RAG system for querying, synthesizing, and learning from historical A/B test results — with built-in experiment validity analysis.**

---

## Overview

Teams that run A/B tests at scale accumulate hundreds of experiment results over time. These live in spreadsheets, wikis, or internal dashboards — and are almost never revisited systematically. Teams re-run experiments that already have answers, make decisions without consulting prior learnings, and repeat the same design mistakes across test groups.

The Experimentation Intelligence Agent sits on top of a corpus of historical experiment data and answers questions in natural language:

- *"Have we ever tested early checkout prompts on mobile users?"*
- *"Which experiments targeting new users had statistically significant results?"*
- *"Are there patterns in what made our highest-uplift experiments succeed?"*
- *"Flag any experiments in this corpus where treatment and control groups may have been imbalanced."*

The agent doesn't just retrieve — it reasons across multiple experiments, synthesizes patterns, and proactively surfaces potential issues in experiment design. It is built as a multi-node reasoning graph using LangGraph, backed by a ChromaDB vector store populated via LlamaIndex, and served through a FastAPI REST interface.

---

## Architecture

The system is structured as a multi-node reasoning graph. Rather than a single retrieval-then-answer step, each query is routed through a deliberate reasoning pipeline:

**Node 1 — Intent Classification**
Parses the incoming query and classifies what kind of reasoning is needed: specific experiment lookup, cross-experiment pattern synthesis, or experiment validity analysis.

**Node 2 — Retrieval**
Queries ChromaDB using semantic similarity search over LlamaIndex-generated embeddings of the experiment corpus. Returns the most relevant experiment documents ranked by relevance.

**Node 3 — Synthesis**
Reasons across retrieved experiments, identifying patterns, contradictions, or recurring themes in outcomes and decisions.

**Node 4 — Bias & Validity Check**
Analyzes retrieved experiments for common experiment design flaws: underpowered tests, imbalanced segment representation, novelty effects, and results applied beyond the segment they were measured on. Produces structured flags with explanations.

**Node 5 — Answer Generation**
Generates a final natural language response with citations to specific experiments, synthesized patterns, and any bias flags surfaced in Node 4. Powered by Ollama + Llama 3 locally, with Anthropic Claude API as a quality fallback.

The full agent is served as a REST API via FastAPI and deployed on Hugging Face Spaces.

![Architecture diagram coming soon](docs/architecture.png)

---

## Tech Stack

| Component | Tool | Why |
|---|---|---|
| Agent graph / reasoning flow | LangGraph | Multi-step agentic reasoning with explicit state |
| Document ingestion & indexing | LlamaIndex | Best-in-class for corpus ingestion pipelines |
| Vector store | ChromaDB | Open-source, runs locally, no API key required |
| LLM (primary) | Ollama + Llama 3 (quantized) | Free, local, Apple Silicon optimized |
| LLM (fallback) | Anthropic Claude API | Higher quality for complex synthesis tasks |
| Model serving | FastAPI | Lightweight REST endpoint for the agent |
| Deployment | Hugging Face Spaces | Free, public, shareable |
| Data pipeline (stretch) | dbt + Airflow | Scheduled re-ingestion when new experiments land |
| MCP tools (stretch) | Custom MCP layer | Exposes agent capabilities to Claude Desktop and MCP clients |

Everything in this stack is either fully open-source or available on a free tier.

---

## The Dataset

The experiment corpus is synthetically generated but designed to reflect realistic enterprise experimentation patterns rather than LLM-imagined ones.

The generation approach uses **template-based synthesis with randomized parameters** — not a prompt asking a model to "make up 200 A/B tests." The structure of each experiment record is defined explicitly: hypothesis, primary metric, user segments tested, sample sizes, observed effect size, statistical power, outcome, and decision. Parameters are drawn from distributions modeled on real experimentation dynamics:

- Sample sizes from log-normal distributions matching realistic traffic volumes
- Effect sizes in the 1–5% range typical of conversion rate experiments
- Segment breakdowns across user taxonomies: new vs. returning, mobile vs. desktop, geographic
- Outcomes correlated with sample size to reflect real statistical power constraints

This approach means the *structure and realism* of the data comes from domain expertise in experimentation, while the *variation* is programmatic and independent of any single generation model.

**Schema highlights:**
- 5-digit Test IDs (e.g., `TEST-10042`)
- Control group + Recipe B, C, D treatment arms
- 10% confidence level threshold
- Primary and secondary success metrics
- Desktop / mobile analysis splits
- Bias flags embedded per experiment (see Bias Detection below)

The corpus is generated by `scripts/generate_experiments.py` and outputs to `data/experiments.json` (200 experiments).

---

## Bias Detection

The bias check node is core to the system's value, not a bolt-on. Common experiment validity problems the agent detects and flags:

- **Underpowered tests** — experiments where the reported effect size would require a larger sample than was used, making the result a likely false positive
- **Segment imbalance** — treatment and control group compositions that differ meaningfully across key user attributes
- **Novelty effect risk** — short-duration experiments where initial lift may not reflect sustained behavior change
- **Multiple success metrics** — experiments measuring many outcomes simultaneously, increasing the risk of false positives through multiple comparisons

Each flag includes a structured explanation so downstream consumers can reason about the severity, not just the presence, of the issue.

---

## Quickstart

```bash
# Clone the repo
git clone https://github.com/your-username/experimentation-intelligence-agent.git
cd experimentation-intelligence-agent

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies (requirements.txt coming soon)
pip install -r requirements.txt

# Generate the synthetic experiment corpus
python scripts/generate_experiments.py
# Output: data/experiments.json (200 experiments)
```

> **Note:** The ingestion pipeline, agent graph, and API server are under active development. See Project Status below.

---

## Project Status

| Component | Status |
|---|---|
| Synthetic dataset generator (`scripts/generate_experiments.py`) | Complete |
| Experiment corpus (`data/experiments.json`, 200 records) | Complete |
| LlamaIndex ingestion into ChromaDB | In progress |
| LangGraph multi-node agent | Planned |
| FastAPI server | Planned |
| Hugging Face Spaces deployment | Planned |
| dbt + Airflow pipeline layer | Stretch goal |
| MCP tool exposure | Stretch goal |

---

## Roadmap

- [ ] ChromaDB ingestion via LlamaIndex
- [ ] LangGraph agent: intent classification → retrieval → synthesis → bias check → answer generation
- [ ] FastAPI REST server with `/query` and `/validate` endpoints
- [ ] Hugging Face Spaces deployment with public demo
- [ ] Inference benchmark: local Llama 3 vs. Claude API (latency, cost, quality)
- [ ] dbt models + Airflow DAG for scheduled corpus re-ingestion *(stretch)*
- [ ] MCP tool layer: `search_experiments`, `check_experiment_validity`, `synthesize_patterns` *(stretch)*

---

## License

MIT (license file to be added)
