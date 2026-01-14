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

```bash
blastn -version
ls data/blast_db/*.n*
```

If missing, run `./setup_blast_db.sh` first.

## Instructions

### Step 1: Verify BLAST Setup

```bash
blastn -version
ls -la data/blast_db/
```

If databases don't exist, instruct user to run setup script and wait.

### Step 2: Run BLAST Screening Script

```bash
python .deepagents/skills/blast-screen/scripts/run_blast.py \
  --candidates output/{species_slug}/candidates.json \
  --blast-db-dir data/blast_db \
  --output output/{species_slug}/blast_results.json
```

The script:
1. Writes each candidate to temp FASTA
2. Runs blastn against human_cds and honeybee_cds
3. Parses output for max alignment length
4. Applies EPA safety thresholds

### Step 3: Verify Results

```bash
jq '[.results[] | select(.safety_status == "reject")] | length' \
  output/{species_slug}/blast_results.json
```

### Step 4: Generate Visualization

Create safety analysis plots:

```bash
python .deepagents/skills/blast-screen/scripts/plot_safety.py \
  --blast-results output/{species_slug}/blast_results.json \
  --candidates output/{species_slug}/candidates.json \
  --output-dir output/{species_slug}/figures/
```

This creates:
- `safety_heatmap.png` - Heatmap showing human/honeybee matches for each candidate
- `safety_distribution.png` - Histogram of match lengths
- `safety_by_gene.png` - Grouped bar chart of safety status per target gene

### Step 5: Present Results

Output this summary to the user:

```
## BLAST Screening Complete

**Summary:**
- {total} candidates screened against human and honeybee CDS
- Safe (<15bp): {safe_count} candidates
- Caution (15-18bp): {caution_count} candidates
- Rejected (>=19bp): {reject_count} candidates

**Safety Results:**
| Candidate | Human Match | Honeybee Match | Status |
|-----------|-------------|----------------|--------|
| vATPase_1 | 12bp | 14bp | Safe |
| ... | ... | ... | ... |

**Files Created:**
- `output/{species_slug}/blast_results.json`

**Figures:** [Show safety heatmap]

---
Proceed to score-rank? (yes/no)
```

**Note:** If >5 candidates are rejected, warn user that ranking may include marginal candidates.

## Safety Thresholds (EPA Guidelines)

| Match Length | Status | Color | Action |
|--------------|--------|-------|--------|
| <15 bp | ✅ Safe | Green | Proceed to ranking |
| 15-18 bp | ⚠️ Caution | Yellow | Flag but include |
| ≥19 bp | ❌ Reject | Red | Exclude from ranking |

These thresholds are based on:
- EPA Guidelines for RNAi Biopesticide Assessment
- Published research on minimum siRNA complementarity for gene silencing
- Conservative approach for environmental safety

## Output Format

`output/{species_slug}/blast_results.json`:
```json
{
  "success": true,
  "screening_date": "2024-01-15",
  "databases_used": ["human_cds", "honeybee_cds"],
  "results": [
    {
      "candidate_id": "vATPase_1",
      "human_max_match": 12,
      "honeybee_max_match": 14,
      "max_match": 14,
      "safety_status": "safe",
      "safe": true
    }
  ]
}
```

## Expected Output

- `output/{species_slug}/blast_results.json`
- `output/{species_slug}/figures/safety_heatmap.png`
- `output/{species_slug}/figures/safety_distribution.png`
- `output/{species_slug}/figures/safety_by_gene.png`

## Available Tools

- `shell` - Check BLAST installation, run script and plotting
- `read_file` / `write_file` - Handle JSON

## Troubleshooting

### BLAST not found
```bash
# macOS
brew install blast

# Ubuntu/Debian
sudo apt-get install ncbi-blast+
```

### Database files missing
```bash
./setup_blast_db.sh
```

### BLAST timeout
- Increase timeout in run_blast.py
- Or screen candidates in smaller batches
