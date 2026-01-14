# dsRNA Designer - Implementation Tasks

> Generated from `docs/implementation-plan-v3.md`

---

## Phase 1: Project Structure Setup

### 1.1 Create Directory Structure

- [x] **Task 1.1.1**: Create `.deepagents/` root directory ✅
- [x] **Task 1.1.2**: Create `.deepagents/skills/` directory ✅
- [x] **Task 1.1.3**: Create all 7 skill directories with `scripts/` subdirectories: ✅
  ```
  .deepagents/skills/
  ├── fetch-genome/scripts/
  ├── literature-search/scripts/
  ├── identify-genes/scripts/
  ├── design-dsrna/scripts/
  ├── blast-screen/scripts/
  ├── score-rank/scripts/
  └── generate-report/scripts/
  ```
- [x] **Task 1.1.4**: Create `references/` subdirectories for: ✅
  - `.deepagents/skills/blast-screen/references/`
  - `.deepagents/skills/generate-report/references/`

### 1.2 Project Agent Configuration

- [x] **Task 1.2.1**: Write `.deepagents/agent.md` containing: ✅
  - Agent identity and purpose
  - Core workflow (6 steps, one at a time) + literature-search as utility skill
  - Interaction protocol (execute → visualize → summarize → checkpoint → wait)
  - Visualization requirements per skill
  - Safety rules (EPA thresholds: <15bp safe, 15-18bp caution, ≥19bp reject)
  - Output structure (`output/{species_slug}/` and `output/{species_slug}/figures/`)
  - PubMed MCP server integration

---

## Phase 2: SKILL.md Files

### 2.1 fetch-genome Skill

- [x] **Task 2.1.1**: Write `.deepagents/skills/fetch-genome/SKILL.md` ✅ (Updated)
  - YAML frontmatter: `name: fetch-genome`, `description: Download CDS sequences from NCBI RefSeq`
  - Instructions for: TaxID lookup, assembly search, FTP path extraction, CDS download
  - Checkpoint: "Ready to proceed to identify-genes? (yes/no)"
  - Note about literature-search utility skill available anytime

### 2.2 literature-search Skill (Utility)

- [x] **Task 2.2.1**: Write `.deepagents/skills/literature-search/SKILL.md` ✅ (Updated)
  - YAML frontmatter: `name: literature-search`, `type: utility`
  - Uses PubMed MCP server at `https://pubmed.mcp.claude.com/mcp`
  - Available tools: `search_articles`, `get_article_metadata`, `find_related_articles`, `get_full_text_article`
  - Gene patterns to match: vATPase, chitin synthase, AChE, tubulin, actin, RpS/RpL, CYP, EcR, trehalase
  - **Utility skill** - no checkpoint, can be invoked at any workflow step

### 2.3 identify-genes Skill

- [x] **Task 2.3.1**: Write `.deepagents/skills/identify-genes/SKILL.md` ✅ (Updated)
  - YAML frontmatter: `name: identify-genes`, `description: Match essential genes using orthology and literature`
  - Scoring logic: 0.5 base + 0.3 literature (optional) + 0.05×species (max 0.2)
  - Output: Top 20 genes with sequences
  - Checkpoint: "Ready to proceed to design-dsrna for top 5 genes? (yes/no)"
  - Note: `--literature` flag is optional (boost scores if literature-search was run)

### 2.4 design-dsrna Skill

- [x] **Task 2.4.1**: Write `.deepagents/skills/design-dsrna/SKILL.md` ✅
  - YAML frontmatter: `name: design-dsrna`, `description: Design dsRNA candidates using sliding window`
  - Parameters: 300bp length, 3 candidates per gene, top 5 genes = 15 total
  - Scoring criteria: GC 35-50% (+2), GC 30-55% (+1), no poly-N (+1), position (+2)
  - Checkpoint: "Ready to proceed to blast-screen? (yes/no)"

### 2.5 blast-screen Skill

- [x] **Task 2.5.1**: Write `.deepagents/skills/blast-screen/SKILL.md` ✅
  - YAML frontmatter: `name: blast-screen`, `description: Screen candidates for off-target matches`
  - Prerequisites: BLAST+ installed, human_cds and honeybee_cds databases
  - Safety thresholds: <15bp safe, 15-18bp caution, ≥19bp reject
  - Checkpoint: "Ready to proceed to score-rank? (yes/no)"

- [x] **Task 2.5.2**: Write `.deepagents/skills/blast-screen/references/safety_thresholds.md` ✅
  - EPA guidelines documentation
  - Threshold rationale and references

### 2.6 score-rank Skill

- [x] **Task 2.6.1**: Write `.deepagents/skills/score-rank/SKILL.md` ✅
  - YAML frontmatter: `name: score-rank`, `description: Calculate final scores combining efficacy and safety`
  - Efficacy formula: 0.3×GC + 0.2×poly_n + 0.2×position + 0.3×gene_score
  - Safety formula: 1.0 (<15bp), 0.7 (15-18bp), 0.0 (≥19bp)
  - Combined: efficacy × safety
  - Checkpoint: "Ready to proceed to generate-report? (yes/no)"

### 2.7 generate-report Skill

- [x] **Task 2.7.1**: Write `.deepagents/skills/generate-report/SKILL.md` ✅ (Updated)
  - YAML frontmatter: `name: generate-report`, `description: Generate comprehensive markdown report`
  - Report sections: Executive Summary, Top Candidates, Detailed Analysis, Safety, Genes, Literature (if available), Recommendations
  - Final output: `report.md` + `summary_dashboard.png`
  - Note: Can invoke literature-search utility to enrich references before generating

- [x] **Task 2.7.2**: Write `.deepagents/skills/generate-report/references/report_template.md` ✅
  - Full markdown template with placeholders
  - Table formats for candidates, safety, genes

---

## Phase 3: Helper Scripts (Data Processing)

### 3.1 literature-search Helper

- [x] **Task 3.1.1**: Write `.deepagents/skills/literature-search/scripts/parse_pubmed.py` ✅
  - Input: PubMed XML file
  - Output: JSON with PMIDs, titles, gene_names, abstract_snippets
  - Gene pattern regex matching (case-insensitive)
  - Dependencies: `xml.etree.ElementTree`, `json`, `re`, `argparse`

### 3.2 identify-genes Helper

- [x] **Task 3.2.1**: Write `.deepagents/skills/identify-genes/scripts/match_essential.py` ✅
  - Input: genome FASTA, essential_genes.json, literature_search.json
  - Output: Top 20 matched genes with scores and sequences
  - Dependencies: `biopython`, `json`, `argparse`

### 3.3 design-dsrna Helper

- [x] **Task 3.3.1**: Write `.deepagents/skills/design-dsrna/scripts/sliding_window.py` ✅
  - Input: Gene JSON with sequence
  - Output: 3 non-overlapping candidates per gene
  - Sliding window with 50bp step
  - Scoring: GC content, poly-N runs, position
  - Dependencies: `json`, `re`, `argparse`

### 3.4 blast-screen Helper

- [x] **Task 3.4.1**: Write `.deepagents/skills/blast-screen/scripts/run_blast.py` ✅
  - Input: candidates.json, blast_db directory
  - Output: blast_results.json with max match lengths and safety status
  - BLAST parameters: word_size=7, outfmt="6 qseqid sseqid length", evalue=10
  - Dependencies: `subprocess`, `json`, `tempfile`, `pathlib`, `argparse`

### 3.5 score-rank Helper

- [x] **Task 3.5.1**: Write `.deepagents/skills/score-rank/scripts/calculate_scores.py` ✅
  - Input: candidates.json, blast_results.json, essential_genes.json
  - Output: ranked_candidates.json sorted by combined_score
  - Implements efficacy × safety formula
  - Dependencies: `json`, `argparse`

---

## Phase 4: Plotting Scripts (Visualization)

### 4.1 fetch-genome Plots

- [x] **Task 4.1.1**: Write `.deepagents/skills/fetch-genome/scripts/plot_genome_stats.py` ✅
  - Input: genome.fasta
  - Outputs:
    - `genome_gc_distribution.png` - GC content histogram with mean line
    - `genome_length_distribution.png` - CDS length histogram
    - `genome_stats.json` - Summary statistics
  - Dependencies: `matplotlib`, `seaborn`, `biopython`, `numpy`

### 4.2 literature-search Plots

- [x] **Task 4.2.1**: Write `.deepagents/skills/literature-search/scripts/plot_literature.py` ✅
  - Input: literature_search.json
  - Outputs:
    - `literature_gene_frequency.png` - Horizontal bar chart of gene mentions
    - `literature_summary.txt` - Key findings text
  - Dependencies: `matplotlib`, `json`, `collections`

### 4.3 identify-genes Plots

- [x] **Task 4.3.1**: Write `.deepagents/skills/identify-genes/scripts/plot_genes.py` ✅
  - Input: essential_genes.json
  - Outputs:
    - `gene_ranking.png` - Horizontal bar chart of top 10 genes with scores
    - `gene_evidence_breakdown.png` - Stacked bar (orthology vs literature)
    - `gene_length_distribution.png` - CDS lengths for identified genes
  - Dependencies: `matplotlib`, `seaborn`, `pandas`

### 4.4 design-dsrna Plots

- [x] **Task 4.4.1**: Write `.deepagents/skills/design-dsrna/scripts/plot_candidates.py` ✅
  - Input: candidates.json, essential_genes.json
  - Outputs:
    - `candidate_locations.png` - Genomic positions per gene
    - `candidate_gc_distribution.png` - GC content histogram
    - `candidate_scores_heatmap.png` - Design score components
  - Dependencies: `matplotlib`, `seaborn`, `pandas`

### 4.5 blast-screen Plots

- [x] **Task 4.5.1**: Write `.deepagents/skills/blast-screen/scripts/plot_safety.py` ✅
  - Input: blast_results.json, candidates.json
  - Outputs:
    - `safety_heatmap.png` - Candidates × species match lengths
    - `safety_distribution.png` - Match length histogram with thresholds
    - `safety_by_gene.png` - Grouped bar of safety status per gene
  - Dependencies: `matplotlib`, `seaborn`, `pandas`

### 4.6 score-rank Plots

- [x] **Task 4.6.1**: Write `.deepagents/skills/score-rank/scripts/plot_rankings.py` ✅
  - Input: ranked_candidates.json
  - Outputs:
    - `score_breakdown.png` - Stacked bar of efficacy/safety components
    - `efficacy_vs_safety_scatter.png` - Scatter plot with labels
    - `top_candidates_radar.png` - Radar chart for top 5
  - Dependencies: `matplotlib`, `seaborn`, `pandas`, `numpy`

### 4.7 generate-report Plots

- [x] **Task 4.7.1**: Write `.deepagents/skills/generate-report/scripts/create_dashboard.py` ✅
  - Input: All JSON files from output directory
  - Output: `summary_dashboard.png` - Multi-panel summary
    - Top 3 candidates with scores
    - Safety statistics pie chart
    - Gene essentiality scores
    - Workflow completion checklist
  - Dependencies: `matplotlib`, `json`, `pathlib`

---

## Phase 5: Data Files

### 5.1 Essential Genes Database

- [x] **Task 5.1.1**: Create/populate `data/essential_genes.json` ✅
  - Structure:
    ```json
    {
      "genes": [
        {
          "name": "vATPase",
          "aliases": ["V-ATPase", "vha", "ATP6V"],
          "function": "Vacuolar proton pump",
          "essential_in": ["D. melanogaster", "T. castaneum"],
          "references": ["PMID:12345678"]
        }
      ]
    }
    ```
  - Include ~30-50 known essential insect genes (50 genes included)

### 5.2 BLAST Databases

- [ ] **Task 5.2.1**: Verify/update `setup_blast_db.sh` script
  - Downloads human CDS from NCBI
  - Downloads honeybee CDS from NCBI
  - Runs `makeblastdb` for both

- [ ] **Task 5.2.2**: Run `setup_blast_db.sh` to create:
  - `data/blast_db/human_cds.*`
  - `data/blast_db/honeybee_cds.*`

---

## Phase 6: Dependencies & Configuration

### 6.1 Update pyproject.toml

- [x] **Task 6.1.1**: Add visualization dependencies: ✅
  ```toml
  dependencies = [
      "biopython>=1.84",
      "python-dotenv>=1.2.1",
      "matplotlib>=3.8.0",
      "seaborn>=0.13.0",
      "pandas>=2.1.0",
      "numpy>=1.26.0",
  ]
  ```

### 6.2 Install Dependencies

- [x] **Task 6.2.1**: Run `uv sync` to install all dependencies ✅
- [ ] **Task 6.2.2**: Verify BLAST+ installation: `blastn -version`

---

## Phase 7: Testing

### 7.1 Unit Tests

- [x] **Task 7.1.1**: Test `parse_pubmed.py` with sample XML ✅
- [x] **Task 7.1.2**: Test `match_essential.py` with sample FASTA ✅
- [x] **Task 7.1.3**: Test `sliding_window.py` with sample gene ✅
- [x] **Task 7.1.4**: Test `run_blast.py` with sample candidates ✅ (mocked - needs BLAST DB)
- [x] **Task 7.1.5**: Test `calculate_scores.py` with sample data ✅
- [x] **Task 7.1.6**: Test all plotting scripts with sample inputs ✅

### 7.2 Integration Tests

- [ ] **Task 7.2.1**: Test fetch-genome with Drosophila suzukii (TaxID: 28584)
- [ ] **Task 7.2.2**: Test literature-search with PubMed API
- [ ] **Task 7.2.3**: Test full pipeline: genome → literature → genes → candidates → blast → rank → report

### 7.3 End-to-End Test

- [ ] **Task 7.3.1**: Run complete workflow for Drosophila suzukii
- [ ] **Task 7.3.2**: Verify all 7 checkpoints trigger correctly
- [ ] **Task 7.3.3**: Verify all visualizations generate without errors
- [ ] **Task 7.3.4**: Verify `report.md` is complete and scientifically accurate

---

## Phase 8: Validation & Documentation

### 8.1 Output Validation

- [ ] **Task 8.1.1**: Verify all expected files exist in `output/{species_slug}/`:
  - `genome.fasta`
  - `genome_metadata.json`
  - `literature_search.json`
  - `essential_genes.json`
  - `candidates.json`
  - `blast_results.json`
  - `ranked_candidates.json`
  - `report.md`

- [ ] **Task 8.1.2**: Verify all figures exist in `output/{species_slug}/figures/`:
  - `genome_gc_distribution.png`
  - `genome_length_distribution.png`
  - `literature_gene_frequency.png`
  - `gene_ranking.png`
  - `gene_evidence_breakdown.png`
  - `candidate_locations.png`
  - `candidate_gc_distribution.png`
  - `safety_heatmap.png`
  - `safety_distribution.png`
  - `score_breakdown.png`
  - `efficacy_vs_safety_scatter.png`
  - `summary_dashboard.png`

### 8.2 Scientific Validation

- [ ] **Task 8.2.1**: Compare identified genes against published RNAi studies
- [ ] **Task 8.2.2**: Verify safety thresholds match EPA guidelines
- [ ] **Task 8.2.3**: Validate top candidates have supporting literature

### 8.3 Documentation

- [ ] **Task 8.3.1**: Update `README.md` with:
  - Installation instructions
  - Usage examples
  - Checkpoint workflow explanation
  - Output file descriptions

- [ ] **Task 8.3.2**: Add example output screenshots to docs/

---

## Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| 1. Project Structure | 5 tasks | ✅ Complete |
| 2. SKILL.md Files | 9 tasks | ✅ Complete |
| 3. Helper Scripts | 5 tasks | ✅ Complete |
| 4. Plotting Scripts | 7 tasks | ✅ Complete |
| 5. Data Files | 3 tasks | 🟡 Partial (1/3) |
| 6. Dependencies | 3 tasks | 🟡 Partial (2/3) |
| 7. Testing | 10 tasks | 🟡 Partial (6/10) |
| 8. Validation | 6 tasks | ⬜ Not started |
| **Total** | **48 tasks** | **38 complete** |

---

## Recommended Implementation Order

1. **Phase 1** → Project structure (foundation)
2. **Phase 6** → Dependencies (needed for scripts)
3. **Phase 5.1** → Essential genes database (needed for testing)
4. **Phase 2** → All SKILL.md files (workflow definition)
5. **Phase 3** → Helper scripts (core logic)
6. **Phase 4** → Plotting scripts (visualization)
7. **Phase 5.2** → BLAST databases (safety screening)
8. **Phase 7** → Testing (validation)
9. **Phase 8** → Final validation and docs
