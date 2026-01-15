"""dsRNA Designer Agent - Built on deepagents library with skills middleware.

This agent uses:
- FilesystemBackend for direct filesystem access (genomes, BLAST DBs, outputs)
- SkillsMiddleware for progressive disclosure of dsRNA design skills
- MCP integration for PubMed literature search
- Local domain tools for BLAST screening and dsRNA design
"""

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

from .tools import (
    design_dsrna_candidates,
    fetch_genome,
    generate_report,
    identify_essential_genes,
    literature_search,
    run_offtarget_blast,
    score_efficiency,
)

PROJECT_ROOT = Path(__file__).parent.parent
MCP_CONFIG_PATH = PROJECT_ROOT / "mcp_config.json"
SKILLS_PATH = PROJECT_ROOT / ".deepagents" / "skills"


def load_mcp_tools():
    """Load tools from MCP servers defined in mcp_config.json."""
    if not MCP_CONFIG_PATH.exists():
        return []

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        print("Warning: langchain-mcp-adapters not installed, skipping MCP tools")
        return []

    with open(MCP_CONFIG_PATH) as f:
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
        tools = await client.get_tools()
        return tools

    try:
        return asyncio.run(get_tools())
    except Exception as e:
        print(f"Warning: Failed to load MCP tools: {e}")
        return []


SYSTEM_PROMPT = """You are an RNAi biopesticide design assistant. Your goal is to
design dsRNA molecules that effectively kill target pest species while ensuring
safety for humans and beneficial insects like honeybees.

## Core Workflow

Execute these steps in order for each target species. After each step, present
results and ask to proceed:

| Step | Skill | Key Output |
|------|-------|------------|
| 1 | fetch-genome | Genome stats, CDS sequences |
| 2 | identify-genes | Gene ranking with evidence |
| 3 | design-dsrna | Candidate locations, GC distribution |
| 4 | blast-screen | Safety heatmap, match distribution |
| 5 | score-rank | Score breakdown, ranked list |
| 6 | generate-report | Final report, dashboard |

## Safety Rules (EPA Guidelines)

- ALWAYS screen candidates against human and honeybee genomes
- REJECT any candidate with ≥19bp contiguous match to non-targets
- FLAG candidates with 15-18bp matches as "caution"
- Prefer genes with low conservation in non-target species

## Output Location

All artifacts are written to `output/{species_slug}/`:
- `genome.fasta` - Downloaded CDS sequences
- `essential_genes.json` - Ranked essential genes  
- `candidates.json` - dsRNA candidates with scores
- `blast_results.json` - Off-target screening results
- `report.md` - Final report with recommendations

## Important Notes

- Use the skills system for detailed step-by-step instructions
- Read SKILL.md files for each step before executing
- If BLAST databases are missing, inform user to run `./setup_blast_db.sh`
- Always explain your reasoning when selecting genes and candidates
"""


def create_dsrna_agent():
    """Create and return the dsRNA designer agent.
    
    Uses deepagents library with:
    - FilesystemBackend for direct file access
    - SkillsMiddleware for dsRNA design workflow skills
    - Domain-specific tools for BLAST, design, scoring
    - MCP tools for PubMed literature search
    """
    # Load MCP tools (PubMed, etc.)
    mcp_tools = load_mcp_tools()
    if mcp_tools:
        print(f"Loaded {len(mcp_tools)} MCP tools: {[t.name for t in mcp_tools]}")

    # Domain-specific tools
    domain_tools = [
        fetch_genome,
        literature_search,
        identify_essential_genes,
        design_dsrna_candidates,
        run_offtarget_blast,
        score_efficiency,
        generate_report,
    ]
    
    all_tools = domain_tools + mcp_tools

    # FilesystemBackend for direct filesystem access
    # This allows the agent to read/write files in the project directory
    backend = FilesystemBackend(root_dir=PROJECT_ROOT)

    # Skills are loaded from .deepagents/skills/
    # Each skill has a SKILL.md with instructions
    skills_sources = [str(SKILLS_PATH) + "/"]

    return create_deep_agent(
        model="claude-sonnet-4-5-20250929",
        tools=all_tools,
        system_prompt=SYSTEM_PROMPT,
        backend=backend,
        skills=skills_sources,
    )


def main():
    """CLI entry point for the dsRNA designer agent."""
    if len(sys.argv) < 2:
        print("Usage: dsrna-designer <query>")
        print('Example: dsrna-designer "Design dsRNA for Drosophila suzukii"')
        sys.exit(1)

    query = " ".join(sys.argv[1:])

    print(f"Starting dsRNA Designer Agent...")
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
