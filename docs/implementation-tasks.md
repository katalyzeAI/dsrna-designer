# Implementation Tasks

Simplified task breakdown using deepagents built-in tools only.

## Overview

**No custom tools needed!** Deepagents provides:
- `shell` - Run bash/Python commands
- `read_file` / `write_file` / `edit_file` - File operations
- `fetch_url` - HTTP requests
- `glob` / `grep` - File search
- `write_todos` - Task tracking

We just need to:
1. Write skill markdown files
2. Create a simple agent config that loads skills into system prompt
3. Configure PubMed MCP server

---

## Phase 1: Write Skills (Markdown Only)

### Task 1.1: `skills/fetch_genome.md`
**Effort:** Low

Teach agent to:
- Query NCBI E-utilities via `fetch_url`
- Resolve species → TaxID → Assembly → FTP path
- Download CDS FASTA (using `shell` + curl for large files)
- Save to `output/{species}/genome.fasta`

Include:
- NCBI API URL templates
- JSON parsing guidance
- Alternative download method via curl

---

### Task 1.2: `skills/literature_search.md`
**Effort:** Low

Teach agent to:
- Use PubMed MCP `search_articles` tool
- Use `get_article_metadata` for details
- Extract gene names from abstracts
- Save to `output/{species}/literature.json`

Include:
- Search query construction
- Gene name patterns to look for
- Output format

---

### Task 1.3: `skills/identify_genes.md`
**Effort:** Medium

Teach agent to:
- Read `data/essential_genes.json`
- Parse genome FASTA (using Python via `shell`)
- Match genes by annotation text
- Score and rank candidates
- Save to `output/{species}/essential_genes.json`

Include:
- Complete Python script for matching
- Scoring formula explanation

---

### Task 1.4: `skills/design_dsrna.md`
**Effort:** Medium

Teach agent to:
- Implement sliding window algorithm
- Calculate GC content
- Check for poly-N runs
- Select non-overlapping candidates
- Save to `output/{species}/candidates.json`

Include:
- Complete Python implementation
- Parameter explanations
- Edge case handling (short genes)

---

### Task 1.5: `skills/blast_screen.md`
**Effort:** Medium

Teach agent to:
- Run local BLAST+ via `shell`
- Parse tabular output
- Apply EPA safety thresholds
- Save to `output/{species}/blast_results.json`

Include:
- BLAST command with correct parameters
- Python script for batch processing
- Safety threshold table

---

### Task 1.6: `skills/score_rank.md`
**Effort:** Low

Teach agent to:
- Merge candidate and BLAST data
- Calculate efficacy score
- Calculate safety score
- Compute combined ranking
- Save to `output/{species}/ranked_candidates.json`

Include:
- Scoring formula
- Example calculations

---

### Task 1.7: `skills/generate_report.md`
**Effort:** Low

Teach agent to:
- Read all intermediate files
- Format markdown report
- Include tables, sequences, recommendations
- Save to `output/{species}/report.md`

Include:
- Report template
- Table formatting

---

## Phase 2: Agent Configuration

### Task 2.1: Create Skill Loader
**File:** `dsrna_agent/skills.py`
**Effort:** Low

```python
from pathlib import Path

def load_skills() -> str:
    """Load all skill files and concatenate into system prompt section."""
    skills_dir = Path(__file__).parent.parent / "skills"
    skills_text = []

    for skill_file in sorted(skills_dir.glob("*.md")):
        content = skill_file.read_text()
        skills_text.append(f"### {skill_file.stem}\n\n{content}")

    return "\n\n---\n\n".join(skills_text)
```

---

### Task 2.2: Agent Configuration
**File:** `dsrna_agent/agent.py`
**Effort:** Medium

Configure agent with:
- System prompt (role, workflow, safety rules)
- Skills (loaded from markdown)
- PubMed MCP tools (if available)

Key questions to resolve:
- How to configure remote MCP server in deepagents?
- Sync vs async invocation?

---

### Task 2.3: PubMed MCP Integration
**Effort:** Medium (depends on deepagents MCP support)

Options:
1. Use `langchain-mcp-adapters` with remote server URL
2. Use deepagents CLI MCP config
3. Fallback: Use `fetch_url` with PubMed E-utilities directly

Need to investigate:
- Does `MultiServerMCPClient` support HTTP/SSE remote servers?
- How does deepagents-cli handle MCP config?

---

### Task 2.4: Update Dependencies
**File:** `pyproject.toml`
**Effort:** Low

Add:
```toml
dependencies = [
    "deepagents-cli>=0.0.12",
    "langchain-mcp-adapters>=0.1.0",  # If needed for MCP
    "biopython>=1.84",
    "httpx>=0.27.0",
]
```

---

## Phase 3: Testing

### Task 3.1: End-to-End Test
**Effort:** Medium

Test with: `deepagents run dsrna_agent "Design dsRNA for Drosophila suzukii"`

Verify:
- [ ] Genome downloads successfully
- [ ] Literature search returns results
- [ ] Essential genes identified
- [ ] Candidates designed (15 total)
- [ ] BLAST screening runs
- [ ] Report generated

Success criteria:
- `output/drosophila_suzukii/report.md` exists
- All unsafe candidates rejected
- Clear recommendation provided

---

## Task Summary

| Phase | Task | Effort | Dependencies |
|-------|------|--------|--------------|
| 1 | fetch_genome.md | Low | None |
| 1 | literature_search.md | Low | None |
| 1 | identify_genes.md | Medium | None |
| 1 | design_dsrna.md | Medium | None |
| 1 | blast_screen.md | Medium | None |
| 1 | score_rank.md | Low | None |
| 1 | generate_report.md | Low | None |
| 2 | Skill loader | Low | Phase 1 |
| 2 | Agent config | Medium | Skill loader |
| 2 | MCP integration | Medium | Research needed |
| 2 | Dependencies | Low | None |
| 3 | E2E test | Medium | Phase 2 |

**Critical path:** Task 2.3 (MCP integration) - need to understand how deepagents handles remote MCP servers.

---

## Open Questions

1. **MCP Configuration:** How does deepagents-cli configure remote MCP servers? The examples show local command-based servers. For `https://pubmed.mcp.claude.com/mcp`, we need HTTP/SSE transport.

2. **Async vs Sync:** MCP tools require async invocation. Does this affect how we run via deepagents CLI?

3. **Fallback:** If MCP is complex to configure, should we fall back to direct PubMed E-utilities via `fetch_url`?
