---
name: score-rank
description: Calculate final scores combining efficacy and safety
---

# Score and Rank Candidates Skill

## When to Use This Skill

Use after BLAST screening to compute final rankings combining design quality,
gene essentiality, and safety.

## Data Storage Structure

**Reads from:**
- `output/{run}/candidates.json` - From design-dsrna step
- `output/{run}/blast_results.json` - From blast-screen step
- `output/{run}/essential_genes.json` - From identify-genes step

**Writes to:**
- `output/{run}/ranked_candidates.json` - Final ranked list
- `output/{run}/figures/` - Scoring visualization plots

## Instructions

### Step 1: Run Scoring Script

```bash
python .deepagents/skills/score-rank/scripts/calculate_scores.py \
  --candidates output/{run}/candidates.json \
  --blast-results output/{run}/blast_results.json \
  --essential-genes output/{run}/essential_genes.json \
  --output output/{run}/ranked_candidates.json
```

### Step 2: Verify Rankings

```bash
jq '.[0:5] | .[] | {id, gene_name, combined_score, safety_status}' \
  output/{run}/ranked_candidates.json
```

### Step 3: Generate Visualization

Create comprehensive scoring plots:

```bash
python .deepagents/skills/score-rank/scripts/plot_rankings.py \
  --ranked output/{run}/ranked_candidates.json \
  --output-dir output/{run}/figures/
```

This creates:
- `score_breakdown.png` - Stacked bar chart showing efficacy/safety components
- `efficacy_vs_safety_scatter.png` - Scatter plot with candidates labeled
- `top_candidates_radar.png` - Radar chart comparing top 5 across all metrics

### Step 4: Present Results

Output this summary to the user:

```
## Score and Rank Complete

**Top 5 Candidates:**
| Rank | Candidate | Gene | Efficacy | Safety | Combined |
|------|-----------|------|----------|--------|----------|
| 1 | vATPase_1 | vATPase | 0.87 | 1.0 | 0.87 |
| 2 | ... | ... | ... | ... | ... |

**Top Recommendation:** {top_candidate} targeting {gene}
- Combined score: {score}
- Rationale: {why_this_candidate}

**Files Created:**
- `output/{run}/ranked_candidates.json`
- `output/{run}/figures/score_breakdown.png`

**Figures:** [Show efficacy vs safety scatter plot]

---
Proceed to generate-report? (yes/no)
```

**Insights to include:**
- Which genes appear multiple times in top 5
- Trade-offs between efficacy and safety
- Whether literature-supported genes rank highly

## Scoring Formula

### Efficacy Score (0-1)

```
efficacy = 0.3×GC_score + 0.2×poly_n_score + 0.2×position_score + 0.3×gene_score
```

| Component | Weight | Calculation |
|-----------|--------|-------------|
| GC_score | 0.3 | 1.0 if 35-50%, 0.7 if 30-55%, 0.3 otherwise |
| poly_n_score | 0.2 | 1.0 if no poly-N runs, 0.0 if present |
| position_score | 0.2 | design_score / 5.0 (normalized) |
| gene_score | 0.3 | Gene essentiality from identify-genes (0-1) |

### Safety Score (0-1)

| Max Match | Safety Score |
|-----------|--------------|
| <15 bp | 1.0 |
| 15-18 bp | 0.7 |
| ≥19 bp | 0.0 |

### Combined Score

```
combined = efficacy × safety
```

**Note:** Rejected candidates (≥19bp match) get combined score of 0.

## Output Format

`output/{run}/ranked_candidates.json`:
```json
[
  {
    "id": "vATPase_1",
    "gene_name": "vATPase",
    "gene_id": "lcl|NC_XXX",
    "sequence": "ATGCGT...",
    "start": 150,
    "end": 450,
    "length": 300,
    "gc_content": 0.423,
    "has_poly_n": false,
    "design_score": 5,
    "efficacy_score": 0.87,
    "safety_score": 1.0,
    "combined_score": 0.87,
    "human_max_match": 12,
    "honeybee_max_match": 14,
    "safety_status": "safe"
  }
]
```

Sorted by `combined_score` descending.

## Expected Output

All outputs go in `output/{run}/`:
- `ranked_candidates.json`
- `figures/score_breakdown.png`
- `figures/efficacy_vs_safety_scatter.png`
- `figures/top_candidates_radar.png`

## Available Tools

- `shell` - Run Python script and plotting
- `read_file` / `write_file` - Handle JSON

## Interpretation Guide

### High Combined Score (>0.7)
- Excellent candidate for synthesis
- Good GC content, no poly-N, essential gene target, safe

### Medium Combined Score (0.4-0.7)
- Acceptable candidate
- May have suboptimal GC or caution-level off-targets

### Low Combined Score (<0.4)
- Consider alternatives
- Either low efficacy or safety concerns
