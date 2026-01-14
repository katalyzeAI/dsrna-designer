"""dsRNA Designer Agent - Main agent configuration and entry point."""

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from deepagents import create_deep_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

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


def load_mcp_tools():
    """Load tools from MCP servers defined in mcp_config.json."""
    if not MCP_CONFIG_PATH.exists():
        print(f"No MCP config found at {MCP_CONFIG_PATH}")
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

## Workflow

Follow these steps in order for each target species:

1. **fetch_genome**: Download CDS sequences for the target species from NCBI RefSeq
   - Input: species name (e.g., "Drosophila suzukii")
   - Output: Path to genome FASTA file

2. **literature_search**: Find published RNAi studies for this species
   - Input: species name
   - Output: List of papers with gene names mentioned

3. **identify_essential_genes**: Rank genes by essentiality
   - Input: species name, genome_path, list of literature gene names
   - Output: Top 20 essential genes with sequences and scores

4. **design_dsrna_candidates**: For the top 5 genes, design 3 dsRNA candidates each
   - Input: gene_sequence, gene_name, gene_id
   - Output: 3 candidate sequences with GC content and design scores
   - Run this tool 5 times (once per gene), collecting all 15 candidates

5. **run_offtarget_blast**: Screen ALL candidates against human and honeybee
   - Input: list of all 15 candidate dicts
   - Output: Off-target match lengths for each candidate

6. **score_efficiency**: Compute final rankings
   - Input: candidates list, blast_results list, gene_scores dict
   - Output: Candidates sorted by combined efficacy × safety score

7. **generate_report**: Write comprehensive report to output directory
   - Input: species name, scored_candidates list, essential_genes list
   - Output: Paths to report.md and candidates.json

## Safety Rules

- ALWAYS screen candidates against human and honeybee genomes using run_offtarget_blast
- REJECT any candidate with ≥19bp contiguous match to non-targets (EPA threshold)
- Flag candidates with 15-18bp matches as "caution" but don't reject
- Prefer genes with low conservation in non-target species
- Include clear safety assessment in the final report

## Output

All artifacts are written to output/{species_slug}/:
- genome.fasta: Downloaded CDS sequences
- literature_search.json: PubMed search results
- essential_genes.json: Ranked essential genes
- candidates.json: All candidates with scores
- report.md: Final report with recommendations

## Important Notes

- If fetch_genome fails, suggest alternative species names or check NCBI for the correct scientific name
- If BLAST databases are not found, inform the user to run setup_blast_db.sh first
- Always explain your reasoning when selecting genes and candidates
- Provide the user with actionable recommendations at the end
"""


def create_dsrna_agent():
    """Create and return the dsRNA designer agent."""
    # Load MCP tools from mcp_config.json
    mcp_tools = load_mcp_tools()
    if mcp_tools:
        print(f"Loaded {len(mcp_tools)} MCP tools: {[t.name for t in mcp_tools]}")

    all_tools = [
        fetch_genome,
        literature_search,
        identify_essential_genes,
        design_dsrna_candidates,
        run_offtarget_blast,
        score_efficiency,
        generate_report,
    ] + mcp_tools

    return create_deep_agent(
        tools=all_tools,
        system_prompt=SYSTEM_PROMPT,
        model="claude-sonnet-4-5-20250929",
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
