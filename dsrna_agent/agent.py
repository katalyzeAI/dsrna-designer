"""dsRNA Designer Agent - Flexible research assistant for RNAi biopesticide design.

This agent uses:
- LocalSandboxBackend for filesystem access + shell execution
- SkillsMiddleware for progressive disclosure of dsRNA design skills
- MCP integration for PubMed literature search
- Fundamental tools only (filesystem, shell) - no hardcoded domain tools

The agent assists with partial tasks, research, or complete workflows,
with human confirmation at each major step.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from deepagents.backends.protocol import ExecuteResponse, SandboxBackendProtocol

PROJECT_ROOT = Path(__file__).parent.parent
MCP_CONFIG_PATH = PROJECT_ROOT / "mcp_config.json"

# Skills are stored in the package directory
SKILLS_DIR = Path(__file__).parent / "skills"


class LocalSandboxBackend(FilesystemBackend, SandboxBackendProtocol):
    """FilesystemBackend with shell execution support.

    Extends FilesystemBackend to implement SandboxBackendProtocol,
    enabling the `execute` tool for running shell commands locally.
    """

    def __init__(self, root_dir: str | Path, **kwargs):
        super().__init__(root_dir=root_dir, **kwargs)
        self._id = f"local-sandbox-{id(self)}"

    @property
    def id(self) -> str:
        return self._id

    def execute(self, command: str) -> ExecuteResponse:
        """Execute a shell command in the project directory."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            output = result.stdout
            if result.stderr:
                output += "\n" + result.stderr if output else result.stderr
            return ExecuteResponse(
                output=output or "",
                exit_code=result.returncode,
                truncated=False,
            )
        except subprocess.TimeoutExpired:
            return ExecuteResponse(
                output="Command timed out after 5 minutes",
                exit_code=-1,
                truncated=False,
            )
        except Exception as e:
            return ExecuteResponse(
                output=f"Error executing command: {e}",
                exit_code=-1,
                truncated=False,
            )


@tool
def fetch_url(url: str) -> str:
    """Fetch content from a URL.

    Args:
        url: The URL to fetch content from.

    Returns:
        The text content of the response, or an error message.
    """
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text[:50000]  # Limit response size
    except httpx.HTTPStatusError as e:
        return f"HTTP error {e.response.status_code}: {e.response.reason_phrase}"
    except httpx.RequestError as e:
        return f"Request failed: {e}"
    except Exception as e:
        return f"Error fetching URL: {e}"


def _sanitize_nones(obj):
    """Recursively replace None values with empty strings in dicts/lists."""
    if obj is None:
        return ""
    if isinstance(obj, dict):
        return {k: _sanitize_nones(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_nones(item) for item in obj]
    return obj


def _wrap_tool_with_sanitizer(tool):
    """Wrap a tool to sanitize None values in its output."""
    original_invoke = tool.invoke

    def sanitized_invoke(*args, **kwargs):
        result = original_invoke(*args, **kwargs)
        return _sanitize_nones(result)

    tool.invoke = sanitized_invoke
    return tool


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
        tools = asyncio.run(
            MultiServerMCPClient(connections, tool_name_prefix=True).get_tools()
        )
        # Wrap tools to handle None values in responses (schema validation fix)
        return [_wrap_tool_with_sanitizer(t) for t in tools]
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

## IMPORTANT: No Subagent Delegation

**DO NOT use the `task` tool to delegate work to subagents.** Execute all steps yourself
directly, maintaining full context and presenting results to the user at each checkpoint.
This ensures the user can review and adjust at every step.

## How to Help

- **Partial tasks**: User may ask for just one step (e.g., "search for RNAi papers")
- **Research**: User may want to explore without running the full workflow
- **Complete workflow**: For full dsRNA design, use the `full-workflow` skill

## Complete Workflow Mode

Trigger phrases: "design dsRNA for {species}", "run complete workflow", "full analysis"

**When user requests a complete workflow:**
1. Read the `full-workflow` skill: `dsrna_agent/skills/full-workflow/SKILL.md`
2. Follow the skill instructions exactly
3. STOP after each step and present results
4. Wait for user confirmation before proceeding to next step
5. Allow user to adjust, skip, or provide feedback at any checkpoint

## Workflow Steps

| Step | Skill | Key Output |
|------|-------|------------|
| 1 | fetch-genome | Genome stats, CDS sequences |
| 2 | identify-genes | Gene ranking with evidence |
| 3 | design-dsrna | Candidate locations, GC distribution |
| 4 | blast-screen | Safety heatmap, match distribution |
| 5 | score-rank | Score breakdown, ranked list |
| 6 | generate-report | Final report, dashboard |

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
    - LocalSandboxBackend for file access + shell execution
    - SkillsMiddleware loads skills from dsrna_agent/skills/
    - MCP tools for PubMed (if configured)
    - fetch_url tool for web requests
    """
    # LocalSandboxBackend extends FilesystemBackend with execute() for shell commands
    backend = LocalSandboxBackend(root_dir=PROJECT_ROOT)

    # MCP tools (PubMed)
    mcp_tools = load_mcp_tools()
    if mcp_tools:
        print(f"Loaded {len(mcp_tools)} MCP tools: {[t.name for t in mcp_tools]}")

    # Custom tools: fetch_url for web requests
    custom_tools = [fetch_url]

    return create_deep_agent(
        model="claude-3-7-sonnet-20250219",
        tools=mcp_tools + custom_tools,
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
