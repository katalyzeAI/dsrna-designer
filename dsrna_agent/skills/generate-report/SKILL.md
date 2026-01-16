---
name: generate-report
description: Generate comprehensive markdown report with ranked candidates
---

# Generate Report Skill

## When to Use This Skill

Use as the final step to create a human-readable markdown report with all
results, recommendations, and safety analysis.

## Data Storage Structure

**Reads from:**
- `data/{assembly}/genome_metadata.json` - Cached genome metadata
- `output/{run}/ranked_candidates.json` - From score-rank step
- `output/{run}/essential_genes.json` - From identify-genes step
- `output/{run}/literature_search.json` - From literature search (optional)
- `output/{run}/blast_results.json` - From blast-screen step

**Writes to:**
- `output/{run}/report.md` - Final markdown report
- `output/{run}/figures/summary_dashboard.png` - Final dashboard

## Instructions

### Step 1: Load All Data Files

Use `read_file` for:
- `output/{run}/ranked_candidates.json`
- `output/{run}/essential_genes.json`
- `output/{run}/literature_search.json` (optional - if literature was searched)
- `output/{run}/blast_results.json`
- `data/{assembly}/genome_metadata.json` (cached input data)

**Tip:** If literature references are needed for the report but `literature_search.json`
doesn't exist, use the `literature-search` utility skill now to enrich the report.

### Step 2: Generate Report

Create `output/{run}/report.md` following the structure below.

Use the report template in `references/report_template.md` as a guide.

### Step 3: Create Summary Dashboard

Generate a final summary visualization:

```bash
python .deepagents/skills/generate-report/scripts/create_dashboard.py \
  --data-dir output/{run}/ \
  --output output/{run}/figures/summary_dashboard.png
```

This creates a multi-panel dashboard showing:
- Top 3 candidates with scores
- Safety statistics pie chart
- Gene essentiality scores
- Workflow completion checklist

### Step 4: Present Final Results

Output this summary to the user:

```
## Workflow Complete

**Report Generated:** `output/{run}/report.md`

**Top Recommendation:**
- **Candidate:** {top_candidate}
- **Target Gene:** {gene_name} - {gene_function}
- **Combined Score:** {score}
- **Safety Status:** Safe
- **Key Strength:** {rationale}

**Sequence (300bp):**
```
{sequence}
```

**Files Created:**
- `output/{run}/report.md`
- `output/{run}/figures/summary_dashboard.png`

**Dashboard:** [Show summary dashboard]

---
**Next Steps:**
1. Review the full report at `output/{run}/report.md`
2. Order synthesis of top candidate sequence
3. Design feeding bioassay protocol
```

## Report Structure

### 1. Executive Summary
- Target species
- Number of candidates evaluated
- Top recommendation with justification

### 2. Top Candidates Table
| Rank | ID | Target Gene | Efficacy | Safety | Combined | Status |
|------|-----|-------------|----------|--------|----------|--------|

### 3. Detailed Candidate Analysis
For top 3 candidates:
- Gene name and function
- Sequence (formatted as code block)
- GC content, length, position
- Off-target matches (human/honeybee)
- Safety status with icon

### 4. Off-Target Safety Analysis
- Table of all candidates with match lengths
- Summary statistics (safe/caution/reject counts)

### 5. Essential Genes Identified
- Table showing top genes evaluated
- Evidence sources (orthology, literature)

### 6. Literature References (if available)
- Papers found for this species
- Key genes mentioned
- (Note: If no literature search was run, state "No literature search performed")

### 7. Recommendations
- Which candidate to synthesize first
- Alternative candidates
- Testing protocol suggestions

### 8. Methods Summary
- Genome source (NCBI assembly ID)
- Essential genes database
- Off-target screening (BLAST parameters)
- Safety thresholds applied

## Expected Output

All outputs go in `output/{run}/`:
- `report.md` - Professional markdown report
- `figures/summary_dashboard.png` - Final dashboard
- Complete audit trail of all intermediate files and plots

## Available Tools

- `read_file` - Load JSON data
- `write_file` - Create report
- `shell` - Run dashboard generation script

## Report Quality Checklist

Before presenting to user, verify:
- [ ] All sections populated
- [ ] Top candidate clearly identified
- [ ] Safety analysis complete
- [ ] Figures referenced correctly
- [ ] No placeholder text remaining
- [ ] Scientific accuracy of claims
