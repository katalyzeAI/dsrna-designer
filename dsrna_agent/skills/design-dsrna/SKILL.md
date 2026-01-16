---
name: design-dsrna
description: Design dsRNA candidates using sliding window algorithm
---

# Design dsRNA Candidates Skill

## When to Use This Skill

Use after identifying essential genes to design 3 dsRNA candidates per gene
for the top 5 genes (15 total candidates).

## Data Storage Structure

**Reads from:**
- `output/{run}/essential_genes.json` - From identify-genes step

**Writes to:**
- `output/{run}/candidates.json` - Designed dsRNA candidates
- `output/{run}/figures/` - Visualization plots

## Instructions

### Step 1: Select Top 5 Genes

Use `shell` with jq:

```bash
jq '.[0:5]' output/{run}/essential_genes.json > /tmp/top5_genes.json
```

### Step 2: Design Candidates

Run the sliding window design script:

```bash
python .deepagents/skills/design-dsrna/scripts/sliding_window.py \
  --genes output/{run}/essential_genes.json \
  --num-genes 5 \
  --candidates-per-gene 3 \
  --length 300 \
  --output output/{run}/candidates.json
```

This processes top 5 genes and generates 3 candidates each = 15 total.

### Step 3: Verify Output

```bash
jq 'length' output/{run}/candidates.json
```

Should show 15 (or fewer if some genes are too short)

### Step 4: Generate Visualization

Create plots showing candidate design quality:

```bash
python .deepagents/skills/design-dsrna/scripts/plot_candidates.py \
  --candidates output/{run}/candidates.json \
  --genes output/{run}/essential_genes.json \
  --output-dir output/{run}/figures/
```

This creates:
- `candidate_locations.png` - Genomic positions of candidates along each gene
- `candidate_gc_distribution.png` - Histogram of GC content across all candidates
- `candidate_scores_heatmap.png` - Heatmap showing design score components

### Step 5: Present Results

Output this summary to the user:

```
## Design dsRNA Complete

**Summary:**
- {candidate_count} candidates designed from {gene_count} genes
- GC content range: {min_gc}% - {max_gc}%
- All candidates are 300bp

**Candidates by Gene:**
| Gene | Candidate | Position | GC% | Score |
|------|-----------|----------|-----|-------|
| vATPase | vATPase_1 | 150-450 | 42.3% | 5 |
| ... | ... | ... | ... | ... |

**Files Created:**
- `output/{run}/candidates.json`
- `output/{run}/figures/candidate_locations.png`

**Figures:** [Show candidate locations plot]

---
Proceed to blast-screen? (yes/no)
```

## Design Algorithm

### Sliding Window Parameters
- **Window length**: 300 bp (optimal for dsRNA synthesis)
- **Step size**: 50 bp
- **Candidates per gene**: 3 (non-overlapping)

### Window Scoring (0-5 points)

| Criterion | Points | Condition |
|-----------|--------|-----------|
| Optimal GC | +2 | 35-50% GC content |
| Acceptable GC | +1 | 30-55% GC content |
| No poly-N runs | +1 | No 4+ consecutive same base |
| Good start position | +1 | Not in first 75bp of CDS |
| Good end position | +1 | Not in last 50bp of CDS |

### Selection Process
1. Score all windows
2. Sort by score (descending)
3. Select highest-scoring non-overlapping windows
4. Take top 3 per gene

## Output Format

`output/{run}/candidates.json`:
```json
[
  {
    "id": "vATPase_1",
    "gene_name": "vATPase",
    "gene_id": "lcl|NC_XXX_cds_XP_XXX",
    "sequence": "ATGCGTACG...",
    "start": 150,
    "end": 450,
    "length": 300,
    "gc_content": 0.423,
    "has_poly_n": false,
    "design_score": 5
  }
]
```

## Expected Output

All outputs go in `output/{run}/`:
- `candidates.json`
- `figures/candidate_locations.png`
- `figures/candidate_gc_distribution.png`
- `figures/candidate_scores_heatmap.png`

## Available Tools

- `shell` - Run Python script, jq, and plotting
- `read_file` / `write_file` - Handle JSON

## Notes

- If a gene is shorter than 300bp, it will be skipped
- Overlapping candidates are avoided to maximize coverage
- Lower-scoring candidates may be selected if needed for non-overlap
