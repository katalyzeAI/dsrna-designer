#!/usr/bin/env python3
"""Parse PubMed XML and extract gene names relevant to RNAi research."""

import xml.etree.ElementTree as ET
import json
import re
import argparse
from collections import Counter
from pathlib import Path

# Gene patterns commonly targeted in insect RNAi studies
GENE_PATTERNS = [
    # Housekeeping/essential genes
    (r'\b(v-?ATPase|vha\d*|ATP6V\w*|vacuolar.{0,10}ATPase)\b', 'vATPase'),
    (r'\b(chitin\s*synthase|ChS\d?|CHS\d?)\b', 'chitin synthase'),
    (r'\b(acetylcholinesterase|AChE|Ace\d?)\b', 'acetylcholinesterase'),
    (r'\b(α-?tubulin|alpha.?tubulin|TUA\d?)\b', 'alpha-tubulin'),
    (r'\b(β-?tubulin|beta.?tubulin|TUB\d?)\b', 'beta-tubulin'),
    (r'\b(actin|ACT\d?|act\d+)\b', 'actin'),

    # Ribosomal proteins
    (r'\b(ribosomal\s*protein|RpS\d+|RpL\d+|Rps\d+|Rpl\d+)\b', 'ribosomal protein'),

    # Cytochrome P450s
    (r'\b(cytochrome\s*P450|CYP\d+\w*|P450)\b', 'cytochrome P450'),

    # Hormone receptors
    (r'\b(ecdysone\s*receptor|EcR)\b', 'ecdysone receptor'),
    (r'\b(juvenile\s*hormone|JH\w*)\b', 'juvenile hormone'),

    # Metabolic enzymes
    (r'\b(trehalase|TRE\d?)\b', 'trehalase'),
    (r'\b(laccase|Lac\d?)\b', 'laccase'),
    (r'\b(aquaporin|AQP\d?)\b', 'aquaporin'),
    (r'\b(glutathione\s*S-?transferase|GST\w*)\b', 'glutathione S-transferase'),

    # Cuticle proteins
    (r'\b(cuticle\s*protein|CP\d+|cuticular)\b', 'cuticle protein'),

    # Ion channels
    (r'\b(sodium\s*channel|Nav\d*|para)\b', 'sodium channel'),
    (r'\b(GABA\s*receptor|Rdl|GABAR)\b', 'GABA receptor'),

    # Other targets
    (r'\b(heat\s*shock\s*protein|HSP\d+|Hsp\d+)\b', 'heat shock protein'),
    (r'\b(superoxide\s*dismutase|SOD\d?)\b', 'superoxide dismutase'),
    (r'\b(catalase|CAT)\b', 'catalase'),
    (r'\b(hexamerin|HEX\d?)\b', 'hexamerin'),
]


def extract_genes_from_text(text: str) -> list[str]:
    """Extract gene names from text using pattern matching."""
    if not text:
        return []

    found_genes = []
    for pattern, canonical_name in GENE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            found_genes.append(canonical_name)

    return list(set(found_genes))


def parse_pubmed_xml(xml_path: str) -> list[dict]:
    """Parse PubMed XML and extract article info with gene mentions."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return []

    results = []

    # Handle both PubmedArticleSet and direct article responses
    articles = root.findall('.//PubmedArticle')
    if not articles:
        articles = root.findall('.//Article')

    for article in articles:
        # Extract PMID
        pmid_elem = article.find('.//PMID')
        pmid = pmid_elem.text if pmid_elem is not None else ''

        # Extract title
        title_elem = article.find('.//ArticleTitle')
        title = ''.join(title_elem.itertext()) if title_elem is not None else ''

        # Extract abstract (may have multiple AbstractText elements)
        abstract_parts = []
        for abstract_elem in article.findall('.//AbstractText'):
            if abstract_elem.text:
                abstract_parts.append(abstract_elem.text)
        abstract = ' '.join(abstract_parts)

        # Extract year
        year_elem = article.find('.//PubDate/Year')
        if year_elem is None:
            year_elem = article.find('.//DateCompleted/Year')
        year = year_elem.text if year_elem is not None else ''

        # Extract authors
        authors = []
        for author in article.findall('.//Author'):
            lastname = author.find('LastName')
            if lastname is not None and lastname.text:
                authors.append(lastname.text)

        # Find gene mentions
        full_text = f"{title} {abstract}"
        gene_names = extract_genes_from_text(full_text)

        # Create snippet
        snippet = abstract[:500] + '...' if len(abstract) > 500 else abstract

        results.append({
            'pmid': pmid,
            'title': title,
            'year': year,
            'authors': authors[:3],  # First 3 authors
            'gene_names': gene_names,
            'abstract_snippet': snippet
        })

    return results


def summarize_results(results: list[dict]) -> dict:
    """Generate summary statistics from parsed results."""
    all_genes = []
    for r in results:
        all_genes.extend(r.get('gene_names', []))

    gene_counts = Counter(all_genes)

    return {
        'total_papers': len(results),
        'papers_with_genes': sum(1 for r in results if r.get('gene_names')),
        'unique_genes': len(gene_counts),
        'gene_frequency': dict(gene_counts.most_common(20)),
        'top_genes': [g for g, _ in gene_counts.most_common(10)]
    }


def main():
    parser = argparse.ArgumentParser(
        description='Parse PubMed XML and extract gene names'
    )
    parser.add_argument('--xml-file', required=True,
                        help='Path to PubMed XML file')
    parser.add_argument('--output', required=True,
                        help='Output JSON file path')
    args = parser.parse_args()

    # Parse XML
    results = parse_pubmed_xml(args.xml_file)

    # Add summary
    summary = summarize_results(results)

    output_data = {
        'summary': summary,
        'papers': results
    }

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)

    # Print summary
    print(f"✓ Parsed {summary['total_papers']} papers")
    print(f"  - Papers with gene mentions: {summary['papers_with_genes']}")
    print(f"  - Unique genes found: {summary['unique_genes']}")
    if summary['top_genes']:
        print(f"  - Top genes: {', '.join(summary['top_genes'][:5])}")


if __name__ == '__main__':
    main()
