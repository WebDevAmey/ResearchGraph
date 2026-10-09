# ResearchGraph

Turn a question into evidence-backed research. A LangGraph agent plans the
research, investigates topics in parallel on the web, and writes a cited report
with Claude.

## Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env        # add ANTHROPIC_API_KEY and TAVILY_API_KEY

.venv/bin/pytest            # offline tests, no API keys needed
.venv/bin/python -m app.cli "How effective are four-day work weeks?"
```

### Layout

```
backend/app/
  config.py            settings from env / .env
  agent/
    graph.py           parent graph + per-topic research subgraph
    state.py           shared state + reducers
    context.py         injected dependencies (LLM, search)
    schemas.py         LLM output schemas + domain models
    prompts.py         LangChain prompt templates
    citations.py       source numbering + citation validation
    nodes/             planner, researcher, evaluator, synthesizer
  services/
    llm.py             StructuredLLM port + Claude adapter
    search.py          SearchClient port + Tavily adapter
  cli.py               run a question from the terminal
```
