---
name: fetch-genome
description: Download CDS sequences from NCBI RefSeq for a target species
---

# Fetch Genome Skill

## When to Use This Skill

Use at the start of dsRNA design workflow when you need coding sequences (CDS)
for a pest species from NCBI.

## IMPORTANT: Check Cache First

Before downloading, always check if the genome data already exists:

```bash
ls data/*/genome_metadata.json 2>/dev/null | head -5
```

If you find a matching assembly for your species, **skip the download** and use
the existing data. Read the metadata to confirm it's the right species:

```bash
cat data/{assembly}/genome_metadata.json
```

## Instructions

### Step 1: Resolve Species to TaxID

Use `fetch_url` to query NCBI Taxonomy:

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=taxonomy&term={species}&retmode=json
```

Parse JSON response: `esearchresult.idlist[0]` is the TaxID

### Step 2: Find RefSeq Assembly

Use `fetch_url`:

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=assembly&term=txid{TAXID}[Organism:exp]+AND+latest_refseq[filter]&retmode=json
```

Get assembly ID from `esearchresult.idlist[0]`

### Step 3: Get Assembly Accession and FTP Path

Use `fetch_url`:

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=assembly&id={ASSEMBLY_ID}&retmode=json
```

Extract from response:
- Assembly accession: `result[assembly_id].assemblyaccession` (e.g., "GCF_000001215.4")
- FTP path: `result[assembly_id].ftppath_refseq`

### Step 4: Check if Already Downloaded

**CRITICAL:** Check if this assembly is already cached:

```bash
if [ -f "data/{ASSEMBLY_ACCESSION}/genome.fasta" ]; then
    echo "CACHED: Genome already exists"
else
    echo "NOT CACHED: Need to download"
fi
```

If cached, **skip to Step 8** (literature search).

### Step 5: Create Data Directory

```bash
mkdir -p data/{ASSEMBLY_ACCESSION}
mkdir -p data/{ASSEMBLY_ACCESSION}/figures
```

Use the assembly accession (e.g., "GCF_000001215.4") as the folder name.

### Step 6: Download CDS FASTA

Use `execute` to download:

```bash
FTP_PATH="https://ftp.ncbi.nlm.nih.gov/..."  # from step 3
ASSEMBLY_NAME=$(basename $FTP_PATH)
curl -L -o data/{ASSEMBLY_ACCESSION}/genome.fasta.gz \
  "${FTP_PATH}/${ASSEMBLY_NAME}_cds_from_genomic.fna.gz"
gunzip data/{ASSEMBLY_ACCESSION}/genome.fasta.gz
```

If `_cds_from_genomic.fna.gz` returns 404, try `_rna.fna.gz` instead.

### Step 7: Verify Download

Use `execute`:

```bash
grep -c "^>" data/{ASSEMBLY_ACCESSION}/genome.fasta
```

Should show thousands of sequences (typically 10,000-20,000 for insects)

### Step 8: Save Metadata

Use `write_file` to save `data/{ASSEMBLY_ACCESSION}/genome_metadata.json`:

```json
{
  "species": "{species_name}",
  "taxid": "{TAXID}",
  "assembly_id": "{ASSEMBLY_ID}",
  "assembly_accession": "{ASSEMBLY_ACCESSION}",
  "ftp_path": "{FTP_PATH}",
  "download_date": "{ISO_DATE}",
  "sequence_count": {COUNT},
  "total_length": {LENGTH}
}
```

### Step 9: Search Literature (Automatic)

Automatically search PubMed for RNAi studies on this species:
```
pubmed_search_articles
query: "{species}" AND (RNAi OR dsRNA OR "RNA interference" OR "gene silencing")
max_results: 50
```

Save results to `data/{ASSEMBLY_ACCESSION}/literature_search.json`.

**This step does NOT require user confirmation** - literature search is automatic.

### Step 10: Present Results

Output this summary to the user:

```
## Fetch Genome Complete

**Species:** {species_name} (TaxID: {taxid})
**Assembly:** {assembly_accession}
**Status:** {DOWNLOADED or CACHED}

**Summary:**
- {sequence_count} CDS sequences
- Total length: {total_length} bp

**Literature:** Found {paper_count} RNAi papers, top genes: {gene_list}

**Data Location:**
- `data/{assembly_accession}/genome.fasta`
- `data/{assembly_accession}/genome_metadata.json`
- `data/{assembly_accession}/literature_search.json`

---
Proceed to identify-genes? (yes/no)
```

## Expected Output

- `data/{assembly}/genome.fasta` - Downloaded CDS sequences
- `data/{assembly}/genome_metadata.json` - TaxID, assembly ID, stats
- `data/{assembly}/literature_search.json` - PubMed search results

## Available Tools

- `fetch_url` - Query NCBI APIs
- `execute` - Run curl/gunzip commands
- `write_file` - Save metadata
- `pubmed_search_articles` - Search literature
