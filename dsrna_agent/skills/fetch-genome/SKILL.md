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

```bash
mkdir -p output/{species_slug}
mkdir -p output/{species_slug}/figures
```

Use lowercase with underscores (e.g., "drosophila_suzukii")

### Step 2: Resolve Species to TaxID

Use `fetch_url` to query NCBI Taxonomy:

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=taxonomy&term={species}&retmode=json
```

Parse JSON response: `esearchresult.idlist[0]` is the TaxID

### Step 3: Find RefSeq Assembly

Use `fetch_url`:

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=assembly&term=txid{TAXID}[Organism:exp]+AND+latest_refseq[filter]&retmode=json
```

Get assembly ID from `esearchresult.idlist[0]`

### Step 4: Get FTP Path

Use `fetch_url`:

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=assembly&id={ASSEMBLY_ID}&retmode=json
```

Extract FTP path from `result[assembly_id].ftppath_refseq`

### Step 5: Download CDS FASTA

Use `shell` to download (faster for large files):

```bash
FTP_PATH="https://ftp.ncbi.nlm.nih.gov/..."  # from step 4
ASSEMBLY_NAME=$(basename $FTP_PATH)
curl -L -o output/{species_slug}/genome.fasta.gz \
  "${FTP_PATH}/${ASSEMBLY_NAME}_cds_from_genomic.fna.gz"
gunzip output/{species_slug}/genome.fasta.gz
```

If `_cds_from_genomic.fna.gz` returns 404, try `_rna.fna.gz` instead.

### Step 6: Verify Download

Use `shell`:

```bash
grep -c "^>" output/{species_slug}/genome.fasta
```

Should show thousands of sequences (typically 10,000-20,000 for insects)

### Step 7: Generate Visualization

Create `output/{species_slug}/figures/` directory and generate GC content analysis:

```bash
python .deepagents/skills/fetch-genome/scripts/plot_genome_stats.py \
  --genome output/{species_slug}/genome.fasta \
  --output-dir output/{species_slug}/figures/
```

This creates:
- `genome_gc_distribution.png` - Histogram of GC content across all CDS
- `genome_length_distribution.png` - CDS length distribution
- `genome_stats.json` - Summary statistics

### Step 8: Save Metadata

Use `write_file` to save `output/{species_slug}/genome_metadata.json`:

```json
{
  "species": "{species_name}",
  "taxid": "{TAXID}",
  "assembly_id": "{ASSEMBLY_ID}",
  "assembly_name": "{ASSEMBLY_NAME}",
  "ftp_path": "{FTP_PATH}",
  "download_date": "{ISO_DATE}",
  "sequence_count": {COUNT},
  "total_length": {LENGTH}
}
```

### Step 9: Search Literature (Automatic)

Automatically search PubMed for RNAi studies on this species:
```
mcp__plugin_pubmed_PubMed__search_articles
query: "{species}" AND (RNAi OR dsRNA OR "RNA interference" OR "gene silencing")
max_results: 50
```

Save results to `output/{species_slug}/literature_search.json`.

**This step does NOT require user confirmation** - literature search is automatic.

### Step 10: Present Results

Output this summary to the user:

```
## Fetch Genome Complete

**Species:** {species_name} (TaxID: {taxid})
**Assembly:** {assembly_name}

**Summary:**
- {sequence_count} CDS sequences downloaded
- Total length: {total_length} bp
- Average GC content: {avg_gc}%

**Literature:** Found {paper_count} RNAi papers, top genes: {gene_list}

**Files Created:**
- `output/{species_slug}/genome.fasta`
- `output/{species_slug}/genome_metadata.json`
- `output/{species_slug}/literature_search.json`

**Figures:** [Show GC distribution plot]

---
Proceed to identify-genes? (yes/no)
```

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
