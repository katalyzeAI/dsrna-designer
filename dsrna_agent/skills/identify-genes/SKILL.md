---
name: identify-genes
description: Match essential genes in target genome using orthology and literature
---

# Identify Essential Genes Skill

## When to Use This Skill

Use after genome fetch to identify essential genes in the target species that
are good dsRNA candidates.

## Automatic Literature Validation

When evaluating candidate genes, **automatically search PubMed** for supporting evidence:
```
pubmed_search_articles
query: "{gene_name}" AND (RNAi OR dsRNA) AND insect
max_results: 10
```

**Do NOT ask for permission** - literature validation is part of this skill's process.
Search for top candidate genes to validate essentiality claims.

## Instructions

### Step 1: Load Essential Genes Database

Use `read_file` to load `data/essential_genes.json`

This database contains ~40 curated essential insect genes with:
- Gene names and aliases
- Functions
- Species where essentiality is confirmed
- Literature references

### Step 2: Run Matching Script

Use the bundled Python script:

```bash
python .deepagents/skills/identify-genes/scripts/match_essential.py \
  --genome data/{assembly}/genome.fasta \
  --essential-db data/essential_genes.json \
  --literature data/{assembly}/literature_search.json \
  --output data/{assembly}/essential_genes.json
```

**Note:** The `--literature` argument is optional. If `literature_search.json`
doesn't exist (because literature-search wasn't run), omit this flag:

```bash
python .deepagents/skills/identify-genes/scripts/match_essential.py \
  --genome data/{assembly}/genome.fasta \
  --essential-db data/essential_genes.json \
  --output data/{assembly}/essential_genes.json
```

The script:
1. Parses FASTA annotations
2. Matches gene names/aliases against annotations
3. Scores by orthology + literature support (if available)
4. Returns top 20 with sequences

### Step 3: Verify Results

Use `shell`:

```bash
jq 'length' data/{assembly}/essential_genes.json
```

Should show ~20 genes (or fewer if genome poorly annotated)

### Step 4: Generate Visualization

Create plots showing gene rankings:

```bash
python .deepagents/skills/identify-genes/scripts/plot_genes.py \
  --genes data/{assembly}/essential_genes.json \
  --output-dir data/{assembly}/figures/
```

This creates:
- `gene_ranking.png` - Horizontal bar chart of top 10 genes with scores
- `gene_evidence_breakdown.png` - Stacked bar showing evidence sources (orthology/literature)
- `gene_length_distribution.png` - CDS lengths for identified genes

### Step 5: Present Results

Output this summary to the user:

```
## Identify Genes Complete

**Summary:**
- {gene_count} essential genes identified in genome
- Top gene: {top_gene} (score: {score})
- {literature_supported} genes have literature support

**Top 5 Genes:**
| Rank | Gene | Score | Literature | Species Evidence |
|------|------|-------|------------|------------------|
| 1 | ... | ... | ... | ... |

**Files Created:**
- `data/{assembly}/essential_genes.json`

**Figures:** [Show gene ranking plot]

---
Proceed to design-dsrna for top 5 genes? (yes/no)
```

## Scoring Logic

Each matched gene receives a score from 0 to 1:

| Component | Points | Condition |
|-----------|--------|-----------|
| Base (ortholog match) | 0.50 | Gene name/alias found in genome |
| Literature support | +0.30 | Gene mentioned in PubMed results |
| Multi-species essential | +0.05 per species | Up to +0.20 max |

**Maximum score: 1.0**

## Output Format

`data/{assembly}/essential_genes.json`:
```json
[
  {
    "gene_id": "lcl|NC_XXX_cds_XP_XXX",
    "gene_name": "vATPase",
    "function": "Vacuolar proton pump - essential for pH homeostasis",
    "score": 0.85,
    "evidence": {
      "ortholog_match": true,
      "literature_support": true,
      "essential_in_species": ["D. melanogaster", "T. castaneum"]
    },
    "sequence": "ATGCGT...",
    "sequence_length": 1842
  }
]
```

## Expected Output

- `data/{assembly}/essential_genes.json`
- `data/{assembly}/figures/gene_ranking.png`
- `data/{assembly}/figures/gene_evidence_breakdown.png`
- `data/{assembly}/figures/gene_length_distribution.png`

## Available Tools

- `read_file` - Load databases
- `shell` - Run Python script and plotting
- `write_file` - Save results
