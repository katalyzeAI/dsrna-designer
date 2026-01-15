"""dsRNA Designer Agent - Flexible research assistant for RNAi biopesticide design.

This agent uses:
- FilesystemBackend for direct filesystem access (genomes, BLAST DBs, outputs)
- SkillsMiddleware for progressive disclosure of dsRNA design skills
- MCP integration for PubMed literature search
- Fundamental tools only (filesystem, shell) - no hardcoded domain tools

The agent assists with partial tasks, research, or complete workflows,
with human confirmation at each major step.
"""

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

PROJECT_ROOT = Path(__file__).parent.parent
MCP_CONFIG_PATH = PROJECT_ROOT / "mcp_config.json"

# Skills are stored in the package directory
SKILLS_DIR = Path(__file__).parent / "skills"


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


# System prompt - describes role, does NOT hardcode workflow
SYSTEM_PROMPT = """You are an agricultural biotechnology research assistant specializing in
RNAi-based biopesticides. You help plant scientists and agricultural researchers design
dsRNA molecules for sustainable, species-specific pest management.

## Background

RNA interference (RNAi) biopesticides are an EPA-registered class of agricultural pest
management tools. Unlike broad-spectrum chemical pesticides, RNAi biopesticides use
double-stranded RNA (dsRNA) that targets specific genes in agricultural pest insects,
providing species-specific control while minimizing environmental impact. This technology
is used in commercial products like Bayer's SmartStax PRO corn (targeting corn rootworm)
and is actively researched for managing crop pests like Colorado potato beetle, spotted
wing drosophila, and aphids.

Your role is to assist researchers in designing dsRNA sequences that:
1. Effectively target essential genes in agricultural pest insects
2. Pass rigorous safety screening against non-target organisms (humans, pollinators)
3. Meet EPA regulatory guidelines for environmental safety

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

## Workflow Steps

| Step | Skill | Key Output |
|------|-------|------------|
| 1 | fetch-genome | Genome stats, CDS sequences |
| 2 | literature-search | Gene targets from published RNAi studies |
| 3 | identify-genes | Gene ranking with evidence |
| 4 | design-dsrna | Candidate locations, GC distribution |
| 5 | blast-screen | Safety heatmap, match distribution |
| 6 | score-rank | Score breakdown, ranked list |
| 7 | generate-report | Final report, dashboard |

## Safety Screening (EPA Guidelines)

All candidates undergo mandatory off-target screening:
- REJECT any candidate with >=19bp contiguous match to human or honeybee genomes
- FLAG candidates with 15-18bp matches as "caution"
- Prefer genes with low conservation in beneficial insects and mammals

## Using Skills

Read the SKILL.md file for each step before executing. Skills contain:
- Detailed instructions for each workflow step
- Scripts to run for data processing and visualization
- Reference materials and templates

Example:
```
read_file dsrna_agent/skills/fetch-genome/SKILL.md
```

## Output Location

All artifacts are written to `output/{species_slug}/`:
- `genome.fasta` - Downloaded CDS sequences
- `essential_genes.json` - Ranked essential genes
- `candidates.json` - dsRNA candidates with scores
- `blast_results.json` - Off-target screening results
- `report.md` - Final report with recommendations
"""


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
    if mcp_tools:
        print(f"Loaded {len(mcp_tools)} MCP tools: {[t.name for t in mcp_tools]}")

    return create_deep_agent(
        model="claude-3-7-sonnet-20250219",
        tools=mcp_tools,  # Only MCP tools - fundamental tools come from deepagents
        system_prompt=SYSTEM_PROMPT,
        backend=backend,
        # SkillsMiddleware handles loading, parsing frontmatter, and progressive disclosure
        skills=[str(SKILLS_DIR) + "/"],
    )


def main():
    """CLI entry point for the dsRNA designer agent."""
    if len(sys.argv) < 2:
        print("Usage: dsrna-designer <query>")
        print('Example: dsrna-designer "Design dsRNA for Drosophila suzukii"')
        sys.exit(1)

    query = " ".join(sys.argv[1:])

    print("Starting dsRNA Designer Agent...")
    print(f"Query: {query}")
    print("-" * 50)

    agent = create_dsrna_agent()
    result = agent.invoke({"messages": [{"role": "user", "content": query}]})

    # Print final response
    final_message = result["messages"][-1].content
    print("\n" + "=" * 50)
    print("FINAL RESPONSE:")
    print("=" * 50)
    print(final_message)


if __name__ == "__main__":
    main()
