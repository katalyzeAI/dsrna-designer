---
name: literature-search
description: Search PubMed for RNAi/dsRNA research on target genes or species (utility skill - use anytime)
type: utility
---

# Literature Search Skill

## When to Use This Skill

This is a **utility skill** - use it at ANY point in the workflow when you need:
- Published RNAi/dsRNA studies for a pest species
- Evidence supporting gene essentiality
- Validation of candidate gene targets
- References for the final report

## IMPORTANT: Tool Selection

**ALWAYS use PubMed MCP tools for literature searches. DO NOT use WebSearch/Tavily.**

| Correct | Incorrect |
|---------|-----------|
| `pubmed_search_articles` | `WebSearch` |
| `pubmed_get_article_metadata` | `WebFetch` on Google Scholar |

PubMed provides peer-reviewed, citable scientific literature with structured metadata
(PMIDs, DOIs, abstracts). Web search returns unstructured, potentially unreliable results.

## Instructions

### Step 1: Search PubMed Using MCP Server

Use the PubMed MCP tools.

**For species-wide RNAi research:**
```
pubmed_search_articles
query: "{species}" AND (RNAi OR dsRNA OR "RNA interference" OR "gene silencing")
max_results: 50
```

**For specific gene targets:**
```
pubmed_search_articles
query: "{gene_name}" AND (RNAi OR dsRNA) AND insect
max_results: 20
```

### Step 2: Get Article Details

For relevant PMIDs, fetch full metadata:
```
pubmed_get_article_metadata
pmids: ["PMID1", "PMID2", ...]
```

### Step 3: Extract Gene Names (CRITICAL)

**You MUST extract gene names from each paper's title and abstract.**

The `match_essential.py` script relies on the `gene_names` field to give literature
support scores to candidate genes. If this field is empty or missing, literature
support will be ignored.

Look for these gene patterns in titles and abstracts:

| Gene | Patterns to Match |
|------|-------------------|
| vATPase | V-ATPase, vATPase, vha, ATP6V, vacuolar ATPase |
| chitin synthase | chitin synthase, ChS, CHS |
| acetylcholinesterase | acetylcholinesterase, AChE, Ace |
| alpha-tubulin | α-tubulin, alpha-tubulin, TUA |
| beta-tubulin | β-tubulin, beta-tubulin, TUB |
| ribosomal protein | ribosomal protein, RpS, RpL |
| cytochrome P450 | cytochrome P450, CYP, P450 |
| ecdysone receptor | ecdysone receptor, EcR |
| trehalase | trehalase, TRE |
| laccase | laccase, Lac |
| aquaporin | aquaporin, AQP |
| heat shock protein | heat shock protein, HSP, Hsp |
| actin | actin, ACT |
| GABA receptor | GABA receptor, Rdl, GABAR |
| sodium channel | sodium channel, Nav, para |

### Step 4: Save Results in Required Format

**Analysis outputs go in `output/{run}/`, NOT in `data/`.**

Write to `output/{run}/literature_search.json`:

**REQUIRED FORMAT:**
```json
[
  {
    "pmid": "12345678",
    "doi": "10.1234/example",
    "title": "RNAi silencing of vATPase in Drosophila suzukii causes mortality",
    "authors": ["Smith J", "Jones K"],
    "journal": "Journal of Insect Physiology",
    "year": "2020",
    "gene_names": ["vATPase"],
    "abstract_snippet": "We demonstrate effective gene silencing..."
  },
  {
    "pmid": "12345679",
    "title": "Chitin synthase and acetylcholinesterase as RNAi targets",
    "gene_names": ["chitin synthase", "acetylcholinesterase"],
    ...
  }
]
```

**CRITICAL FIELDS:**
- `gene_names` - **REQUIRED** - Array of gene names found in title/abstract
- `pmid` - PubMed ID
- `title` - Article title

The downstream script `match_essential.py` checks `paper.get('gene_names', [])`
for each paper. If `gene_names` is missing or empty, that paper won't contribute
to literature support scores.

### Step 5: Verify Format

After saving, verify the format is correct:

```bash
jq '.[0:2] | .[] | {pmid, gene_names}' output/{run}/literature_search.json
```

Should show each paper with its extracted gene_names array.

## Alternative: Use parse_pubmed.py Script

If you have raw PubMed XML, you can use the bundled script to extract genes:

```bash
python dsrna_agent/skills/literature-search/scripts/parse_pubmed.py \
  --xml-file /tmp/pubmed_results.xml \
  --output output/{run}/literature_search.json
```

This automatically extracts gene names using pattern matching.

## Available MCP Tools

| Tool | Purpose |
|------|---------|
| `pubmed_search_articles` | Search PubMed with query |
| `pubmed_get_article_metadata` | Get full article details by PMID |
| `pubmed_find_related_articles` | Find similar papers |
| `pubmed_get_full_text_article` | Get PMC full text (if available) |

## Notes

- Always cite PubMed and include DOIs when reporting findings
- If no results for exact species, try related species or genus-level queries
- Gene mentions from literature boost candidate scores in the scoring step
- **This skill runs AUTONOMOUSLY - no user confirmation needed**
- Do NOT ask "Would you like me to search PubMed?" - just search when relevant
- Integrate results silently and continue with the workflow
