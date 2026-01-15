# dsRNA Designer Agent Redesign Plan

## Overview

Redesign the dsRNA agent to be a flexible research assistant rather than a rigid workflow executor. The agent should assist with dsRNA biopesticide design tasks using fundamental tools and skills, without hardcoding specific workflows.

## Goals

1. **Remove CLI dependency** - Build entirely on `deepagents` library
2. **Skills as knowledge, not code** - Move skills into the Python module following [Anthropic Agent Skills spec](https://agentskills.io/specification)
3. **Fundamental tools only** - Use filesystem, shell, Python interpreter - no hardcoded domain tools
4. **Flexible assistance** - Help with partial tasks, research, or complete workflows
5. **Human-in-the-loop** - Confirm after each major step in complete workflows

## Architecture Changes

### 1. Remove `.deepagents` Directory

Move skills from `.deepagents/skills/` into the Python module, following the Agent Skills specification:

```
dsrna_agent/
├── __init__.py
├── agent.py                    # Main agent setup (includes system prompt)
├── skills/                     # Skills following Agent Skills spec
│   ├── fetch-genome/
│   │   ├── SKILL.md            # Required: frontmatter + instructions
│   │   ├── scripts/            # Executable code
│   │   │   └── plot_genome_stats.py
│   │   └── references/         # Additional docs (optional)
│   │       └── ncbi-api.md
│   ├── identify-genes/
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   │   └── ortholog_search.py
│   │   └── assets/
│   │       └── essential_genes.json
│   ├── design-dsrna/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── sliding_window.py
│   │       └── plot_candidates.py
│   ├── blast-screen/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── run_blast.py
│   │       └── plot_safety.py
│   ├── score-rank/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── score_candidates.py
│   ├── generate-report/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── build_report.py
│   └── literature-search/
│       ├── SKILL.md
│       └── references/
│           └── pubmed-queries.md
└── data/                       # Shared reference data
    └── blast_db/               # BLAST databases (external)
```

### 2. Agent Skills Specification Compliance

Each skill follows the [Agent Skills spec](https://agentskills.io/specification):

#### Directory Structure
```
skill-name/
├── SKILL.md          # Required: YAML frontmatter + markdown body
├── scripts/          # Optional: executable code
├── references/       # Optional: additional documentation
└── assets/           # Optional: static resources (templates, data)
```

#### SKILL.md Format
```markdown
---
name: fetch-genome
description: Download CDS sequences from NCBI RefSeq for a target species. Use when starting dsRNA design or when you need coding sequences for any organism.
license: MIT
compatibility: Requires curl, gunzip, and internet access to NCBI
metadata:
  author: katalyze
  version: "1.0"
---

# Fetch Genome

## When to Use
Use when you need coding sequences (CDS) for a pest species.

## Instructions

### Step 1: Create Output Directory
```bash
mkdir -p output/{species_slug}
```

### Step 2: Resolve Species to TaxID
Use `fetch_url` to query NCBI Taxonomy API...

## Scripts

Run the genome statistics script after download:
```bash
python scripts/plot_genome_stats.py --genome output/{species_slug}/genome.fasta
```

See [references/ncbi-api.md](references/ncbi-api.md) for API details.
```

#### Progressive Disclosure (per spec)

1. **Metadata** (~100 tokens): `name` and `description` loaded at startup for all skills
2. **Instructions** (<5000 tokens): Full `SKILL.md` body loaded when skill is activated
3. **Resources** (as needed): `scripts/`, `references/`, `assets/` loaded only when required

### 3. Remove Hardcoded Tools

**Remove from `tools.py`:**
- `fetch_genome`
- `literature_search`
- `identify_essential_genes`
- `design_dsrna_candidates`
- `run_offtarget_blast`
- `score_efficiency`
- `generate_report`

**Use fundamental tools instead (provided by deepagents):**
- `read_file` / `write_file` / `edit_file` - File operations
- `shell` - Execute scripts, curl, BLAST commands
- `glob` / `grep` - Find files and search content
- `fetch_url` - HTTP requests to NCBI APIs
- `web_search` - Research via Tavily

The agent uses skills (markdown instructions) to know HOW to accomplish tasks using these fundamental tools.

### 4. System Prompt

The system prompt describes the agent's role and behavior but does NOT list skills (the `SkillsMiddleware` automatically injects skill summaries):

```python
SYSTEM_PROMPT = """You are an RNAi biopesticide design assistant. You help researchers 
design safe, effective dsRNA molecules for pest control.

## How to Help

- **Partial tasks**: User may ask for just one step (e.g., "search for RNAi papers")
- **Research**: User may want to explore without running the full workflow  
- **Complete workflow**: If user requests full dsRNA design, run all steps but STOP 
  after each to confirm before proceeding

## Complete Workflow Mode

Trigger phrases: "design dsRNA for {species}", "run complete workflow", "full analysis"

When running complete workflow:
1. Execute each step using the relevant skill
2. Present results clearly
3. Ask "Proceed to next step?" before continuing
4. Allow user to adjust, skip, or stop at any point

## Safety Rules (EPA Guidelines)

- REJECT any candidate with ≥19bp contiguous match to human or honeybee
- FLAG candidates with 15-18bp matches as "caution"
- Always run BLAST screening before final recommendations
"""
```

The `SkillsMiddleware` appends a "Skills System" section to this prompt with:
- List of available skills (name + description from frontmatter)
- Instructions on how to read full skill content
- Paths to each skill's `SKILL.md`

### 5. Agent Implementation

```python
"""dsRNA Designer Agent - Flexible research assistant for RNAi biopesticide design."""

import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

PROJECT_ROOT = Path(__file__).parent.parent
MCP_CONFIG_PATH = PROJECT_ROOT / "mcp_config.json"

# Skills are stored in the package directory
SKILLS_DIR = Path(__file__).parent / "skills"

# System prompt - describes role, does NOT hardcode workflow
SYSTEM_PROMPT = """You are an RNAi biopesticide design assistant. You help researchers 
design safe, effective dsRNA molecules for pest control.

## How to Help

- **Partial tasks**: User may ask for just one step (e.g., "search for RNAi papers")
- **Research**: User may want to explore without running the full workflow  
- **Complete workflow**: If user requests full dsRNA design, run all steps but STOP 
  after each to confirm before proceeding

## Complete Workflow Mode

Trigger phrases: "design dsRNA for {species}", "run complete workflow", "full analysis"

When running complete workflow:
1. Execute each step using the relevant skill
2. Present results clearly
3. Ask "Proceed to next step?" before continuing
4. Allow user to adjust, skip, or stop at any point

## Safety Rules (EPA Guidelines)

- REJECT any candidate with ≥19bp contiguous match to human or honeybee
- FLAG candidates with 15-18bp matches as "caution"
- Always run BLAST screening before final recommendations
"""


def load_mcp_tools():
    """Load tools from MCP servers defined in mcp_config.json."""
    if not MCP_CONFIG_PATH.exists():
        return []

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        return []

    with open(MCP_CONFIG_PATH) as f:
        config = json.load(f)

    servers = config.get("mcpServers", {})
    connections = {
        name: {"url": cfg["url"], "transport": "streamable_http"}
        for name, cfg in servers.items()
        if cfg.get("url") and cfg.get("transport") in ("http", "sse")
    }

    if not connections:
        return []

    try:
        return asyncio.run(
            MultiServerMCPClient(connections, tool_name_prefix=True).get_tools()
        )
    except Exception:
        return []


def create_dsrna_agent():
    """Create the dsRNA design assistant.
    
    Uses deepagents library with:
    - FilesystemBackend for direct file access
    - SkillsMiddleware loads skills from dsrna_agent/skills/
    - MCP tools for PubMed (if configured)
    - No hardcoded domain tools - uses fundamental tools only
    """
    # FilesystemBackend for project file access (genomes, outputs, etc.)
    backend = FilesystemBackend(root_dir=PROJECT_ROOT)
    
    # MCP tools (PubMed)
    mcp_tools = load_mcp_tools()
    
    return create_deep_agent(
        model="claude-sonnet-4-5-20250929",
        tools=mcp_tools,
        system_prompt=SYSTEM_PROMPT,
        backend=backend,
        # SkillsMiddleware handles loading, parsing frontmatter, and progressive disclosure
        skills=[str(SKILLS_DIR) + "/"],
    )
```

The `create_deep_agent` function with `skills` parameter automatically:
- Loads skills from the specified directory via `SkillsMiddleware`
- Parses YAML frontmatter from each `SKILL.md`
- Injects skill summaries (name + description) into the system prompt
- Provides tools for the agent to read full skill instructions on-demand

### 6. Skill Scripts

Scripts are packaged WITH their skills per the Agent Skills spec. The agent executes them via shell:

```bash
# From within a skill's instructions
python dsrna_agent/skills/design-dsrna/scripts/sliding_window.py \
  --genes output/bemisia_tabaci/essential_genes.json \
  --output output/bemisia_tabaci/candidates.json
```

Each script should:
- Be self-contained with clear CLI interface
- Include `--help` documentation
- Handle errors gracefully with helpful messages
- Use relative paths from project root

Example script header:
```python
#!/usr/bin/env python3
"""Sliding window dsRNA candidate design.

Usage:
    python sliding_window.py --genes GENES_JSON --output OUTPUT_JSON [--length 300]
"""
import argparse
import json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--genes", required=True, help="Path to essential_genes.json")
    parser.add_argument("--output", required=True, help="Output path for candidates.json")
    parser.add_argument("--length", type=int, default=300, help="dsRNA length (default: 300)")
    # ...
```

## Migration Steps

1. [x] Create `dsrna_agent/skills/` directory structure per Agent Skills spec
2. [x] Move each skill from `.deepagents/skills/{name}/` to `dsrna_agent/skills/{name}/`
3. [x] Move scripts INTO each skill's `scripts/` directory
4. [x] Update `agent.py` with new system prompt and skills path
5. [x] Delete `tools.py` (remove hardcoded tools)
6. [x] Update `pyproject.toml` to include package data
7. [x] Remove `.deepagents/` directory
8. [ ] Test partial task execution
9. [ ] Test complete workflow with step confirmations

## pyproject.toml Updates

```toml
[project]
name = "dsrna-designer"
# ...

[tool.setuptools.package-data]
dsrna_agent = [
    "skills/*/SKILL.md",
    "skills/*/scripts/*.py",
    "skills/*/references/*.md",
    "skills/*/assets/*",
]
```

## MCP Configuration

The agent uses MCP (Model Context Protocol) servers for external integrations. Create `mcp_config.json` in the project root:

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

### Available MCP Tools (PubMed)

When the PubMed MCP server is configured, the agent has access to:

| Tool | Description |
|------|-------------|
| `pubmed_search_articles` | Search PubMed for articles matching a query |
| `pubmed_get_article_metadata` | Get detailed metadata for a specific article |
| `pubmed_find_related_articles` | Find articles related to a given PMID |
| `pubmed_lookup_article_by_citation` | Find article by citation details |
| `pubmed_convert_article_ids` | Convert between PMID, DOI, PMC IDs |
| `pubmed_get_full_text_article` | Retrieve full text (when available) |
| `pubmed_get_copyright_status` | Check article copyright/access status |

### Loading MCP Tools

```python
import asyncio
import json
from pathlib import Path

def load_mcp_tools():
    """Load tools from MCP servers defined in mcp_config.json."""
    config_path = Path(__file__).parent.parent / "mcp_config.json"
    
    if not config_path.exists():
        return []

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        print("Warning: langchain-mcp-adapters not installed")
        return []

    with open(config_path) as f:
        config = json.load(f)

    servers = config.get("mcpServers", {})
    if not servers:
        return []

    connections = {}
    for name, server_config in servers.items():
        url = server_config.get("url")
        transport = server_config.get("transport", "http")
        if url and transport in ("http", "sse"):
            connections[name] = {"url": url, "transport": "streamable_http"}

    if not connections:
        return []

    async def get_tools():
        client = MultiServerMCPClient(connections, tool_name_prefix=True)
        return await client.get_tools()

    try:
        return asyncio.run(get_tools())
    except Exception as e:
        print(f"Warning: Failed to load MCP tools: {e}")
        return []
```

### Using PubMed in Skills

The `literature-search` skill should reference MCP tools:

```markdown
---
name: literature-search
description: Search PubMed for RNAi/dsRNA research on target species or genes
---

# Literature Search

## Tools Available

This skill uses PubMed MCP tools when available:
- `pubmed_search_articles` - Primary search tool
- `pubmed_get_article_metadata` - Get paper details
- `pubmed_find_related_articles` - Expand search

## Instructions

### Step 1: Search PubMed

Use the `pubmed_search_articles` tool:
```
query: "{species}" AND (RNAi OR dsRNA OR "RNA interference")
max_results: 50
```

### Step 2: Extract Gene Names

Parse article titles and abstracts for gene mentions...
```

## Example Interactions

### Partial Task
```
User: Search for RNAi papers on Drosophila suzukii

Agent: I'll search PubMed for RNAi research on this species.
[Reads literature-search/SKILL.md, uses web_search/fetch_url]
Found 23 papers. Key targets mentioned: vATPase (8 papers), chitin synthase (5)...
```

### Research Question
```
User: What makes a good dsRNA target gene?

Agent: [Explains from knowledge, may reference skills]
Good dsRNA targets have: high essentiality, low conservation in non-targets...
Would you like me to search for specific genes in a species?
```

### Complete Workflow
```
User: Design dsRNA for Bemisia tabaci

Agent: I'll run the complete dsRNA design workflow for Bemisia tabaci (whitefly).

## Step 1: Fetch Genome
[Reads fetch-genome/SKILL.md, executes steps]
Downloaded 18,432 CDS sequences from NCBI RefSeq.

**Proceed to Step 2 (Identify Essential Genes)?** [yes/no]

User: yes

Agent: ## Step 2: Identify Essential Genes
[Reads identify-genes/SKILL.md, runs scripts/ortholog_search.py]
Found 47 potential essential genes. Top candidates: vATPase, chitin synthase...

**Proceed to Step 3 (Design dsRNA Candidates)?** [yes/no]
```

## Benefits

1. **Standards compliant** - Follows [Agent Skills specification](https://agentskills.io/specification)
2. **Self-contained skills** - Scripts bundled with their skill, not scattered
3. **Progressive disclosure** - Efficient context usage per spec
4. **Flexibility** - Users can run any subset of tasks
5. **Transparency** - Skills are readable markdown
6. **Portability** - Skills packaged with module
7. **User control** - Confirmation points in complete workflows
8. **Research-friendly** - Agent helps with exploration, not just execution
