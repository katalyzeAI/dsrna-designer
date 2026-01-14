# dsRNA Designer - Minimal Prototype Plan

## Overview

Build a minimal prototype using `deepagents`. The agent orchestrates 7 tools to design dsRNA candidates for target pest species, writing all artifacts to files.

**Choices:**
- **BLAST:** Local BLAST+ installation for fast off-target screening
- **Gene data:** Curated real essential genes from DEG/FlyBase
- **Interface:** deepagents CLI (`deepagents run`)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              deepagents CLI                                     │
│         deepagents run dsrna_agent "Design dsRNA for..."        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     7 Tools (@tool decorated)                   │
├─────────────────────────────────────────────────────────────────┤
│ fetch_genome       │ Resolve species → download CDS from NCBI  │
│ literature_search  │ Query PubMed for known RNAi targets       │
│ identify_genes     │ Rank essential genes via orthology+lit    │
│ design_dsrna       │ Sliding window algorithm for candidates   │
│ run_blast          │ Off-target screening via local BLAST+     │
│ score_efficiency   │ Rule-based efficacy scoring               │
│ generate_report    │ Compile markdown report with rankings     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                        output/{species}/
                        ├── genome.fasta
                        ├── candidates.json
                        └── report.md
```

## File Structure

```
dsrna-designer/
├── dsrna_agent/             # Agent package
│   ├── __init__.py
│   ├── agent.py             # create_deep_agent() setup
│   └── tools.py             # All 7 tools
├── data/
│   ├── essential_genes.json # Curated DEG + FlyBase genes
│   └── blast_db/            # Pre-built BLAST databases
│       ├── human_cds.*      # Human CDS for off-target
│       └── honeybee_cds.*   # Honeybee CDS for off-target
├── output/                  # Generated artifacts
├── pyproject.toml
├── setup_blast_db.sh        # Script to download/build BLAST DBs
└── README.md
```

## Prerequisites

### BLAST+ Installation

```bash
# macOS
brew install blast

# Verify
blastn -version
```

### BLAST Database Setup

We need human and honeybee CDS databases for off-target screening:

```bash
# setup_blast_db.sh
mkdir -p data/blast_db
cd data/blast_db

# Download human RefSeq CDS
curl -O https://ftp.ncbi.nlm.nih.gov/refseq/H_sapiens/annotation/GRCh38_latest/refseq_identifiers/GRCh38_latest_rna.fna.gz
gunzip GRCh38_latest_rna.fna.gz
makeblastdb -in GRCh38_latest_rna.fna -dbtype nucl -out human_cds -title "Human CDS"

# Download honeybee RefSeq CDS
curl -O https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/003/254/395/GCF_003254395.2_Amel_HAv3.1/GCF_003254395.2_Amel_HAv3.1_rna.fna.gz
gunzip GCF_003254395.2_Amel_HAv3.1_rna.fna.gz
makeblastdb -in GCF_003254395.2_Amel_HAv3.1_rna.fna -dbtype nucl -out honeybee_cds -title "Honeybee CDS"
```

## Tool Implementations

### 1. `fetch_genome`

```python
@tool
def fetch_genome(species: str) -> str:
    """Fetch CDS sequences for a species from NCBI.

    Args:
        species: Scientific name (e.g., "Drosophila suzukii")

    Returns:
        Path to downloaded FASTA file
    """
```

**Implementation:**
1. Use NCBI E-utilities to resolve species → TaxID
2. Find RefSeq assembly via Assembly database
3. Download CDS FASTA via FTP or efetch
4. Save to `output/{species_slug}/genome.fasta`

**Key APIs:**
- `esearch.fcgi?db=taxonomy&term={species}` → TaxID
- `esearch.fcgi?db=assembly&term=txid{taxid}[Organism:exp]+AND+latest_refseq[filter]`
- FTP: `ftp.ncbi.nlm.nih.gov/genomes/all/GCF/.../cds_from_genomic.fna.gz`

### 2. `literature_search`

```python
@tool
def literature_search(species: str) -> list[dict]:
    """Search PubMed for known RNAi targets in this species.

    Args:
        species: Scientific name

    Returns:
        List of {gene_name, pmid, title, evidence_snippet}
    """
```

**Implementation:**
1. Query PubMed: `"{species}"[Title/Abstract] AND (RNAi OR dsRNA OR "RNA interference")`
2. Fetch abstracts for top 20 results
3. Use regex patterns to extract gene names (vATPase, chitin synthase, etc.)
4. Return structured results with citations

### 3. `identify_essential_genes`

```python
@tool
def identify_essential_genes(genome_path: str, literature_hits: list[dict]) -> list[dict]:
    """Identify essential genes in the target genome.

    Args:
        genome_path: Path to CDS FASTA
        literature_hits: Results from literature_search

    Returns:
        Ranked list of {gene_id, gene_name, function, score, evidence, sequence}
    """
```

**Implementation:**
1. Load curated essential genes list from `data/essential_genes.json`
2. BLAST target genome CDS against essential genes (tblastn or blastn)
3. Score hits by: e-value, coverage, literature support
4. Return top 20 with sequences for downstream design

### 4. `design_dsrna_candidates`

```python
@tool
def design_dsrna_candidates(
    gene_sequence: str,
    gene_name: str,
    length: int = 300,
    num_candidates: int = 3
) -> list[dict]:
    """Design dsRNA sequences targeting a gene.

    Args:
        gene_sequence: CDS nucleotide sequence
        gene_name: Gene identifier
        length: Target dsRNA length (200-500bp)
        num_candidates: Number of candidates to return

    Returns:
        List of {id, sequence, start, end, gc_content, score}
    """
```

**Scoring algorithm:**
```python
def score_window(seq, start, gene_length):
    score = 0
    gc = (seq.count('G') + seq.count('C')) / len(seq)

    # GC content 35-50%
    if 0.35 <= gc <= 0.50:
        score += 2
    elif 0.30 <= gc <= 0.55:
        score += 1

    # No poly-N runs ≥4
    if not re.search(r'([ATGC])\1{3,}', seq):
        score += 1

    # Avoid first 75bp (5' variable region)
    if start >= 75:
        score += 1

    # Avoid last 50bp (3' variable region)
    if start + len(seq) <= gene_length - 50:
        score += 1

    return score, gc
```

### 5. `run_offtarget_blast`

```python
@tool
def run_offtarget_blast(
    candidates: list[dict],
    blast_db_dir: str = "data/blast_db"
) -> list[dict]:
    """Screen dsRNA candidates against human and honeybee genomes.

    Args:
        candidates: List of {id, sequence, ...} from design step
        blast_db_dir: Path to BLAST databases

    Returns:
        List of {candidate_id, human_max_match, honeybee_max_match, safe}
    """
```

**Implementation:**
```python
def blast_sequence(seq, db_path):
    """Run blastn and return max contiguous match length."""
    # Write temp query file
    # Run: blastn -query temp.fa -db {db_path} -word_size 7 -outfmt 6
    # Parse output to find longest alignment
    # Return max match length
```

**Safety thresholds (EPA):**
- ✅ Safe: max match < 15bp
- ⚠️ Caution: 15-18bp match
- ❌ Reject: ≥19bp contiguous match

### 6. `score_efficiency`

```python
@tool
def score_efficiency(
    candidates: list[dict],
    blast_results: list[dict],
    gene_scores: dict[str, float]
) -> list[dict]:
    """Compute final efficacy and safety scores.

    Args:
        candidates: dsRNA candidates with sequence features
        blast_results: Off-target analysis results
        gene_scores: Essentiality scores per gene

    Returns:
        Candidates with efficacy_score, safety_score, combined_score
    """
```

**Scoring formula:**
```python
# Efficacy (0-1)
efficacy = (
    0.3 * gc_score +           # GC in optimal range
    0.2 * (1 if no_poly_n else 0) +
    0.2 * position_score +     # Good CDS position
    0.3 * gene_essentiality    # Target gene importance
)

# Safety (0-1)
if max_offtarget_match >= 19:
    safety = 0.0
elif max_offtarget_match >= 15:
    safety = 0.7
else:
    safety = 1.0

# Combined
combined = efficacy * safety
```

### 7. `generate_report`

```python
@tool
def generate_report(
    species: str,
    candidates: list[dict],
    output_dir: str
) -> str:
    """Generate markdown report with ranked candidates.

    Args:
        species: Target species name
        candidates: Scored candidates
        output_dir: Output directory path

    Returns:
        Path to generated report
    """
```

**Report structure:**
```markdown
# dsRNA Design Report: {species}

## Executive Summary
- Target: {species}
- Candidates screened: {n}
- Recommended: {top_candidate}

## Top Candidates

| Rank | ID | Target Gene | Efficacy | Safety | Combined |
|------|-------|-------------|----------|--------|----------|
| 1 | ... | vATPase | 0.85 | 1.0 | 0.85 |

## Candidate Details

### Candidate 1: {id}
- **Target gene:** {gene_name} ({function})
- **Sequence:** (300bp)
- **GC content:** 42%
- **Off-target:** Human 12bp, Honeybee 10bp ✅

## Off-Target Analysis

| Candidate | Human | Honeybee | Status |
|-----------|-------|----------|--------|
| ... | 12bp | 10bp | ✅ Safe |

## Recommendations
{agent_generated_recommendations}
```

## Essential Genes Data

Curated list in `data/essential_genes.json`:

```json
{
  "genes": [
    {
      "name": "vATPase subunit A",
      "aliases": ["vha68-2", "ATP6V1A", "V-ATPase A"],
      "function": "Vacuolar proton pump, essential for pH homeostasis",
      "drosophila_id": "FBgn0005671",
      "essential_in": ["D. melanogaster", "T. castaneum", "L. decemlineata"],
      "references": ["PMID:27234456", "PMID:25678123"]
    },
    {
      "name": "Chitin synthase",
      "aliases": ["ChS", "CHS1", "chs-1"],
      "function": "Synthesizes chitin for cuticle, essential for molting",
      "drosophila_id": "FBgn0000355",
      "essential_in": ["D. melanogaster", "S. frugiperda", "M. persicae"],
      "references": ["PMID:23456789"]
    }
  ]
}
```

**Sources to curate from:**
- DEG (Database of Essential Genes): essentialgene.org
- FlyBase lethal genes: flybase.org
- Published RNAi screens in pest insects

## Agent Configuration

### dsrna_agent/agent.py

```python
from deepagents import create_deep_agent
from langchain_core.tools import tool
from .tools import (
    fetch_genome,
    literature_search,
    identify_essential_genes,
    design_dsrna_candidates,
    run_offtarget_blast,
    score_efficiency,
    generate_report,
)

SYSTEM_PROMPT = """You are an RNAi biopesticide design assistant. Your goal is to
design dsRNA molecules that effectively kill target pest species while ensuring
safety for humans and beneficial insects.

## Workflow
Follow these steps in order:
1. fetch_genome: Download CDS sequences for the target species from NCBI
2. literature_search: Find published RNAi targets for this species
3. identify_essential_genes: Rank genes by essentiality using orthology + literature
4. design_dsrna_candidates: For the top 5 genes, design 3 dsRNA candidates each
5. run_offtarget_blast: Screen all 15 candidates against human and honeybee
6. score_efficiency: Compute final rankings
7. generate_report: Write comprehensive report to output directory

## Safety Rules
- ALWAYS screen candidates against human and honeybee genomes
- REJECT any candidate with ≥19bp contiguous match to non-targets
- Prefer genes with low conservation in non-target species
- Include clear safety assessment in the final report

## Output
All artifacts are written to output/{species_slug}/:
- genome.fasta: Downloaded CDS sequences
- candidates.json: All candidates with scores
- report.md: Final report with recommendations
"""

def create_dsrna_agent():
    return create_deep_agent(
        tools=[
            fetch_genome,
            literature_search,
            identify_essential_genes,
            design_dsrna_candidates,
            run_offtarget_blast,
            score_efficiency,
            generate_report,
        ],
        system_prompt=SYSTEM_PROMPT,
        model="claude-sonnet-4-5-20250929",
    )
```

## Dependencies

```toml
[project]
name = "dsrna-designer"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "deepagents-cli>=0.0.12",
    "python-dotenv>=1.2.1",
    "httpx>=0.27.0",
    "biopython>=1.84",
]
```

## Implementation Steps

1. **Setup project structure**
   - Create directories: `dsrna_agent/`, `data/`, `output/`
   - Update pyproject.toml with dependencies

2. **Curate essential genes data**
   - Research DEG, FlyBase, published RNAi screens
   - Create `data/essential_genes.json` with ~50 validated genes

3. **Setup BLAST databases**
   - Create `setup_blast_db.sh` script
   - Download human and honeybee RefSeq CDS
   - Build BLAST databases

4. **Implement tools** (in order)
   - `fetch_genome` - NCBI E-utilities + FTP
   - `literature_search` - PubMed API
   - `identify_essential_genes` - BLAST + scoring
   - `design_dsrna_candidates` - Sliding window
   - `run_offtarget_blast` - Local BLAST+
   - `score_efficiency` - Rule-based scoring
   - `generate_report` - Markdown generation

5. **Wire up agent**
   - Create `dsrna_agent/agent.py`
   - Register with deepagents CLI

6. **Test end-to-end**
   - Run with Drosophila suzukii

## Verification

```bash
# Setup BLAST databases first
./setup_blast_db.sh

# Run the agent
deepagents run dsrna_agent "Design dsRNA candidates for Drosophila suzukii (spotted wing drosophila)"
```

**Expected outputs in `output/drosophila_suzukii/`:**
- `genome.fasta` - ~15,000 CDS sequences
- `candidates.json` - 15 candidates (5 genes × 3 each)
- `report.md` - Ranked recommendations

**Success criteria:**
- Report contains 3-5 ranked candidates with sequences
- All recommended candidates have <15bp off-target matches
- Clear recommendation for which to test first
