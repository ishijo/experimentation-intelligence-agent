# Experimentation Intelligence Agent

## The Idea
 
Most organizations that run A/B tests at scale accumulate hundreds of experiment results over time. These live in spreadsheets, wikis, or internal dashboards — and are almost never revisited systematically. Teams re-run experiments that already have answers, make decisions without consulting prior learnings, and repeat the same design mistakes across test groups.
 
This project builds an intelligent agent that sits on top of a corpus of historical A/B test data and answers questions like:
 
- "Have we ever tested early checkout prompts on mobile users?"
- "Which experiments targeting new users had statistically significant results?"
- "Are there patterns in what made our highest-uplift experiments succeed?"
- "Flag any experiments in this corpus where the treatment and control groups may have been imbalanced."
The agent doesn't just retrieve — it reasons across multiple experiments, synthesizes patterns, and proactively surfaces potential issues in experiment design. This is the public, fully engineered version of a concept I filed a patent for at Dell Technologies in 2024: the Test Insights Advisor Chatbot.
 
---
 
## Why This Project
 
At Dell's experimentation team, I ran A/B tests on live traffic, built recommender systems validated by experiments, and designed tools to manage experiment quality at scale. One recurring problem: institutional knowledge about past experiments was trapped in documentation that nobody searched. I built an internal chatbot to solve this, which became a patented tool recognized by Dell's SVP.
 
This project rebuilds that idea from scratch using a modern open-source AI engineering stack — making it public, reproducible, and extensible. It's grounded in real domain expertise, not a tutorial.
 
---
 
## Architecture
 
The system is structured as a multi-node reasoning graph built with LangGraph. Rather than a single retrieval-then-answer step, the agent routes each query through a deliberate reasoning pipeline:
 
**Node 1 — Intent Classification**
Parses the incoming query and classifies what kind of reasoning is needed: specific experiment lookup, cross-experiment pattern synthesis, or experiment validity analysis.
 
**Node 2 — Retrieval**
Queries ChromaDB using semantic similarity search over LlamaIndex-generated embeddings of the experiment corpus. Returns the most relevant experiment documents ranked by relevance.
 
**Node 3 — Synthesis**
Uses LangChain to reason across retrieved experiments, identifying patterns, contradictions, or recurring themes in outcomes and decisions.
 
**Node 4 — Bias & Validity Check**
Analyzes retrieved experiments for common experiment design flaws: underpowered tests given reported effect sizes, imbalanced segment representation across treatment and control, and results that may not generalize across user subgroups. This node produces structured flags with explanations.
 
**Node 5 — Answer Generation**
Generates a final natural language response with citations to specific experiments, synthesis of patterns, and any bias flags surfaced in Node 4. Powered by a locally quantized Llama/Mistral model via Ollama (free, runs on Apple Silicon) with an optional API fallback.
 
The full agent is served as a REST API via FastAPI and deployed on Hugging Face Spaces.
 
---
 
## Tech Stack
 
| Component | Tool | Why |
|---|---|---|
| Agent graph / reasoning flow | LangGraph | Multi-step agentic reasoning with explicit state |
| Document ingestion & indexing | LlamaIndex | Best-in-class for corpus ingestion pipelines |
| Vector store | ChromaDB | Open-source, runs locally, no API key needed |
| Retrieval chain | LangChain | Tool orchestration between retrieval and LLM |
| LLM (primary) | Ollama + Llama 3 / Mistral (quantized) | Free, local, Apple Silicon optimized |
| LLM (fallback) | Anthropic Claude API | Higher quality for complex synthesis |
| Data pipeline | dbt + Airflow | Transforms raw experiment logs, schedules re-ingestion |
| Model serving | FastAPI | REST endpoint for the full agent |
| Deployment | Hugging Face Spaces | Free, public, linkable |
| MCP tools | Custom MCP layer | Exposes agent capabilities to Claude Desktop / MCP clients |
 
Everything in this stack is either fully open-source or available on a free tier.
 
---
 
## The Dataset
 
The experiment corpus is synthetically generated but designed to reflect realistic experimentation patterns rather than LLM-imagined ones.
 
The generation approach uses **template-based synthesis with randomized parameters** — not a prompt asking an LLM to "generate 100 A/B tests." The structure of each experiment record (hypothesis, metric, user segments tested, sample sizes, observed effect, statistical power, outcome, decision made) is defined explicitly, based on two years of real experimentation work. Parameters are then drawn from realistic distributions:
 
- Sample sizes from log-normal distributions matching real traffic volumes
- Effect sizes in the 1–5% range typical for conversion rate experiments
- Segment breakdowns across realistic user taxonomies (new vs. returning, mobile vs. desktop, geography)
- Outcomes correlated with sample size to reflect real statistical power constraints
This approach means the *structure and realism* of the data comes from domain expertise, while the *variation* is programmatic and unbiased by any single generation model. The bias check node is also tested against deliberately flawed synthetic experiments — underpowered tests, imbalanced groups — to validate its detection capability.
 
---
 
## Responsible AI / Bias Mitigation
 
The bias check node isn't a bolted-on ethics layer — it's core to the use case. Common experiment validity problems this agent detects:
 
- **Underpowered tests**: flags experiments where the reported effect size would require a larger sample than was used, meaning the result may be a false positive
- **Segment imbalance**: detects when treatment and control group compositions differ meaningfully across key user attributes
- **Generalizability warnings**: surfaces when a result was measured on a narrow segment but the decision was applied broadly
- **Novelty effect flags**: identifies short-duration experiments where initial lift may not reflect sustained behavior change
This directly extends work I did at Dell building automated clustering tools to ensure balanced A/B test groups — now made intelligent and language-queryable.
 
---
 
## Inference Optimization
 
The agent runs on a quantized local model by default (GGUF format via Ollama), which brings inference costs to zero and makes the project fully reproducible without any API keys. The README includes a benchmarked comparison between the quantized local model and the Claude API fallback across three dimensions: latency, cost per query, and answer quality on a set of held-out test questions. This documents the real trade-off engineers face when choosing between local and API-hosted inference.
 
---
 
## MCP Integration
 
The agent's core capabilities are exposed as MCP tools, making them callable from Claude Desktop or any MCP-compatible client:
 
- `search_experiments(query)` — semantic search over the experiment corpus
- `check_experiment_validity(experiment_id)` — runs the bias check node on a specific experiment
- `synthesize_patterns(topic)` — cross-experiment synthesis on a given theme
This means the agent isn't just a standalone app — it's composable infrastructure that can be plugged into other AI workflows.
 
---
 
## Data Pipeline (dbt + Airflow)
 
Raw experiment logs (simulated as structured JSON) are transformed into clean, enriched experiment summaries using dbt models. Airflow schedules nightly re-ingestion into ChromaDB when new experiments are added to the corpus — simulating the production pattern where an experimentation platform continuously produces new results that the agent should learn from.
 
This layer makes the project feel production-grade: the vector store isn't a static file, it's a maintained, governed artifact with a real update cadence.
 
---
 
## What This Demonstrates
 
For **MLE roles**: model serving via FastAPI, inference optimization with quantized models, MLflow-adjacent experiment tracking thinking, data pipeline design with dbt and Airflow, deployment on cloud-adjacent infrastructure.
 
For **AI Engineer roles**: RAG architecture, vector database design and management, agentic multi-step reasoning with LangGraph, LLM API integration, evaluation pipeline thinking, MCP tool development.
 
For **Product DS roles**: deep experimentation domain knowledge, bias detection and responsible AI in the context of A/B testing, the full cycle from data → model → decision → deployment.
 
---
 
## Build Plan (Sprint Structure)
 
**Weekend 1 — Core agent (portfolio-ready at end of this)**
- Synthetic dataset generation with parameter randomization
- LlamaIndex ingestion → ChromaDB
- LangGraph graph with 4 nodes (intent, retrieval, synthesis, answer)
- FastAPI endpoint
- Basic README and Hugging Face deployment
**Weekend 2 — Bias check + inference comparison**
- Bias/validity check node (Node 4)
- Ollama local model setup + API fallback
- Benchmarked comparison in README
- Responsible AI documentation
**Weekend 3 — Pipeline + MCP (optional but strong)**
- dbt models for raw log transformation
- Airflow DAG for scheduled re-ingestion
- MCP tools layer
- Final README polish and demo GIF
---
 
## Resume Bullet (draft, update with actual metrics after build)
 
*Experimentation Intelligence Agent — Agentic RAG system for querying and synthesizing historical A/B test corpora; multi-node LangGraph reasoning pipeline with built-in experiment bias detection; served via FastAPI, deployed on Hugging Face Spaces; local inference via quantized Llama (Ollama) with benchmarked API comparison; extends Dell patent (2024) on experimentation insight retrieval.*
