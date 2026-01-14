# dsRNA Designer - Technical Plan v2

## Architecture Overview

A skill-based agent using `deepagents-cli` with:
- **Built-in tools** from deepagents (no custom tools needed)
- **Skills** = natural language instructions teaching the agent how to accomplish tasks
- **MCP Servers** = PubMed for literature search

```
┌─────────────────────────────────────────────────────────────────┐
│                    deepagents CLI Agent                         │
│              (Claude with system prompt + skills)               │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Built-in     │    │    Skills     │    │  MCP Servers  │
│    Tools      │    │  (markdown    │    │               │
│  (deepagents) │    │   prompts)    │    │ • PubMed      │
│               │    │               │    │               │
│ • shell       │    │ • fetch_genome│    │               │
│ • read_file   │    │ • lit_search  │    │               │
│ • write_file  │    │ • identify_genes               │
│ • edit_file   │    │ • design_dsrna│    │               │
│ • glob        │    │ • blast_screen│    │               │
│ • grep        │    │ • score_rank  │    │               │
│ • fetch_url   │    │ • gen_report  │    │               │
│ • web_search  │    │               │    │               │
└───────────────┘    └───────────────┘    └───────────────┘
```

## Built-in Tools (from deepagents)

Deepagents provides these tools automatically - **no custom code needed**:

| Tool | Purpose | Usage in dsRNA workflow |
|------|---------|------------------------|
| `shell` | Execute local commands | Run BLAST, Python scripts |
| `read_file` | Read file contents | Load genome FASTA, JSON data |
| `write_file` | Write to files | Save outputs, reports |
| `edit_file` | Modify existing files | Update results |
| `glob` | Find files by pattern | Locate output files |
| `grep` | Search in files | Find genes in FASTA |
| `fetch_url` | HTTP GET requests | Download from NCBI FTP |
| `web_search` | Search the web | Find documentation |
| `write_todos` | Task management | Track workflow progress |
| `task` | Delegate to subagents | Complex sub-tasks |

## MCP Server Integration

### PubMed MCP Server
URL: `https://pubmed.mcp.claude.com/mcp`

Tools available:
- `search_articles` - Search PubMed with queries
- `get_article_metadata` - Fetch article details by PMID
- `find_related_articles` - Find similar papers
- `get_full_text_article` - Get full text from PMC

### Configuration with langchain-mcp-adapters

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from deepagents import create_deep_agent

async def create_agent():
    mcp_client = MultiServerMCPClient({
        "pubmed": {
            "url": "https://pubmed.mcp.claude.com/mcp"
            # or via SSE transport if supported
        }
    })
    mcp_tools = await mcp_client.get_tools()

    agent = create_deep_agent(
        tools=mcp_tools,  # Add MCP tools to built-ins
        system_prompt=SYSTEM_PROMPT
    )
    return agent
```

## Skills Architecture

Skills are markdown files that teach the agent *how* to accomplish tasks using the built-in tools. Each skill contains:

1. **Purpose** - What this skill accomplishes
2. **When to use** - Trigger conditions
3. **Instructions** - Step-by-step approach
4. **Code examples** - Python/bash snippets to execute via `shell`
5. **Expected output** - What files to create

### Skill: `fetch_genome`

```markdown
## Skill: Fetch Genome

**Purpose:** Download CDS sequences for a target species from NCBI.

**When to use:** At the start of the workflow, when you need genome data for a species.

**Instructions:**
1. Use `fetch_url` to query NCBI E-utilities and resolve species name to TaxID
2. Query the Assembly database to find the RefSeq assembly
3. Get the FTP path from assembly summary
4. Download the CDS FASTA file using `fetch_url`
5. Save to `output/{species}/genome.fasta` using `write_file`

**Example - Get TaxID:**
Use `fetch_url` with:
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=taxonomy&term=Drosophila+suzukii&retmode=json
```
Parse the JSON response to extract the TaxID from `esearchresult.idlist[0]`.

**Example - Get Assembly:**
Use `fetch_url` with:
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=assembly&term=txid{TAXID}[Organism:exp]+AND+latest_refseq[filter]&retmode=json
```

**Alternative approach:**
If `fetch_url` doesn't handle large files well, use `shell` to run:
```bash
curl -L -o output/{species}/genome.fasta.gz "{FTP_URL}"
gunzip output/{species}/genome.fasta.gz
```

**Output:** `output/{species}/genome.fasta`
```

### Skill: `literature_search`

```markdown
## Skill: Literature Search

**Purpose:** Find published RNAi research for the target species using PubMed.

**When to use:** After fetching genome, to identify known effective RNAi targets.

**Instructions:**
1. Use the PubMed MCP tools to search for RNAi papers
2. Extract gene names from titles and abstracts
3. Save results to JSON file

**Using PubMed MCP:**
Call `search_articles` with query:
```
"{species}" AND (RNAi OR dsRNA OR "RNA interference" OR "gene silencing" OR lethal)
```

Then call `get_article_metadata` for the top 20-30 PMIDs.

**Gene extraction patterns:**
Look for these gene names in titles/abstracts:
- V-ATPase, vATPase, vha (vacuolar ATPase)
- Chitin synthase, ChS, CHS
- Acetylcholinesterase, AChE
- Tubulin, actin
- Ecdysone receptor, EcR
- Laccase, Snf7

**Output:** `output/{species}/literature.json`
```

### Skill: `identify_essential_genes`

```markdown
## Skill: Identify Essential Genes

**Purpose:** Find essential genes in the target genome by matching against known essential genes.

**When to use:** After genome fetch and literature search.

**Instructions:**
1. Read the essential genes database from `data/essential_genes.json`
2. Parse the genome FASTA to get gene descriptions
3. Match genes by name/alias in descriptions
4. Score by: ortholog match + literature support
5. Return top 20 candidates with sequences

**Implementation via shell:**
Create a Python script and run it:

```python
# identify_genes.py
from Bio import SeqIO
import json

# Load essential genes DB
with open('data/essential_genes.json') as f:
    db = json.load(f)

# Parse genome
genes = list(SeqIO.parse('output/{species}/genome.fasta', 'fasta'))

# Match by annotation
candidates = []
for record in genes:
    desc = record.description.lower()
    for essential in db['genes']:
        names = [essential['name'].lower()] + [a.lower() for a in essential.get('aliases', [])]
        if any(name in desc for name in names):
            candidates.append({
                'gene_id': record.id,
                'gene_name': essential['name'],
                'function': essential['function'],
                'sequence': str(record.seq),
                'length': len(record.seq)
            })

# Save results
with open('output/{species}/essential_genes.json', 'w') as f:
    json.dump(candidates[:20], f, indent=2)
```

Run with: `shell("python identify_genes.py")`

**Output:** `output/{species}/essential_genes.json`
```

### Skill: `design_dsrna`

```markdown
## Skill: Design dsRNA Candidates

**Purpose:** Design optimal dsRNA sequences for target genes using sliding window.

**When to use:** After identifying essential genes.

**Instructions:**
For each of the top 5 essential genes:
1. Apply sliding window (300bp, step 50bp)
2. Score each window by GC content, poly-N, position
3. Select top 3 non-overlapping candidates

**Scoring criteria:**
- GC 35-50%: +2 points
- GC 30-55%: +1 point
- No poly-N (4+ same nucleotide): +1 point
- Not in first 75bp: +1 point
- Not in last 50bp: +1 point

**Implementation via shell:**
```python
# design_dsrna.py
import json
import re

def design_candidates(sequence, gene_name, length=300, n=3):
    seq = sequence.upper()
    windows = []

    for start in range(0, len(seq) - length + 1, 50):
        window = seq[start:start+length]
        gc = (window.count('G') + window.count('C')) / length

        score = 0
        if 0.35 <= gc <= 0.50: score += 2
        elif 0.30 <= gc <= 0.55: score += 1
        if not re.search(r'([ATGC])\1{3,}', window): score += 1
        if start >= 75: score += 1
        if start + length <= len(seq) - 50: score += 1

        windows.append({
            'start': start, 'end': start+length,
            'sequence': window, 'gc': gc, 'score': score
        })

    # Select top non-overlapping
    windows.sort(key=lambda x: x['score'], reverse=True)
    selected = []
    used = set()
    for w in windows:
        if len(selected) >= n: break
        pos = set(range(w['start'], w['end']))
        if not pos & used:
            w['id'] = f"{gene_name}_{len(selected)+1}"
            selected.append(w)
            used.update(pos)
    return selected

# Load genes and design candidates
with open('output/{species}/essential_genes.json') as f:
    genes = json.load(f)

all_candidates = []
for gene in genes[:5]:
    candidates = design_candidates(gene['sequence'], gene['gene_name'])
    for c in candidates:
        c['gene_id'] = gene['gene_id']
        c['gene_name'] = gene['gene_name']
    all_candidates.extend(candidates)

with open('output/{species}/candidates.json', 'w') as f:
    json.dump(all_candidates, f, indent=2)
```

**Output:** `output/{species}/candidates.json` (15 candidates: 5 genes × 3 each)
```

### Skill: `blast_screen`

```markdown
## Skill: BLAST Off-Target Screening

**Purpose:** Screen dsRNA candidates against human and honeybee genomes.

**When to use:** After designing candidates, before final scoring.

**Prerequisites:** BLAST databases must exist at `data/blast_db/human_cds` and `data/blast_db/honeybee_cds`

**Instructions:**
1. For each candidate sequence, write to temp FASTA
2. Run blastn against human and honeybee databases
3. Parse output to find max alignment length
4. Apply EPA safety thresholds

**Safety thresholds:**
- <15bp match: ✅ Safe
- 15-18bp match: ⚠️ Caution
- ≥19bp match: ❌ Reject

**Implementation via shell:**
```bash
# For each candidate
echo ">candidate_1" > /tmp/query.fa
echo "ATGCATGC..." >> /tmp/query.fa

blastn -query /tmp/query.fa -db data/blast_db/human_cds \
  -word_size 7 -outfmt "6 qseqid sseqid length" \
  -max_target_seqs 100 -evalue 10

# Parse output to find max length in column 3
```

**Full Python implementation:**
```python
# blast_screen.py
import subprocess
import json
import tempfile
import os

def blast_sequence(seq, db_path):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
        f.write(f">query\n{seq}\n")
        query_file = f.name

    try:
        result = subprocess.run([
            'blastn', '-query', query_file, '-db', db_path,
            '-word_size', '7', '-outfmt', '6',
            '-max_target_seqs', '100', '-evalue', '10'
        ], capture_output=True, text=True, timeout=60)

        max_len = 0
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('\t')
                if len(parts) >= 3:
                    max_len = max(max_len, int(parts[2]))
        return max_len
    finally:
        os.unlink(query_file)

# Load candidates
with open('output/{species}/candidates.json') as f:
    candidates = json.load(f)

results = []
for cand in candidates:
    human = blast_sequence(cand['sequence'], 'data/blast_db/human_cds')
    bee = blast_sequence(cand['sequence'], 'data/blast_db/honeybee_cds')
    max_match = max(human, bee)

    results.append({
        'id': cand['id'],
        'human_match': human,
        'honeybee_match': bee,
        'status': 'safe' if max_match < 15 else ('caution' if max_match < 19 else 'reject')
    })

with open('output/{species}/blast_results.json', 'w') as f:
    json.dump(results, f, indent=2)
```

**Output:** `output/{species}/blast_results.json`
```

### Skill: `score_and_rank`

```markdown
## Skill: Score and Rank Candidates

**Purpose:** Compute final scores combining efficacy and safety.

**When to use:** After BLAST screening.

**Scoring formula:**
```
Efficacy = 0.3×GC_score + 0.2×poly_n_score + 0.2×position_score + 0.3×gene_score
Safety = 1.0 if <15bp, 0.7 if 15-18bp, 0.0 if ≥19bp
Combined = Efficacy × Safety
```

**Implementation:** Merge candidates.json and blast_results.json, calculate scores, sort by combined score.

**Output:** `output/{species}/ranked_candidates.json`
```

### Skill: `generate_report`

```markdown
## Skill: Generate Report

**Purpose:** Create comprehensive markdown report.

**When to use:** Final step after scoring.

**Report structure:**
1. Executive Summary (species, top recommendation)
2. Top Candidates Table
3. Candidate Details (sequence, scores, off-target)
4. Off-Target Analysis Table
5. Methods

**Use `write_file` to create `output/{species}/report.md`**
```

## File Structure

```
dsrna-designer/
├── dsrna_agent/
│   ├── __init__.py
│   ├── agent.py           # Agent config with skills in system prompt
│   └── skills.py          # Skill loader (reads skills/*.md)
├── skills/                # Skill definitions (markdown)
│   ├── fetch_genome.md
│   ├── literature_search.md
│   ├── identify_genes.md
│   ├── design_dsrna.md
│   ├── blast_screen.md
│   ├── score_rank.md
│   └── generate_report.md
├── data/
│   ├── essential_genes.json   # Keep existing
│   └── blast_db/              # Keep existing
├── output/
├── pyproject.toml
└── README.md
```

## System Prompt Structure

```markdown
You are an RNAi biopesticide design assistant. Design dsRNA molecules that
kill target pests while avoiding off-target effects in humans and beneficial insects.

## Available Tools
You have access to these built-in tools:
- `shell(command)` - Execute bash commands (for BLAST, Python scripts, curl)
- `read_file(path)` - Read file contents
- `write_file(path, content)` - Write to files
- `fetch_url(url)` - HTTP GET requests
- `glob(pattern)` - Find files
- `grep(pattern, path)` - Search in files

## MCP Tools
- PubMed: `search_articles`, `get_article_metadata`, `find_related_articles`

## Workflow
1. fetch_genome - Download CDS from NCBI
2. literature_search - Find RNAi papers via PubMed MCP
3. identify_essential_genes - Match against known essentials
4. design_dsrna - Sliding window candidate design
5. blast_screen - Off-target safety check
6. score_and_rank - Final scoring
7. generate_report - Create markdown report

## Skills
[Skills loaded from skills/*.md files]

## Output Directory
All files should be written to: output/{species_slug}/
Use lowercase with underscores for species slug (e.g., "drosophila_suzukii")
```

## Implementation Tasks

### Phase 1: Skills (no code, just markdown)
1. [ ] Write `skills/fetch_genome.md`
2. [ ] Write `skills/literature_search.md`
3. [ ] Write `skills/identify_genes.md`
4. [ ] Write `skills/design_dsrna.md`
5. [ ] Write `skills/blast_screen.md`
6. [ ] Write `skills/score_rank.md`
7. [ ] Write `skills/generate_report.md`

### Phase 2: Agent Setup
8. [ ] Create skill loader (`dsrna_agent/skills.py`)
9. [ ] Configure agent with system prompt + skills (`dsrna_agent/agent.py`)
10. [ ] Configure PubMed MCP server integration
11. [ ] Update pyproject.toml with `langchain-mcp-adapters`

### Phase 3: Testing
12. [ ] End-to-end test with Drosophila suzukii

## Key Benefits of This Approach

| Aspect | Benefit |
|--------|---------|
| **No custom tools** | Uses deepagents built-ins only |
| **Skills as markdown** | Easy to iterate and improve |
| **Agent flexibility** | Can adapt code to handle edge cases |
| **Debugging** | Watch agent's reasoning and code execution |
| **Extensibility** | Add skills by writing markdown |
| **PubMed MCP** | Robust, maintained literature search |
