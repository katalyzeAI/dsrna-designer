# dsRNA Designer

An AI-powered research assistant for designing safe, effective dsRNA molecules for RNAi biopesticides.

## Overview

dsRNA Designer helps researchers design double-stranded RNA (dsRNA) molecules that can silence genes in target pest species while ensuring safety for humans and beneficial insects like honeybees. The agent uses the `deepagents` library with skills-based progressive disclosure.

## Features

- **Flexible Assistance**: Get help with partial tasks, research questions, or complete end-to-end workflows
- **Human-in-the-Loop**: Confirms after each major step in complete workflows
- **Safety First**: Automatic BLAST screening against human and honeybee genomes (EPA guidelines)
- **Skills-Based Architecture**: Transparent, readable markdown instructions the agent follows
- **Literature Integration**: PubMed search via MCP for evidence-based gene target selection

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd dsrna-designer

# Create virtual environment and install dependencies
uv sync

# Set up BLAST databases for off-target screening
./setup_blast_db.sh
```

### Requirements

- Python 3.11+
- BLAST+ (`brew install blast` on macOS)
- API key for Claude (set `ANTHROPIC_API_KEY` in `.env`)

## Usage

### CLI

```bash
# Full workflow
dsrna-designer "Design dsRNA for Drosophila suzukii"

# Partial task
dsrna-designer "Search for RNAi papers on whitefly"

# Research question
dsrna-designer "What makes a good dsRNA target gene?"
```

### Python API

```python
from dsrna_agent import create_dsrna_agent

agent = create_dsrna_agent()
result = agent.invoke({
    "messages": [{"role": "user", "content": "Design dsRNA for Bemisia tabaci"}]
})
print(result["messages"][-1].content)
```

### LangGraph Server

Run the agent as a web service with LangGraph:

```bash
# Install dev dependencies (includes langgraph-cli)
uv sync --extra dev

# Development server with hot reload
langgraph dev

# Production server
langgraph up
```

The server exposes the agent at `http://localhost:8000` with:
- REST API for agent invocation
- Streaming responses
- Thread management for conversation persistence
- LangGraph Studio UI for debugging

## Workflow Steps

When running a complete design workflow, the agent executes these steps:

| Step | Skill | Output |
|------|-------|--------|
| 1 | `fetch-genome` | CDS sequences from NCBI RefSeq |
| 2 | `literature-search` | Gene targets from published RNAi studies |
| 3 | `identify-genes` | Essential gene ranking with evidence |
| 4 | `design-dsrna` | dsRNA candidates (300bp, optimal GC) |
| 5 | `blast-screen` | Off-target matches (human, honeybee) |
| 6 | `score-rank` | Combined efficacy x safety scores |
| 7 | `generate-report` | Final report with recommendations |

After each step, the agent presents results and asks "Proceed to next step?" before continuing.

## Output

All artifacts are written to `output/{species_slug}/`:

```
output/drosophila_suzukii/
├── genome.fasta          # Downloaded CDS sequences
├── literature_search.json # PubMed results
├── essential_genes.json  # Ranked gene targets
├── candidates.json       # dsRNA candidates with scores
├── blast_results.json    # Off-target screening
└── report.md             # Final recommendations
```

## Safety Thresholds (EPA Guidelines)

| Max Match Length | Status | Action |
|------------------|--------|--------|
| < 15 bp | Safe | Proceed |
| 15-18 bp | Caution | Flag but allow |
| >= 19 bp | Reject | Exclude from results |

## Architecture

```
dsrna_agent/
├── agent.py              # Agent configuration
├── graph.py              # LangGraph server entrypoint
├── skills/               # Markdown instructions + scripts
│   ├── fetch-genome/
│   │   ├── SKILL.md      # Instructions for the agent
│   │   └── scripts/      # Python scripts to execute
│   ├── design-dsrna/
│   ├── blast-screen/
│   └── ...
└── __init__.py
langgraph.json            # LangGraph server configuration
```

**Key Design Principles:**

1. **Skills as Knowledge**: Skills are markdown files teaching the agent HOW to accomplish tasks using fundamental tools (`read_file`, `write_file`, `execute`, `glob`, `grep`)

2. **Progressive Disclosure**: Only skill metadata (~100 tokens) loads at startup. Full instructions load on-demand when a skill is activated.

3. **No Hardcoded Tools**: The agent uses fundamental tools to run scripts bundled with each skill, rather than custom Python tool functions.

## Configuration

### Environment Variables

Create a `.env` file:

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

### MCP Integration (Optional)

For PubMed search, create `mcp_config.json`:

```json
{
  "mcpServers": {
    "pubmed": {
      "url": "https://pubmed.mcp.claude.com/mcp",
      "transport": "http"
    }
  }
}
```

## Development

```bash
# Install in development mode
uv sync

# Run tests
pytest

# Format code
ruff format .
ruff check --fix .
```

## License

MIT

## References

- [deepagents API Documentation](docs/deepagents-api.md)
