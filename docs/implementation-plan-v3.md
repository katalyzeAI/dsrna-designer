# dsRNA Designer - Implementation Plan v3 (Skills-Based + Interactive)

## Executive Summary

This plan implements a dsRNA design agent using **deepagents native skills** with **mandatory user checkpoints** at each workflow step.

**Key Changes from v1/v2:**
- ✅ **Skills-based**: 7 SKILL.md files instead of custom @tool functions
- ✅ **Interactive**: Agent completes ONE step at a time, waits for approval
- ✅ **Visual**: Every step generates informative plots and visualizations
- ✅ **Transparent**: User can review intermediary results before proceeding
- ✅ **Token efficient**: Progressive disclosure (only frontmatter loads initially)

**Workflow Pattern:**
```
Execute Skill → Generate Plots → Present Results → WAIT FOR USER → Next Skill
```

**User Experience:**
```
User: "Design dsRNA for Drosophila suzukii"

Agent: [Executes fetch-genome]
       "Downloaded 15,842 CDS sequences (mean GC: 42.3%)
        [Shows GC distribution plot]
        Ready to proceed to literature-search? (yes/no)"

User: "yes"

Agent: [Executes literature-search]
       "Found 12 papers mentioning 8 genes
        [Shows gene frequency bar chart]
        Ready to proceed to identify-genes? (yes/no)"
        
... continues for all 7 steps
```

## Overview

Build a dsRNA design agent using **deepagents native skills** instead of custom tools. Skills provide token-efficient progressive disclosure and allow the agent to use built-in tools (shell, read_file, fetch_url, etc.) to accomplish tasks.

**Architecture:**
- Native deepagents CLI with built-in tools
- Project-level skills at `.deepagents/skills/`
- Skills contain markdown instructions + helper scripts
- Agent orchestrates workflow by reading skills dynamically
- **Interactive workflow**: Agent executes ONE skill at a time, shows results with visualizations, waits for user approval before proceeding

**Key Workflow Principle:**
The agent MUST complete each skill fully, generate informative plots/visualizations, present results to the user, and wait for explicit approval before moving to the next skill. This ensures quality control at every step and allows users to intervene if results are unsatisfactory.

## Why Skills Over Custom Tools

| Aspect | Custom Tools (@tool) | Skills (SKILL.md) |
|--------|---------------------|-------------------|
| Token usage | All schemas loaded upfront | Progressive disclosure (frontmatter only) |
| Flexibility | Fixed implementation | Agent interprets instructions |
| Sharing | Requires code package | Copy folder, works anywhere |
| Extension | Modify Python code | Agent can create new skills |
| Debugging | Stack traces, type safety | Review agent's shell commands |
| Determinism | High | Medium (agent interprets) |

**Decision:** Use skills for this project because:
1. Token efficiency matters with 7 distinct workflows
2. Workflows may need adjustments during testing
3. Skills are easier to share/document for bio-researchers
4. Built-in tools (shell, fetch_url) handle all operations

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    deepagents CLI Agent                         │
│              (Claude with system prompt)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Built-in     │    │  Skills       │    │  Data Files   │
│    Tools      │    │  (.deepagents │    │               │
│               │    │   /skills/)   │    │ • essential_  │
│ • shell       │    │               │    │   genes.json  │
│ • read_file   │    │ 1. fetch-     │    │ • blast_db/   │
│ • write_file  │    │    genome     │    │               │
│ • fetch_url   │    │ 2. literature-│    │               │
│ • glob        │    │    search     │    │               │
│ • grep        │    │ 3. identify-  │    │               │
│ • task        │    │    genes      │    │               │
│               │    │ 4. design-    │    │               │
│               │    │    dsrna      │    │               │
│               │    │ 5. blast-     │    │               │
│               │    │    screen     │    │               │
│               │    │ 6. score-rank │    │               │
│               │    │ 7. generate-  │    │               │
│               │    │    report     │    │               │
└───────────────┘    └───────────────┘    └───────────────┘
```

## Interactive Workflow with Checkpoints

```
User: "Design dsRNA for Drosophila suzukii"
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│ Step 1: fetch-genome                                     │
│ • Download CDS from NCBI                                 │
│ • Generate GC distribution plot                          │
│ • Output: genome.fasta + plots                           │
└──────────────────────────────────────────────────────────┘
  │
  │ Agent: "Downloaded 15,842 sequences. [Shows GC plot]
  │         Ready to proceed? (yes/no)"
  ▼
┌─────────┐
│ User    │ ← USER CHECKPOINT: Review results, approve
│ Approves│
└─────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│ Step 2: literature-search                                │
│ • Query PubMed for RNAi papers                           │
│ • Generate gene frequency plot                           │
│ • Output: literature_search.json + plots                 │
└──────────────────────────────────────────────────────────┘
  │
  │ Agent: "Found 12 papers mentioning 8 genes. [Shows plot]
  │         Ready to proceed? (yes/no)"
  ▼
┌─────────┐
│ User    │ ← USER CHECKPOINT: Review papers, approve
│ Approves│
└─────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│ Step 3: identify-genes                                   │
│ • Match essential genes to genome                        │
│ • Generate ranking plots                                 │
│ • Output: essential_genes.json + plots                   │
└──────────────────────────────────────────────────────────┘
  │
  │ Agent: "Identified 18 essential genes. [Shows ranking]
  │         Ready to design dsRNA? (yes/no)"
  ▼
┌─────────┐
│ User    │ ← USER CHECKPOINT: Review genes, approve
│ Approves│
└─────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│ Step 4: design-dsrna                                     │
│ • Design 3 candidates × 5 genes = 15 total              │
│ • Generate candidate location plots                      │
│ • Output: candidates.json + plots                        │
└──────────────────────────────────────────────────────────┘
  │
  │ Agent: "Designed 15 candidates. [Shows locations + GC]
  │         Ready to screen? (yes/no)"
  ▼
┌─────────┐
│ User    │ ← USER CHECKPOINT: Review candidates, approve
│ Approves│
└─────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│ Step 5: blast-screen                                     │
│ • BLAST vs human + honeybee                              │
│ • Generate safety heatmap                                │
│ • Output: blast_results.json + plots                     │
└──────────────────────────────────────────────────────────┘
  │
  │ Agent: "Screened 15 candidates: 12 safe, 3 caution.
  │         [Shows heatmap] Ready to rank? (yes/no)"
  ▼
┌─────────┐
│ User    │ ← USER CHECKPOINT: Review safety, approve
│ Approves│
└─────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│ Step 6: score-rank                                       │
│ • Calculate efficacy × safety scores                     │
│ • Generate ranking visualizations                        │
│ • Output: ranked_candidates.json + plots                 │
└──────────────────────────────────────────────────────────┘
  │
  │ Agent: "Top candidate: vATPase_2 (score 0.85).
  │         [Shows scatter plot] Generate report? (yes/no)"
  ▼
┌─────────┐
│ User    │ ← USER CHECKPOINT: Review rankings, approve
│ Approves│
└─────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│ Step 7: generate-report                                  │
│ • Create markdown report                                 │
│ • Generate summary dashboard                             │
│ • Output: report.md + dashboard                          │
└──────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│ WORKFLOW COMPLETE                                        │
│ • All files in output/drosophila_suzukii/                │
│ • All plots in output/drosophila_suzukii/figures/        │
│ • Report ready for review                                │
└──────────────────────────────────────────────────────────┘
```

## File Structure

```
dsrna-designer/
├── .deepagents/
│   ├── agent.md              # Project-specific agent config
│   └── skills/               # Project skills (version controlled)
│       ├── fetch-genome/
│       │   ├── SKILL.md
│       │   └── scripts/
│       │       └── ncbi_download.py
│       ├── literature-search/
│       │   ├── SKILL.md
│       │   └── references/
│       │       └── gene_patterns.txt
│       ├── identify-genes/
│       │   ├── SKILL.md
│       │   └── scripts/
│       │       └── match_essential.py
│       ├── design-dsrna/
│       │   ├── SKILL.md
│       │   └── scripts/
│       │       └── sliding_window.py
│       ├── blast-screen/
│       │   ├── SKILL.md
│       │   ├── scripts/
│       │   │   └── run_blast.py
│       │   └── references/
│       │       └── safety_thresholds.md
│       ├── score-rank/
│       │   ├── SKILL.md
│       │   └── scripts/
│       │       └── calculate_scores.py
│       └── generate-report/
│           ├── SKILL.md
│           └── references/
│               └── report_template.md
├── data/
│   ├── essential_genes.json
│   └── blast_db/
│       ├── human_cds.*
│       └── honeybee_cds.*
├── output/                   # Generated by agent
├── pyproject.toml
├── setup_blast_db.sh
└── README.md
```

## Implementation Steps

### Phase 1: Setup Project Structure

**Task 1.1: Create Skills Directory**
```bash
mkdir -p .deepagents/skills
mkdir -p .deepagents/skills/{fetch-genome,literature-search,identify-genes,design-dsrna,blast-screen,score-rank,generate-report}
```

**Task 1.2: Create Project Agent Config**

File: `.deepagents/agent.md`

Content:
```
# dsRNA Designer Agent

You are an RNAi biopesticide design assistant specializing in creating safe, 
effective dsRNA molecules for pest control.

## Core Workflow - ONE STEP AT A TIME

**CRITICAL:** Execute ONLY ONE skill at a time, then STOP and present results.

When asked to design dsRNA for a species, follow these steps:
1. **fetch-genome** skill → Show genome stats + GC distribution plot → WAIT FOR APPROVAL
2. **literature-search** skill → Show paper count + gene frequency plot → WAIT FOR APPROVAL
3. **identify-genes** skill → Show gene ranking plot + evidence breakdown → WAIT FOR APPROVAL
4. **design-dsrna** skill → Show candidate locations + GC content distribution → WAIT FOR APPROVAL
5. **blast-screen** skill → Show safety heatmap + match distribution → WAIT FOR APPROVAL
6. **score-rank** skill → Show score breakdown + ranked candidates plot → WAIT FOR APPROVAL
7. **generate-report** skill → Show report summary → DONE

## Interaction Protocol

After completing each skill:

1. **Execute the skill** - Run all commands for that skill only
2. **Generate visualizations** - Create informative plots using matplotlib/seaborn
3. **Summarize results** - Present key metrics and findings
4. **Save checkpoint** - Write intermediate results to files
5. **Present to user** - Show summary + visualizations
6. **STOP and WAIT** - Do NOT proceed until user approves

**Example interaction:**

Agent: "I've completed fetch-genome for Drosophila suzukii.

Results:
- Downloaded 15,842 CDS sequences
- Total length: 23.4 Mb
- Average CDS length: 1,476 bp
- GC content: 42.3% (see plot below)

[Shows GC distribution histogram]

Ready to proceed to literature-search? (yes/no)"

User: "yes"

Agent: [Proceeds to literature-search skill]


## Visualization Requirements

Each skill MUST generate at least one informative plot:

1. **fetch-genome**: GC content distribution histogram
2. **literature-search**: Bar chart of gene mentions across papers
3. **identify-genes**: Horizontal bar chart of top genes with score breakdown
4. **design-dsrna**: Genomic location plot showing candidate positions per gene
5. **blast-screen**: Heatmap of off-target matches (candidates vs organisms)
6. **score-rank**: Multi-panel plot showing efficacy vs safety scatter plot
7. **generate-report**: Summary dashboard with key metrics

Save all plots to `output/{species_slug}/figures/` with descriptive names.

## Safety Rules
- ALWAYS screen against human and honeybee genomes
- REJECT candidates with ≥19bp contiguous matches (EPA threshold)
- Flag 15-18bp matches as "caution"

## Output Structure
All files go to: output/{species_slug}/
All plots go to: output/{species_slug}/figures/
```

### Phase 2: Write Skills (7 Skills)

Each skill follows this template structure:

- YAML frontmatter with `name` and `description`
- "When to Use This Skill" section
- "Instructions" with step-by-step workflow
- "Available Tools" listing built-in tools used
- "Helper Scripts" if applicable
- "Expected Output" describing files created

---

### Skill 1: fetch-genome

**File:** `.deepagents/skills/fetch-genome/SKILL.md`

**Content:**
```
---
name: fetch-genome
description: Download CDS sequences from NCBI RefSeq for a target species
---

# Fetch Genome Skill

## When to Use This Skill
Use at the start of dsRNA design workflow when you need coding sequences (CDS) 
for a pest species from NCBI.

## Instructions

### Step 1: Create Output Directory

    mkdir -p output/{species_slug}

Use lowercase with underscores (e.g., "drosophila_suzukii")

### Step 2: Resolve Species to TaxID
Use `fetch_url` to query NCBI Taxonomy:

    https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=taxonomy&term={species}&retmode=json

Parse JSON response: `esearchresult.idlist[0]` is the TaxID

### Step 3: Find RefSeq Assembly
Use `fetch_url`:

    https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=assembly&term=txid{TAXID}[Organism:exp]+AND+latest_refseq[filter]&retmode=json

Get assembly ID from `esearchresult.idlist[0]`

### Step 4: Get FTP Path
Use `fetch_url`:

    https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=assembly&id={ASSEMBLY_ID}&retmode=json

Extract FTP path from `result[assembly_id].ftppath_refseq`

### Step 5: Download CDS FASTA
Use `shell` to download (faster for large files):

    FTP_PATH="https://ftp.ncbi.nlm.nih.gov/..."  # from step 4
    ASSEMBLY_NAME=$(basename $FTP_PATH)
    curl -L -o output/{species_slug}/genome.fasta.gz \
      "${FTP_PATH}/${ASSEMBLY_NAME}_cds_from_genomic.fna.gz"
    gunzip output/{species_slug}/genome.fasta.gz

If `_cds_from_genomic.fna.gz` returns 404, try `_rna.fna.gz` instead.

### Step 6: Verify Download
Use `shell`:

    grep -c "^>" output/{species_slug}/genome.fasta

Should show thousands of sequences (typically 10,000-20,000 for insects)

### Step 7: Generate Visualization
Create `output/{species_slug}/figures/` directory and generate GC content analysis:

    python .deepagents/skills/fetch-genome/scripts/plot_genome_stats.py \
      --genome output/{species_slug}/genome.fasta \
      --output-dir output/{species_slug}/figures/

This creates:
- `genome_gc_distribution.png` - Histogram of GC content across all CDS
- `genome_length_distribution.png` - CDS length distribution
- `genome_stats.json` - Summary statistics

### Step 8: Present Results and STOP

Present to user:
1. Summary statistics (gene count, total length, avg GC)
2. Show the generated plots
3. Ask: "Ready to proceed to literature-search? (yes/no)"

**DO NOT PROCEED** until user confirms.

## Expected Output
- `output/{species_slug}/genome.fasta` - Downloaded CDS sequences
- `output/{species_slug}/genome_metadata.json` - TaxID, assembly ID, stats
- `output/{species_slug}/figures/genome_gc_distribution.png`
- `output/{species_slug}/figures/genome_length_distribution.png`
- `output/{species_slug}/figures/genome_stats.json`

## Available Tools
- `fetch_url` - Query NCBI APIs
- `shell` - Run curl/gunzip commands and Python scripts
- `write_file` - Save metadata
```

---

### Skill 2: literature-search

**File:** `.deepagents/skills/literature-search/SKILL.md`

**Content:**
```
---
name: literature-search
description: Search PubMed for published RNAi targets in a pest species
---

# Literature Search Skill

## When to Use This Skill
Use after fetching genome to find genes that have been successfully targeted 
with RNAi/dsRNA in published research.

## Instructions

### Step 1: Search PubMed
Use `fetch_url` to query PubMed E-utilities:

    https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term="{species}"[Title/Abstract]+AND+(RNAi+OR+dsRNA+OR+"RNA+interference"+OR+"gene+silencing")&retmax=20&retmode=json

Get PMIDs from `esearchresult.idlist`

### Step 2: Fetch Abstracts
Use `fetch_url`:

    https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={PMID_LIST}&rettype=abstract&retmode=xml

### Step 3: Extract Gene Names
Parse XML for titles and abstracts. Look for these gene patterns:
- V-ATPase, vATPase, vha (vacuolar ATPase)
- Chitin synthase, ChS, CHS
- Acetylcholinesterase, AChE, Ace
- Tubulin, actin
- Ribosomal protein, RpS, RpL
- Cytochrome P450, CYP
- Ecdysone receptor, EcR
- Trehalase, laccase, aquaporin

Use `shell` with Python or grep to extract matches.

### Step 4: Save Results
Use `write_file` to save to `output/{species_slug}/literature_search.json`:
```json
[
  {
    "pmid": "12345678",
    "title": "...",
    "gene_names": ["vATPase", "chitin synthase"],
    "abstract_snippet": "..."
  }
]
```

## Helper Script
If XML parsing is complex, use the bundled script:
```bash
python .deepagents/skills/literature-search/scripts/parse_pubmed.py \
  --xml-file /tmp/pubmed.xml \
  --output output/{species_slug}/literature_search.json
```

### Step 5: Generate Visualization
Create plots showing literature findings:

```bash
python .deepagents/skills/literature-search/scripts/plot_literature.py \
  --literature output/{species_slug}/literature_search.json \
  --output-dir output/{species_slug}/figures/
```

This creates:
- `literature_gene_frequency.png` - Bar chart of most-mentioned genes
- `literature_timeline.png` - Papers per year (if dates available)
- `literature_summary.txt` - Key findings summary

### Step 6: Present Results and STOP

Present to user:
1. Number of papers found
2. Top 5 most-mentioned genes with citation counts
3. Show the gene frequency plot
4. Ask: "Ready to proceed to identify-genes? (yes/no)"

**DO NOT PROCEED** until user confirms.

## Expected Output
- `output/{species_slug}/literature_search.json`
- `output/{species_slug}/figures/literature_gene_frequency.png`
- `output/{species_slug}/figures/literature_summary.txt`

## Available Tools
- `fetch_url` - Query PubMed APIs
- `shell` - Run Python/grep for parsing and plotting
- `write_file` - Save results
```

**Helper Script:** `.deepagents/skills/literature-search/scripts/parse_pubmed.py`
```python
#!/usr/bin/env python3
"""Parse PubMed XML and extract gene names."""
import xml.etree.ElementTree as ET
import json
import re
import argparse

GENE_PATTERNS = [
    r'\b(v-?ATPase|vha\d+|ATP6V\w+)\b',
    r'\b(chitin\s*synthase|ChS|CHS\d?)\b',
    r'\b(acetylcholinesterase|AChE|Ace)\b',
    r'\b(tubulin|TUB\w*)\b',
    r'\b(actin|ACT\d?)\b',
]

def parse_pubmed_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    gene_regex = re.compile('|'.join(GENE_PATTERNS), re.IGNORECASE)
    results = []
    
    for article in root.findall('.//PubmedArticle'):
        pmid_elem = article.find('.//PMID')
        title_elem = article.find('.//ArticleTitle')
        abstract_elem = article.find('.//AbstractText')
        
        pmid = pmid_elem.text if pmid_elem is not None else ''
        title = title_elem.text if title_elem is not None else ''
        abstract = abstract_elem.text if abstract_elem is not None else ''
        
        text = f"{title} {abstract}"
        gene_matches = gene_regex.findall(text)
        gene_names = list(set(match for match in gene_matches if match))
        
        results.append({
            'pmid': pmid,
            'title': title,
            'gene_names': gene_names,
            'abstract_snippet': abstract[:500] + '...' if len(abstract) > 500 else abstract
        })
    
    return results

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--xml-file', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    
    results = parse_pubmed_xml(args.xml_file)
    
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Found {len(results)} papers with gene mentions")
```

---

### Skill 3: identify-genes

**File:** `.deepagents/skills/identify-genes/SKILL.md`

```
---
name: identify-genes
description: Match essential genes in target genome using orthology and literature
---

# Identify Essential Genes Skill

## When to Use This Skill
Use after genome fetch and literature search to identify essential genes in the 
target species that are good dsRNA candidates.

## Instructions

### Step 1: Load Essential Genes Database
Use `read_file` to load `data/essential_genes.json`

### Step 2: Parse Target Genome
Use the bundled Python script:

    python .deepagents/skills/identify-genes/scripts/match_essential.py \
      --genome output/{species_slug}/genome.fasta \
      --essential-db data/essential_genes.json \
      --literature output/{species_slug}/literature_search.json \
      --output output/{species_slug}/essential_genes.json

The script:
1. Parses FASTA annotations
2. Matches gene names/aliases against annotations
3. Scores by orthology + literature support
4. Returns top 20 with sequences

### Step 3: Verify Results
Use `shell`:

    jq 'length' output/{species_slug}/essential_genes.json

Should show ~20 genes (or fewer if genome poorly annotated)

### Step 4: Generate Visualization
Create plots showing gene rankings:

    python .deepagents/skills/identify-genes/scripts/plot_genes.py \
      --genes output/{species_slug}/essential_genes.json \
      --output-dir output/{species_slug}/figures/

This creates:
- `gene_ranking.png` - Horizontal bar chart of top 10 genes with scores
- `gene_evidence_breakdown.png` - Stacked bar showing evidence sources (orthology/literature)
- `gene_length_distribution.png` - CDS lengths for identified genes

### Step 5: Present Results and STOP

Present to user:
1. Number of essential genes identified
2. Top 5 genes with scores and evidence
3. Show the gene ranking plot
4. Note which genes have literature support
5. Ask: "Ready to proceed to design-dsrna for top 5 genes? (yes/no)"

**DO NOT PROCEED** until user confirms.

## Scoring Logic
- Base score: 0.5 (ortholog match)
- +0.3 if mentioned in literature
- +0.05 per species where it's essential (max +0.2)

## Expected Output
- `output/{species_slug}/essential_genes.json`
- `output/{species_slug}/figures/gene_ranking.png`
- `output/{species_slug}/figures/gene_evidence_breakdown.png`
- `output/{species_slug}/figures/gene_length_distribution.png`

## Available Tools
- `read_file` - Load databases
- `shell` - Run Python script and plotting
- `write_file` - Save results
```

**Helper Script:** `.deepagents/skills/identify-genes/scripts/match_essential.py`
```python
#!/usr/bin/env python3
"""Match essential genes against target genome."""
from Bio import SeqIO
import json
import argparse

def match_essential_genes(genome_path, essential_db_path, literature_path, output_path):
    # Load essential genes
    with open(essential_db_path) as f:
        essential_db = json.load(f)
    
    # Load literature gene names
    literature_genes = []
    if literature_path:
        with open(literature_path) as f:
            lit_data = json.load(f)
            for paper in lit_data:
                literature_genes.extend(paper.get('gene_names', []))
    literature_genes = [g.lower() for g in literature_genes]
    
    # Parse genome
    genome_sequences = {}
    for record in SeqIO.parse(genome_path, 'fasta'):
        genome_sequences[record.id] = {
            'id': record.id,
            'description': record.description,
            'sequence': str(record.seq),
            'length': len(record.seq)
        }
    
    # Match genes
    candidates = []
    for gene in essential_db.get('genes', []):
        gene_name = gene['name'].lower()
        aliases = [a.lower() for a in gene.get('aliases', [])]
        all_names = [gene_name] + aliases
        
        for seq_id, seq_data in genome_sequences.items():
            desc_lower = seq_data['description'].lower()
            
            matched = False
            for name in all_names:
                if name in desc_lower or name.replace('-', '') in desc_lower:
                    matched = True
                    break
            
            if matched:
                # Calculate score
                score = 0.5  # Base ortholog match
                
                # Literature support
                if any(name in literature_genes for name in all_names):
                    score += 0.3
                
                # Essential in multiple species
                essential_count = len(gene.get('essential_in', []))
                score += min(0.2, essential_count * 0.05)
                
                candidates.append({
                    'gene_id': seq_id,
                    'gene_name': gene['name'],
                    'function': gene['function'],
                    'score': round(score, 2),
                    'evidence': {
                        'ortholog_match': True,
                        'literature_support': any(name in literature_genes for name in all_names),
                        'essential_in_species': gene.get('essential_in', []),
                        'references': gene.get('references', [])
                    },
                    'sequence': seq_data['sequence'],
                    'sequence_length': seq_data['length']
                })
    
    # Sort and take top 20
    candidates.sort(key=lambda x: x['score'], reverse=True)
    top_candidates = candidates[:20]
    
    with open(output_path, 'w') as f:
        json.dump(top_candidates, f, indent=2)
    
    print(f"Found {len(top_candidates)} essential gene matches (from {len(candidates)} total)")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--genome', required=True)
    parser.add_argument('--essential-db', required=True)
    parser.add_argument('--literature', required=False)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    
    match_essential_genes(args.genome, args.essential_db, args.literature, args.output)
```

---

### Skill 4: design-dsrna

**File:** `.deepagents/skills/design-dsrna/SKILL.md`

```
---
name: design-dsrna
description: Design dsRNA candidates using sliding window algorithm
---

# Design dsRNA Candidates Skill

## When to Use This Skill
Use after identifying essential genes to design 3 dsRNA candidates per gene 
for the top 5 genes (15 total candidates).

## Instructions

### Step 1: Select Top 5 Genes
Use `shell` with jq:

    jq '.[0:5]' output/{species_slug}/essential_genes.json > /tmp/top5_genes.json

### Step 2: Design Candidates for Each Gene
For each of the 5 genes, run the design script:

    python .deepagents/skills/design-dsrna/scripts/sliding_window.py \
      --gene-file /tmp/gene_N.json \
      --length 300 \
      --num-candidates 3 \
      --output /tmp/candidates_N.json

### Step 3: Merge All Candidates
Use `shell`:

    jq -s 'add' /tmp/candidates_*.json > output/{species_slug}/candidates.json

Should result in 15 candidates total (5 genes × 3 each)

### Step 4: Generate Visualization
Create plots showing candidate design quality:

    python .deepagents/skills/design-dsrna/scripts/plot_candidates.py \
      --candidates output/{species_slug}/candidates.json \
      --genes output/{species_slug}/essential_genes.json \
      --output-dir output/{species_slug}/figures/

This creates:
- `candidate_locations.png` - Genomic positions of candidates along each gene
- `candidate_gc_distribution.png` - Histogram of GC content across all candidates
- `candidate_scores_heatmap.png` - Heatmap showing design score components
- `candidate_summary_table.png` - Table visualization of all 15 candidates

### Step 5: Present Results and STOP

Present to user:
1. Total candidates designed (should be 15)
2. GC content range across candidates
3. Show candidate locations plot (where on genes they are)
4. Show GC distribution plot
5. List candidates grouped by gene
6. Ask: "Ready to proceed to blast-screen? (yes/no)"

**DO NOT PROCEED** until user confirms.

## Design Scoring Criteria
Each window is scored 0-5 points:
- **GC content 35-50%**: +2 points
- **GC content 30-55%**: +1 point
- **No poly-N runs (4+ same base)**: +1 point
- **Not in first 75bp of CDS**: +1 point
- **Not in last 50bp of CDS**: +1 point

Non-overlapping windows with highest scores are selected.

## Expected Output
- `output/{species_slug}/candidates.json`
- `output/{species_slug}/figures/candidate_locations.png`
- `output/{species_slug}/figures/candidate_gc_distribution.png`
- `output/{species_slug}/figures/candidate_scores_heatmap.png`

## Available Tools
- `shell` - Run Python script, jq, and plotting
- `read_file` / `write_file` - Handle JSON
```

**Helper Script:** `.deepagents/skills/design-dsrna/scripts/sliding_window.py`
```python
#!/usr/bin/env python3
"""Design dsRNA candidates using sliding window."""
import json
import re
import argparse

def design_candidates(sequence, gene_name, gene_id, length=300, num_candidates=3):
    seq = sequence.upper()
    gene_length = len(seq)
    
    if gene_length < length:
        return []
    
    windows = []
    step = 50
    
    for start in range(0, gene_length - length + 1, step):
        end = start + length
        window_seq = seq[start:end]
        
        # Calculate GC
        gc = (window_seq.count('G') + window_seq.count('C')) / length
        
        # Score
        score = 0
        if 0.35 <= gc <= 0.50:
            score += 2
        elif 0.30 <= gc <= 0.55:
            score += 1
        
        has_poly_n = bool(re.search(r'([ATGC])\1{3,}', window_seq))
        if not has_poly_n:
            score += 1
        
        if start >= 75:
            score += 1
        if end <= gene_length - 50:
            score += 1
        
        windows.append({
            'start': start,
            'end': end,
            'sequence': window_seq,
            'gc_content': round(gc, 3),
            'has_poly_n': has_poly_n,
            'score': score
        })
    
    # Select top non-overlapping
    windows.sort(key=lambda x: x['score'], reverse=True)
    selected = []
    used_positions = set()
    
    for window in windows:
        if len(selected) >= num_candidates:
            break
        
        window_positions = set(range(window['start'], window['end']))
        if not window_positions.intersection(used_positions):
            candidate_id = f"{gene_name}_{len(selected) + 1}"
            selected.append({
                'id': candidate_id,
                'gene_name': gene_name,
                'gene_id': gene_id,
                'sequence': window['sequence'],
                'start': window['start'],
                'end': window['end'],
                'length': length,
                'gc_content': window['gc_content'],
                'has_poly_n': window['has_poly_n'],
                'design_score': window['score']
            })
            used_positions.update(window_positions)
    
    return selected

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--gene-file', required=True)
    parser.add_argument('--length', type=int, default=300)
    parser.add_argument('--num-candidates', type=int, default=3)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    
    with open(args.gene_file) as f:
        gene = json.load(f)
    
    candidates = design_candidates(
        gene['sequence'],
        gene['gene_name'],
        gene['gene_id'],
        args.length,
        args.num_candidates
    )
    
    with open(args.output, 'w') as f:
        json.dump(candidates, f, indent=2)
    
    print(f"Designed {len(candidates)} candidates for {gene['gene_name']}")
```

---

### Skill 5: blast-screen

**File:** `.deepagents/skills/blast-screen/SKILL.md`

```
---
name: blast-screen
description: Screen dsRNA candidates for off-target matches in human and honeybee
---

# BLAST Off-Target Screening Skill

## When to Use This Skill
Use after designing candidates to screen all 15 dsRNA sequences against human 
and honeybee genomes for safety assessment.

## Prerequisites
BLAST+ must be installed and databases must exist:
- `data/blast_db/human_cds.*`
- `data/blast_db/honeybee_cds.*`

Check with:

    blastn -version
    ls data/blast_db/*.n* 

If missing, run `./setup_blast_db.sh` first.

## Instructions

### Step 1: Run BLAST Screening Script

    python .deepagents/skills/blast-screen/scripts/run_blast.py \
      --candidates output/{species_slug}/candidates.json \
      --blast-db-dir data/blast_db \
      --output output/{species_slug}/blast_results.json

The script:
1. Writes each candidate to temp FASTA
2. Runs blastn against human_cds and honeybee_cds
3. Parses output for max alignment length
4. Applies EPA safety thresholds

### Step 2: Verify Results

    jq '[.results[] | select(.safety_status == "reject")] | length' \
      output/{species_slug}/blast_results.json

### Step 3: Generate Visualization
Create safety analysis plots:

    python .deepagents/skills/blast-screen/scripts/plot_safety.py \
      --blast-results output/{species_slug}/blast_results.json \
      --candidates output/{species_slug}/candidates.json \
      --output-dir output/{species_slug}/figures/

This creates:
- `safety_heatmap.png` - Heatmap showing human/honeybee matches for each candidate
- `safety_distribution.png` - Histogram of match lengths
- `safety_by_gene.png` - Grouped bar chart of safety status per target gene
- `safety_summary_table.png` - Visual table of all candidates with color-coded safety

### Step 4: Present Results and STOP

Present to user:
1. Total candidates screened (15)
2. Safety breakdown:
   - Safe (<15bp): X candidates
   - Caution (15-18bp): Y candidates
   - Rejected (≥19bp): Z candidates
3. Show safety heatmap
4. Highlight any rejected candidates
5. Ask: "Ready to proceed to score-rank? (yes/no)"

**DO NOT PROCEED** until user confirms.

**Important:** If >5 candidates are rejected, warn user that top-5 ranking may include marginal candidates.

## Safety Thresholds (EPA Guidelines)
- **<15bp match**: ✅ Safe
- **15-18bp match**: ⚠️ Caution (acceptable but flagged)
- **≥19bp match**: ❌ Reject (high off-target risk)

## Expected Output
- `output/{species_slug}/blast_results.json`
- `output/{species_slug}/figures/safety_heatmap.png`
- `output/{species_slug}/figures/safety_distribution.png`
- `output/{species_slug}/figures/safety_by_gene.png`

## Available Tools
- `shell` - Check BLAST installation, run script and plotting
- `read_file` / `write_file` - Handle JSON
```

**Helper Script:** `.deepagents/skills/blast-screen/scripts/run_blast.py`
```python
#!/usr/bin/env python3
"""Screen dsRNA candidates with BLAST."""
import subprocess
import json
import tempfile
import os
import argparse
from pathlib import Path

def run_blast_query(query_file, db_path):
    """Run BLAST and return max alignment length."""
    try:
        result = subprocess.run([
            'blastn',
            '-query', query_file,
            '-db', db_path,
            '-word_size', '7',
            '-outfmt', '6 qseqid sseqid length',
            '-max_target_seqs', '100',
            '-evalue', '10'
        ], capture_output=True, text=True, timeout=60)
        
        if not result.stdout.strip():
            return 0
        
        max_length = 0
        for line in result.stdout.strip().split('\n'):
            parts = line.split('\t')
            if len(parts) >= 3:
                length = int(parts[2])
                max_length = max(max_length, length)
        
        return max_length
    except subprocess.TimeoutExpired:
        return -1
    except Exception:
        return 0

def blast_screen_candidates(candidates_file, blast_db_dir, output_file):
    with open(candidates_file) as f:
        candidates = json.load(f)
    
    blast_db_path = Path(blast_db_dir)
    human_db = blast_db_path / 'human_cds'
    honeybee_db = blast_db_path / 'honeybee_cds'
    
    results = []
    
    for candidate in candidates:
        cand_id = candidate.get('id', 'unknown')
        sequence = candidate.get('sequence', '')
        
        if not sequence:
            results.append({
                'candidate_id': cand_id,
                'error': 'No sequence',
                'safe': False
            })
            continue
        
        # Write temp query file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fa', delete=False) as f:
            f.write(f">{cand_id}\n{sequence}\n")
            query_file = f.name
        
        try:
            human_max = run_blast_query(query_file, str(human_db))
            bee_max = run_blast_query(query_file, str(honeybee_db))
            
            max_match = max(human_max, bee_max)
            
            if max_match >= 19:
                status = 'reject'
                safe = False
            elif max_match >= 15:
                status = 'caution'
                safe = True
            else:
                status = 'safe'
                safe = True
            
            results.append({
                'candidate_id': cand_id,
                'human_max_match': human_max,
                'honeybee_max_match': bee_max,
                'max_match': max_match,
                'safety_status': status,
                'safe': safe
            })
        finally:
            os.unlink(query_file)
    
    output = {
        'success': True,
        'results': results
    }
    
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    safe_count = sum(1 for r in results if r.get('safe'))
    print(f"Screened {len(results)} candidates: {safe_count} safe")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidates', required=True)
    parser.add_argument('--blast-db-dir', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    
    blast_screen_candidates(args.candidates, args.blast_db_dir, args.output)
```

**Reference Doc:** `.deepagents/skills/blast-screen/references/safety_thresholds.md`
```
# EPA Safety Thresholds for dsRNA Off-Target Assessment

## Background
The EPA uses contiguous nucleotide match length as a proxy for off-target 
RNAi effects in non-target organisms.

## Thresholds
- **<15bp contiguous match**: No significant risk of off-target gene silencing
- **15-18bp match**: Low risk, but should be flagged for review
- **≥19bp match**: High risk, candidate should be rejected

## References
- EPA Guidelines for RNAi Biopesticide Assessment (2021)
- Kumar et al. "Off-target prediction for RNAi" (2018)
```

---

### Skill 6: score-rank

**File:** `.deepagents/skills/score-rank/SKILL.md`

```
---
name: score-rank
description: Calculate final scores combining efficacy and safety
---

# Score and Rank Candidates Skill

## When to Use This Skill
Use after BLAST screening to compute final rankings combining design quality, 
gene essentiality, and safety.

## Instructions

### Step 1: Run Scoring Script

    python .deepagents/skills/score-rank/scripts/calculate_scores.py \
      --candidates output/{species_slug}/candidates.json \
      --blast-results output/{species_slug}/blast_results.json \
      --essential-genes output/{species_slug}/essential_genes.json \
      --output output/{species_slug}/ranked_candidates.json

## Scoring Formula

**Efficacy Score (0-1):**

    efficacy = 0.3×GC_score + 0.2×poly_n_score + 0.2×position_score + 0.3×gene_score

- GC_score: 1.0 if optimal (35-50%), 0.7 if acceptable, 0.3 otherwise
- poly_n_score: 1.0 if no poly-N runs, 0.0 if present
- position_score: Normalized design_score (0-1)
- gene_score: Gene essentiality from identify-genes (0-1)

**Safety Score (0-1):**
- 1.0 if max_match < 15bp
- 0.7 if 15-18bp
- 0.0 if ≥19bp

**Combined Score:**

    combined = efficacy × safety

### Step 2: Generate Visualization
Create comprehensive scoring plots:

    python .deepagents/skills/score-rank/scripts/plot_rankings.py \
      --ranked output/{species_slug}/ranked_candidates.json \
      --output-dir output/{species_slug}/figures/

This creates:
- `score_breakdown.png` - Stacked bar chart showing efficacy/safety components
- `efficacy_vs_safety_scatter.png` - Scatter plot with candidates labeled
- `top_candidates_radar.png` - Radar chart comparing top 5 across all metrics
- `ranking_table.png` - Visual table of top 10 candidates with scores

### Step 3: Present Results and STOP

Present to user:
1. Top 5 candidates with combined scores
2. Show efficacy vs safety scatter plot
3. Show radar chart for top candidates
4. Highlight top recommendation with justification
5. Ask: "Ready to proceed to generate-report? (yes/no)"

**DO NOT PROCEED** until user confirms.

**Key insights to mention:**
- Which genes appear in top 5 rankings
- Trade-offs between efficacy and safety
- Whether literature-supported genes rank highly

## Expected Output
- `output/{species_slug}/ranked_candidates.json`
- `output/{species_slug}/figures/score_breakdown.png`
- `output/{species_slug}/figures/efficacy_vs_safety_scatter.png`
- `output/{species_slug}/figures/top_candidates_radar.png`

Sorted by combined_score descending.

## Available Tools
- `shell` - Run Python script and plotting
- `read_file` / `write_file` - Handle JSON
```

**Helper Script:** `.deepagents/skills/score-rank/scripts/calculate_scores.py`
```python
#!/usr/bin/env python3
"""Calculate final efficacy and safety scores."""
import json
import argparse

def calculate_scores(candidates_file, blast_file, genes_file, output_file):
    with open(candidates_file) as f:
        candidates = json.load(f)
    
    with open(blast_file) as f:
        blast_data = json.load(f)
        blast_results = blast_data.get('results', [])
    
    with open(genes_file) as f:
        genes = json.load(f)
    
    # Create lookups
    blast_lookup = {r['candidate_id']: r for r in blast_results}
    gene_lookup = {g['gene_name']: g['score'] for g in genes}
    
    scored = []
    
    for candidate in candidates:
        cand_id = candidate.get('id')
        gene_name = candidate.get('gene_name', '')
        
        blast = blast_lookup.get(cand_id, {})
        
        # Efficacy score
        gc = candidate.get('gc_content', 0.4)
        if 0.35 <= gc <= 0.50:
            gc_score = 1.0
        elif 0.30 <= gc <= 0.55:
            gc_score = 0.7
        else:
            gc_score = 0.3
        
        poly_n_score = 0.0 if candidate.get('has_poly_n', False) else 1.0
        
        design_score = candidate.get('design_score', 0)
        position_score = min(design_score / 5.0, 1.0)
        
        gene_essentiality = gene_lookup.get(gene_name, 0.5)
        
        efficacy = (
            0.3 * gc_score +
            0.2 * poly_n_score +
            0.2 * position_score +
            0.3 * gene_essentiality
        )
        
        # Safety score
        max_match = blast.get('max_match', 0)
        if max_match >= 19:
            safety = 0.0
        elif max_match >= 15:
            safety = 0.7
        else:
            safety = 1.0
        
        # Combined
        combined = efficacy * safety
        
        scored.append({
            **candidate,
            'efficacy_score': round(efficacy, 3),
            'safety_score': round(safety, 3),
            'combined_score': round(combined, 3),
            'human_max_match': blast.get('human_max_match', 0),
            'honeybee_max_match': blast.get('honeybee_max_match', 0),
            'safety_status': blast.get('safety_status', 'unknown')
        })
    
    # Sort by combined score
    scored.sort(key=lambda x: x['combined_score'], reverse=True)
    
    with open(output_file, 'w') as f:
        json.dump(scored, f, indent=2)
    
    print(f"Ranked {len(scored)} candidates")
    if scored:
        print(f"Top candidate: {scored[0]['id']} (score: {scored[0]['combined_score']})")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidates', required=True)
    parser.add_argument('--blast-results', required=True)
    parser.add_argument('--essential-genes', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    
    calculate_scores(args.candidates, args.blast_results, args.essential_genes, args.output)
```

---

### Skill 7: generate-report

**File:** `.deepagents/skills/generate-report/SKILL.md`

```
---
name: generate-report
description: Generate comprehensive markdown report with ranked candidates
---

# Generate Report Skill

## When to Use This Skill
Use as the final step to create a human-readable markdown report with all 
results, recommendations, and safety analysis.

## Instructions

### Step 1: Load All Data Files
Use `read_file` for:
- `output/{species_slug}/ranked_candidates.json`
- `output/{species_slug}/essential_genes.json`
- `output/{species_slug}/literature_search.json`

### Step 2: Generate Report
Use `write_file` to create `output/{species_slug}/report.md` following the 
template in `references/report_template.md`

### Step 3: Create Summary Dashboard
Generate a final summary visualization:

    python .deepagents/skills/generate-report/scripts/create_dashboard.py \
      --data-dir output/{species_slug}/ \
      --figures-dir output/{species_slug}/figures/ \
      --output output/{species_slug}/figures/summary_dashboard.png

This creates a multi-panel dashboard showing:
- Top 3 candidates with scores
- Safety statistics pie chart
- Gene essentiality scores
- Workflow completion checklist

### Step 4: Present Final Results

Present to user:
1. Report generated successfully at `output/{species_slug}/report.md`
2. Show summary dashboard
3. Highlight:
   - **Top recommendation**: [candidate ID] targeting [gene]
   - **Combined score**: X.XX
   - **Safety status**: Safe/Caution
   - **Key strength**: [e.g., "High efficacy + literature support"]
4. Next steps: Review report and synthesize top candidate for testing

**WORKFLOW COMPLETE** - No further steps.

## Report Structure

1. **Executive Summary**
   - Target species
   - Number of candidates evaluated
   - Top recommendation with justification

2. **Top Candidates Table**
   - Show top 5 candidates
   - Columns: Rank, ID, Gene, Efficacy, Safety, Combined

3. **Detailed Analysis**
   - For each top candidate (top 3):
     - Gene name and function
     - Sequence (formatted as code block)
     - GC content, length, position
     - Off-target matches (human/honeybee)
     - Safety status with icon

4. **Off-Target Safety Analysis**
   - Table of all candidates with match lengths
   - Summary statistics

5. **Essential Genes Identified**
   - Table showing top genes evaluated
   - Evidence sources (orthology, literature)

6. **Literature References**
   - Papers found for this species
   - Key genes mentioned

7. **Recommendations**
   - Which candidate to synthesize first
   - Alternative candidates
   - Testing protocol suggestions

8. **Figures Appendix**
   - All generated plots embedded or referenced

## Expected Output
- `output/{species_slug}/report.md` - Professional markdown report
- `output/{species_slug}/figures/summary_dashboard.png` - Final dashboard
- Complete audit trail of all intermediate files and plots

## Available Tools
- `read_file` - Load JSON data
- `write_file` - Create report
- `shell` - Run dashboard generation script
```

**Reference:** `.deepagents/skills/generate-report/references/report_template.md`
```
# dsRNA Design Report: {species}

Generated: {date}

## Executive Summary

**Target Species:** {species}  
**Candidates Evaluated:** {total_candidates}  
**Safe Candidates:** {safe_count}  
**Top Recommendation:** {top_candidate_id}

{top_candidate_summary}

---

## Top Candidates

| Rank | ID | Target Gene | Efficacy | Safety | Combined | Status |
|------|-------|-------------|----------|--------|----------|--------|
| 1 | {id} | {gene} | {efficacy} | {safety} | {combined} | {icon} |

---

## Detailed Candidate Analysis

### Candidate 1: {id}

**Target Gene:** {gene_name} ({gene_function})

**Sequence (300bp):**

    {sequence}

**Design Metrics:**
- **GC Content:** {gc_content}%
- **Position:** {start}-{end} bp in CDS
- **Design Score:** {design_score}/5

**Off-Target Analysis:**
- **Human:** {human_match} bp max match ✅
- **Honeybee:** {bee_match} bp max match ✅
- **Status:** Safe for use

**Efficacy Score:** {efficacy}/1.0  
**Safety Score:** {safety}/1.0  
**Combined Score:** {combined}/1.0

---

## Off-Target Safety Summary

| Candidate | Human Match | Honeybee Match | Max Match | Status |
|-----------|-------------|----------------|-----------|--------|
| {id} | {h} bp | {b} bp | {m} bp | {status} |

**Safety Statistics:**
- Safe (<15bp): {safe_count}
- Caution (15-18bp): {caution_count}
- Rejected (≥19bp): {reject_count}

---

## Essential Genes Evaluated

Top 5 genes identified in {species}:

| Gene Name | Function | Score | Evidence |
|-----------|----------|-------|----------|
| {name} | {function} | {score} | Orthology + Literature |

---

## Literature References

{paper_count} papers found for RNAi in {species}:

- PMID:{pmid} - {title}
  - Genes mentioned: {gene_list}

---

## Recommendations

### Primary Recommendation
Synthesize and test **{top_id}** targeting {gene_name}. This candidate has:
- High efficacy score ({efficacy})
- Excellent safety profile (max {max_match}bp match)
- Targets essential gene with literature support

### Alternative Candidates
If {top_id} shows insufficient efficacy:
1. **{second_id}** - {justification}
2. **{third_id}** - {justification}

### Testing Protocol
1. Synthesize dsRNA via in vitro transcription
2. Test via feeding assay at 50-500 ng/μL
3. Measure mortality at 48h, 72h, 96h
4. Confirm target gene knockdown via qPCR

---

## Methods

**Genome Source:** NCBI RefSeq ({assembly_id})  
**Essential Genes Database:** DEG + FlyBase ({n} curated genes)  
**Off-Target Screening:** BLAST+ vs. GRCh38 human + honeybee HAv3.1  
**Safety Threshold:** EPA guideline (19bp contiguous match)  
```

---

### Phase 2.5: Implement Plotting Scripts

Each skill needs accompanying plotting scripts. Here are example implementations:

**Example: `.deepagents/skills/fetch-genome/scripts/plot_genome_stats.py`**
```python
#!/usr/bin/env python3
"""Generate genome statistics visualizations."""
import argparse
import json
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from Bio import SeqIO
import numpy as np

def plot_genome_stats(genome_fasta, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Parse genome
    sequences = list(SeqIO.parse(genome_fasta, 'fasta'))
    
    # Calculate stats
    lengths = [len(seq.seq) for seq in sequences]
    gc_contents = [(seq.seq.count('G') + seq.seq.count('C')) / len(seq.seq) 
                   for seq in sequences]
    
    # GC distribution
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(gc_contents, bins=50, edgecolor='black', alpha=0.7)
    ax.axvline(np.mean(gc_contents), color='red', linestyle='--', 
               label=f'Mean: {np.mean(gc_contents):.3f}')
    ax.set_xlabel('GC Content')
    ax.set_ylabel('Number of CDS')
    ax.set_title('GC Content Distribution Across All CDS')
    ax.legend()
    plt.tight_layout()
    plt.savefig(output_dir / 'genome_gc_distribution.png', dpi=300)
    plt.close()
    
    # Length distribution
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(lengths, bins=50, edgecolor='black', alpha=0.7)
    ax.axvline(np.mean(lengths), color='red', linestyle='--',
               label=f'Mean: {np.mean(lengths):.0f} bp')
    ax.set_xlabel('CDS Length (bp)')
    ax.set_ylabel('Number of CDS')
    ax.set_title('CDS Length Distribution')
    ax.legend()
    plt.tight_layout()
    plt.savefig(output_dir / 'genome_length_distribution.png', dpi=300)
    plt.close()
    
    # Save stats
    stats = {
        'total_sequences': len(sequences),
        'total_length': sum(lengths),
        'mean_length': np.mean(lengths),
        'median_length': np.median(lengths),
        'mean_gc': np.mean(gc_contents),
        'median_gc': np.median(gc_contents)
    }
    
    with open(output_dir / 'genome_stats.json', 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"✓ Generated plots in {output_dir}")
    print(f"  - Total CDS: {stats['total_sequences']:,}")
    print(f"  - Mean GC: {stats['mean_gc']:.3f}")
    print(f"  - Mean length: {stats['mean_length']:.0f} bp")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--genome', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    
    plot_genome_stats(args.genome, args.output_dir)
```

**Example: `.deepagents/skills/blast-screen/scripts/plot_safety.py`**
```python
#!/usr/bin/env python3
"""Generate safety analysis visualizations."""
import argparse
import json
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

def plot_safety_analysis(blast_results_file, candidates_file, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    with open(blast_results_file) as f:
        blast_data = json.load(f)
    with open(candidates_file) as f:
        candidates = json.load(f)
    
    results = blast_data['results']
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Add gene names from candidates
    gene_map = {c['id']: c['gene_name'] for c in candidates}
    df['gene'] = df['candidate_id'].map(gene_map)
    
    # Safety heatmap
    fig, ax = plt.subplots(figsize=(12, 8))
    heatmap_data = df[['candidate_id', 'human_max_match', 'honeybee_max_match']].set_index('candidate_id')
    sns.heatmap(heatmap_data, annot=True, fmt='d', cmap='RdYlGn_r', 
                vmin=0, vmax=20, cbar_kws={'label': 'Match Length (bp)'}, ax=ax)
    ax.set_title('Off-Target Match Lengths by Candidate')
    ax.set_xlabel('Species')
    ax.set_ylabel('Candidate')
    plt.tight_layout()
    plt.savefig(output_dir / 'safety_heatmap.png', dpi=300)
    plt.close()
    
    # Match distribution
    fig, ax = plt.subplots(figsize=(10, 6))
    all_matches = list(df['human_max_match']) + list(df['honeybee_max_match'])
    ax.hist(all_matches, bins=20, edgecolor='black', alpha=0.7)
    ax.axvline(15, color='orange', linestyle='--', label='Caution threshold (15bp)')
    ax.axvline(19, color='red', linestyle='--', label='Reject threshold (19bp)')
    ax.set_xlabel('Match Length (bp)')
    ax.set_ylabel('Frequency')
    ax.set_title('Distribution of Off-Target Match Lengths')
    ax.legend()
    plt.tight_layout()
    plt.savefig(output_dir / 'safety_distribution.png', dpi=300)
    plt.close()
    
    # Safety by gene
    safety_counts = df.groupby(['gene', 'safety_status']).size().unstack(fill_value=0)
    fig, ax = plt.subplots(figsize=(10, 6))
    safety_counts.plot(kind='bar', stacked=False, ax=ax, 
                       color={'safe': 'green', 'caution': 'orange', 'reject': 'red'})
    ax.set_xlabel('Target Gene')
    ax.set_ylabel('Number of Candidates')
    ax.set_title('Safety Status by Target Gene')
    ax.legend(title='Safety Status')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_dir / 'safety_by_gene.png', dpi=300)
    plt.close()
    
    print(f"✓ Generated safety plots in {output_dir}")
    print(f"  - Safe: {sum(df['safety_status'] == 'safe')}")
    print(f"  - Caution: {sum(df['safety_status'] == 'caution')}")
    print(f"  - Reject: {sum(df['safety_status'] == 'reject')}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--blast-results', required=True)
    parser.add_argument('--candidates', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    
    plot_safety_analysis(args.blast_results, args.candidates, args.output_dir)
```

**Note:** Similar plotting scripts should be created for all other skills following the same pattern:
1. Parse JSON data
2. Create informative visualizations using matplotlib/seaborn
3. Save high-resolution PNG files
4. Print summary statistics

---

### Phase 3: Test End-to-End

**Task 3.1: Verify Skills are Loaded**
```bash
cd /Users/hannes/katalyze/dsrna-designer
deepagents skills list
```

Should show all 7 skills with descriptions.

**Task 3.2: Run Complete Workflow**
```bash
deepagents run "Design dsRNA candidates for Drosophila suzukii (spotted wing drosophila)"
```

**Task 3.3: Verify Outputs**
```bash
ls -lh output/drosophila_suzukii/
# Should show:
# - genome.fasta
# - literature_search.json
# - essential_genes.json
# - candidates.json
# - blast_results.json
# - ranked_candidates.json
# - report.md
```

---

## Dependencies

**Update pyproject.toml:**
```toml
[project]
name = "dsrna-designer"
version = "0.2.0"
requires-python = ">=3.11"
dependencies = [
    "deepagents-cli>=0.0.12",
    "biopython>=1.84",
    "python-dotenv>=1.2.1",
    "matplotlib>=3.8.0",
    "seaborn>=0.13.0",
    "pandas>=2.1.0",
    "numpy>=1.26.0",
]

[project.scripts]
dsrna = "deepagents run"
```

**Visualization Libraries:**
- **matplotlib**: Core plotting functionality
- **seaborn**: Statistical visualizations (heatmaps, distributions)
- **pandas**: Data manipulation for plotting
- **numpy**: Numerical operations

**No custom Python package needed!** All logic is in skills + helper scripts.

---

## Comparison: Custom Tools vs Skills

| Aspect | Custom Tools (v1) | Skills (v3) |
|--------|------------------|-------------|
| Code | 800 lines Python | 7 SKILL.md + 7 scripts (~500 lines) |
| Installation | pip install package | Copy `.deepagents/` folder |
| Modifications | Edit Python, reinstall | Edit markdown/scripts |
| Token usage | ~3000 tokens (all schemas) | ~500 tokens (frontmatter only) |
| Extensibility | Add new @tool function | Agent can create new skills |
| Debugging | Python stack traces | Review shell command outputs |
| Sharing | PyPI or git clone | Copy folder, works immediately |

---

## Migration Path from v1

If you want to keep existing custom tools:

**Hybrid approach:**
1. Keep `dsrna_agent/tools.py` as-is
2. Add skills to `.deepagents/skills/` for workflow orchestration
3. Skills can call custom tools when available
4. Gradually migrate tools → skills as needed

---

## Visualization Summary

Each step produces specific visualizations for user review:

| Step | Visualizations Generated | Purpose |
|------|--------------------------|---------|
| **1. fetch-genome** | • GC distribution histogram<br>• CDS length distribution | Assess genome quality, identify anomalies |
| **2. literature-search** | • Gene mention frequency bar chart<br>• Papers timeline | Identify literature-supported targets |
| **3. identify-genes** | • Gene ranking bar chart<br>• Evidence breakdown (stacked)<br>• Length distribution | Evaluate gene selection quality |
| **4. design-dsrna** | • Candidate genomic locations<br>• GC content distribution<br>• Score component heatmap | Review candidate design parameters |
| **5. blast-screen** | • Safety heatmap (candidates × species)<br>• Match length distribution<br>• Safety by gene grouping | Assess off-target risks |
| **6. score-rank** | • Efficacy vs safety scatter plot<br>• Score breakdown stacked bars<br>• Top-5 radar chart | Compare candidates across metrics |
| **7. generate-report** | • Summary dashboard (multi-panel) | Final overview of entire workflow |

**Total Visualizations:** ~20 plots across all steps

## Success Criteria

✅ All 7 skills load at startup  
✅ Agent completes ONE step at a time, waiting for approval  
✅ All visualizations generate without errors  
✅ Agent presents results clearly after each step  
✅ Output directory contains all expected files  
✅ Report.md is scientifically accurate and complete  
✅ All safe candidates have <15bp off-target matches  
✅ Top recommendation has clear justification  
✅ User can review/intervene at any checkpoint

---

## Quick Reference: Skills Checklist

| Skill | SKILL.md | Helper Scripts | Plotting Scripts | Checkpoint Question |
|-------|----------|----------------|------------------|---------------------|
| 1. fetch-genome | ✓ | ncbi_download.py | plot_genome_stats.py | "Ready to search literature?" |
| 2. literature-search | ✓ | parse_pubmed.py | plot_literature.py | "Ready to identify genes?" |
| 3. identify-genes | ✓ | match_essential.py | plot_genes.py | "Ready to design dsRNA?" |
| 4. design-dsrna | ✓ | sliding_window.py | plot_candidates.py | "Ready to screen for off-targets?" |
| 5. blast-screen | ✓ | run_blast.py | plot_safety.py | "Ready to calculate rankings?" |
| 6. score-rank | ✓ | calculate_scores.py | plot_rankings.py | "Ready to generate report?" |
| 7. generate-report | ✓ | (uses template) | create_dashboard.py | "Workflow complete!" |

**Total Files to Create:**
- 7 SKILL.md files
- ~7 helper scripts (data processing)
- ~7 plotting scripts (visualization)
- 1 agent.md (project config)
- ~21 files total in `.deepagents/skills/`

## Next Steps

1. **Create directory structure**
   ```bash
   mkdir -p .deepagents/skills/{fetch-genome,literature-search,identify-genes,design-dsrna,blast-screen,score-rank,generate-report}/{scripts,references}
   mkdir -p .deepagents/skills/{fetch-genome,literature-search,identify-genes,design-dsrna,blast-screen,score-rank,generate-report}/scripts
   ```

2. **Write all SKILL.md files** (use specifications from Phase 2 above)

3. **Write helper Python scripts** (data processing logic)

4. **Write plotting scripts** (visualization generation)

5. **Create project agent.md** (workflow orchestration rules)

6. **Test with Drosophila suzukii** (verify checkpoint workflow)

7. **Validate against known RNAi literature** (scientific accuracy)

8. **Document in README** (user guide with examples)

## Implementation Priority

**Phase 1 (Core Functionality):**
- All 7 SKILL.md files
- All helper scripts (data processing)
- Basic plotting scripts (histograms, bar charts)

**Phase 2 (Enhanced Visualizations):**
- Advanced plots (heatmaps, radar charts, dashboards)
- Color-coded safety indicators
- Multi-panel summary figures

**Phase 3 (Polish):**
- Error handling in scripts
- Progress indicators
- Result caching for re-runs
