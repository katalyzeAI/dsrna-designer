---
name: full-workflow
description: Execute the complete dsRNA design workflow with human confirmation at each step
---

# Full Workflow Skill

## When to Use This Skill

Use when the user requests a complete dsRNA design workflow for a target species.
Trigger phrases: "design dsRNA for {species}", "full workflow", "complete analysis"

## CRITICAL: Human-in-the-Loop

**You MUST stop after each step and wait for user confirmation before proceeding.**

After each step:
1. Present a clear summary of results
2. Show any generated figures or key data
3. Ask explicitly: "Proceed to [next step]? (yes/no/adjust)"
4. Wait for user response before continuing
5. If user says "adjust" or provides feedback, incorporate it before moving on

**DO NOT run multiple steps without confirmation.**

## Workflow Overview

```
┌─────────────────┐
│ 1. fetch-genome │ → Download CDS sequences from NCBI
└────────┬────────┘
         │ ✋ CONFIRM
         ▼
┌──────────────────┐
│ 2. identify-genes│ → Find essential genes via orthology + literature
└────────┬─────────┘
         │ ✋ CONFIRM
         ▼
┌─────────────────┐
│ 3. design-dsrna │ → Generate 300bp candidates with optimal GC
└────────┬────────┘
         │ ✋ CONFIRM
         ▼
┌─────────────────┐
│ 4. blast-screen │ → Check off-target matches (human, honeybee)
└────────┬────────┘
         │ ✋ CONFIRM
         ▼
┌──────────────────┐
│ 5. score-rank   │ → Calculate efficacy × safety scores
└────────┬────────┘
         │ ✋ CONFIRM
         ▼
┌───────────────────┐
│ 6. generate-report│ → Create final report with recommendations
└───────────────────┘
```

## Instructions

### Step 1: Fetch Genome

Read and execute: `dsrna_agent/skills/fetch-genome/SKILL.md`

**Checkpoint Output:**
```
## ✅ Step 1 Complete: Fetch Genome

**Species:** {species_name} (TaxID: {taxid})
**Assembly:** {assembly_name}
**CDS Count:** {count} sequences
**Total Length:** {length} bp

**Literature Search:** Found {n} RNAi papers
Top mentioned genes: {gene1}, {gene2}, {gene3}

**Files Created:**
- data/{assembly}/genome.fasta
- data/{assembly}/genome_metadata.json
- data/{assembly}/literature_search.json

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Next:** Identify essential genes using orthology and literature evidence

Proceed to Step 2 (identify-genes)? [yes/no/adjust]
```

**WAIT FOR USER RESPONSE**

---

### Step 2: Identify Essential Genes

Read and execute: `dsrna_agent/skills/identify-genes/SKILL.md`

**Checkpoint Output:**
```
## ✅ Step 2 Complete: Identify Essential Genes

**Genes Analyzed:** {total} from genome
**Essential Genes Found:** {count} candidates

**Top 10 Candidates:**
| Rank | Gene | Function | Score | Literature Support |
|------|------|----------|-------|-------------------|
| 1 | {gene} | {function} | {score} | {papers} papers |
| ... | ... | ... | ... | ... |

**Evidence Sources:**
- Ortholog matches: {n}
- Literature support: {n} genes with published RNAi data

**Files Created:**
- data/{assembly}/essential_genes.json

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Next:** Design dsRNA candidates for top 5 genes

Proceed to Step 3 (design-dsrna)? [yes/no/adjust]
```

**WAIT FOR USER RESPONSE**

---

### Step 3: Design dsRNA Candidates

Read and execute: `dsrna_agent/skills/design-dsrna/SKILL.md`

Design candidates for top 5 genes (3 candidates each = 15 total)

**Checkpoint Output:**
```
## ✅ Step 3 Complete: Design dsRNA Candidates

**Genes Targeted:** 5 (top essential genes)
**Candidates Designed:** 15 (3 per gene)
**Target Length:** 300 bp

**Candidate Summary:**
| Gene | Candidate | Position | GC% | Design Score |
|------|-----------|----------|-----|--------------|
| {gene} | {gene}_1 | {start}-{end} | {gc}% | {score}/5 |
| ... | ... | ... | ... | ... |

**GC Content Distribution:** {min}% - {max}% (optimal: 35-50%)

**Files Created:**
- data/{assembly}/candidates.json

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Next:** Screen candidates for off-target matches (human, honeybee)

⚠️ This step requires BLAST databases. If not set up, run: ./setup_blast_db.sh

Proceed to Step 4 (blast-screen)? [yes/no/adjust]
```

**WAIT FOR USER RESPONSE**

---

### Step 4: BLAST Screening

Read and execute: `dsrna_agent/skills/blast-screen/SKILL.md`

**Checkpoint Output:**
```
## ✅ Step 4 Complete: Off-Target Screening

**Candidates Screened:** 15
**Databases:** Human (GRCh38), Honeybee (Amel_HAv3.1)

**Safety Results:**
| Status | Count | Threshold |
|--------|-------|-----------|
| ✅ Safe | {n} | <15 bp match |
| ⚠️ Caution | {n} | 15-18 bp match |
| ❌ Rejected | {n} | ≥19 bp match |

**Detailed Results:**
| Candidate | Human Max | Honeybee Max | Status |
|-----------|-----------|--------------|--------|
| {name} | {bp} bp | {bp} bp | {status} |
| ... | ... | ... | ... |

**Files Created:**
- data/{assembly}/blast_results.json

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Next:** Calculate final efficacy × safety scores

Proceed to Step 5 (score-rank)? [yes/no/adjust]
```

**WAIT FOR USER RESPONSE**

---

### Step 5: Score and Rank

Read and execute: `dsrna_agent/skills/score-rank/SKILL.md`

**Checkpoint Output:**
```
## ✅ Step 5 Complete: Score and Rank Candidates

**Scoring Formula:** Combined = Efficacy × Safety
- Efficacy: GC content (30%) + Position (20%) + No poly-N (20%) + Gene essentiality (30%)
- Safety: 1.0 (<15bp) | 0.7 (15-18bp) | 0.0 (≥19bp)

**Top 5 Candidates:**
| Rank | Candidate | Gene | Efficacy | Safety | Combined |
|------|-----------|------|----------|--------|----------|
| 1 | {name} | {gene} | {eff} | {safe} | {comb} |
| 2 | ... | ... | ... | ... | ... |
| ... | ... | ... | ... | ... | ... |

**Recommendation:** {top_candidate} targeting {gene} (score: {score})

**Files Updated:**
- data/{assembly}/candidates.json (with scores)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Next:** Generate comprehensive report

Proceed to Step 6 (generate-report)? [yes/no/adjust]
```

**WAIT FOR USER RESPONSE**

---

### Step 6: Generate Report

Read and execute: `dsrna_agent/skills/generate-report/SKILL.md`

**Final Output:**
```
## ✅ Workflow Complete: dsRNA Design for {species}

**Final Report Generated**

### Executive Summary
- **Target Species:** {species}
- **Top Recommendation:** {candidate} targeting {gene}
- **Combined Score:** {score}
- **Safety Status:** {status}

### Files Generated
- `data/{assembly}/report.md` - Full scientific report
- `data/{assembly}/candidates.json` - All candidates with scores
- `data/{assembly}/figures/` - Visualizations

### Quick Links
- [View Full Report](data/{assembly}/report.md)
- [Download Candidates JSON](data/{assembly}/candidates.json)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Workflow complete.** Would you like to:
- Review the full report?
- Export sequences for synthesis?
- Run additional analysis on specific candidates?
```

## Error Handling

If any step fails:
1. Report the error clearly
2. Suggest possible fixes
3. Ask if user wants to retry or skip

Example:
```
## ❌ Step 4 Failed: BLAST Screening

**Error:** BLAST database not found at data/blast_db/human_cds

**Solution:** Run the setup script:
\`\`\`bash
./setup_blast_db.sh
\`\`\`

Retry Step 4? [yes/skip/abort]
```

## User Adjustments

If user provides feedback at any checkpoint:
- "adjust" → Ask what they want to change
- "skip" → Move to next step (note in report)
- "go back" → Re-run previous step
- Specific feedback → Incorporate and re-run current step
