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

Use the PubMed MCP tools (loaded from `https://pubmed.mcp.claude.com/mcp`).

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

### Step 3: Extract Gene Information

From article titles and abstracts, identify mentioned genes. Look for:

| Gene Family | Pattern Matches |
|-------------|-----------------|
| V-ATPase | V-ATPase, vATPase, vha, ATP6V, vacuolar ATPase |
| Chitin synthase | chitin synthase, ChS, CHS |
| Acetylcholinesterase | acetylcholinesterase, AChE, Ace |
| Tubulin | alpha-tubulin, beta-tubulin, tubulin |
| Ribosomal | ribosomal protein, RpS, RpL, Rps, Rpl |
| Cytochrome P450 | cytochrome P450, CYP, P450 |
| Ecdysone receptor | ecdysone receptor, EcR |
| Other targets | trehalase, laccase, aquaporin, snf7, COPI |

### Step 4: Save Results

Write findings to `output/{species_slug}/literature_search.json`:

```json
[
  {
    "pmid": "12345678",
    "doi": "10.1234/example",
    "title": "RNAi silencing of vATPase in Drosophila suzukii...",
    "authors": ["Smith J", "Jones K"],
    "journal": "Journal of Insect Physiology",
    "year": "2020",
    "gene_names": ["vATPase", "chitin synthase"],
    "abstract_snippet": "We demonstrate effective gene silencing...",
    "relevance": "Direct RNAi study in target species"
  }
]
```

### Step 5: Generate Visualization (Optional)

If accumulating results across multiple searches:

```bash
python .deepagents/skills/literature-search/scripts/plot_literature.py \
  --literature output/{species_slug}/literature_search.json \
  --output-dir output/{species_slug}/figures/
```

Creates:
- `literature_gene_frequency.png` - Bar chart of gene mentions
- `literature_summary.txt` - Key findings summary

## Usage Patterns

### Pattern A: Initial Species Survey
Call early to understand what genes have been studied for the target species.

### Pattern B: Gene Validation
Call when evaluating specific genes to find supporting literature.

### Pattern C: Report Enrichment
Call before generating report to ensure all candidates have literature support.

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
