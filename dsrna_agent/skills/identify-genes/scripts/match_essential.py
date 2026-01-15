#!/usr/bin/env python3
"""Match essential genes against target genome sequences."""

import json
import argparse
import re
from pathlib import Path
from Bio import SeqIO


def load_essential_genes(db_path: str) -> list[dict]:
    """Load essential genes database."""
    with open(db_path) as f:
        data = json.load(f)
    return data.get('genes', [])


def load_literature_genes(lit_path: str) -> set[str]:
    """Extract gene names from literature search results."""
    if not lit_path or not Path(lit_path).exists():
        return set()

    with open(lit_path) as f:
        data = json.load(f)

    genes = set()

    # Handle both formats (list of papers or dict with 'papers' key)
    papers = data.get('papers', data) if isinstance(data, dict) else data

    for paper in papers:
        for gene in paper.get('gene_names', []):
            genes.add(gene.lower())

    return genes


def match_gene_to_sequence(gene: dict, seq_description: str) -> bool:
    """Check if a gene matches a sequence description."""
    desc_lower = seq_description.lower()

    # Check main gene name
    gene_name = gene['name'].lower()
    if gene_name in desc_lower:
        return True

    # Check without hyphens/spaces
    gene_name_clean = re.sub(r'[-\s]', '', gene_name)
    desc_clean = re.sub(r'[-\s]', '', desc_lower)
    if gene_name_clean in desc_clean:
        return True

    # Check aliases
    for alias in gene.get('aliases', []):
        alias_lower = alias.lower()
        if alias_lower in desc_lower:
            return True
        # Check cleaned version
        alias_clean = re.sub(r'[-\s]', '', alias_lower)
        if alias_clean in desc_clean:
            return True

    return False


def calculate_score(gene: dict, literature_genes: set[str]) -> float:
    """Calculate essentiality score for a gene match."""
    score = 0.5  # Base score for ortholog match

    # Literature support (+0.3)
    gene_names = [gene['name'].lower()] + [a.lower() for a in gene.get('aliases', [])]
    if any(name in literature_genes for name in gene_names):
        score += 0.3

    # Essential in multiple species (+0.05 per species, max +0.2)
    essential_count = len(gene.get('essential_in', []))
    score += min(0.2, essential_count * 0.05)

    return round(score, 2)


def match_essential_genes(
    genome_path: str,
    essential_db_path: str,
    literature_path: str | None,
    output_path: str,
    max_results: int = 20
) -> None:
    """Match essential genes against genome and output ranked results."""

    # Load data
    essential_genes = load_essential_genes(essential_db_path)
    literature_genes = load_literature_genes(literature_path) if literature_path else set()

    print(f"Loaded {len(essential_genes)} essential genes from database")
    print(f"Found {len(literature_genes)} genes in literature")

    # Parse genome
    print(f"Parsing genome from {genome_path}...")
    genome_sequences = {}
    for record in SeqIO.parse(genome_path, 'fasta'):
        genome_sequences[record.id] = {
            'id': record.id,
            'description': record.description,
            'sequence': str(record.seq),
            'length': len(record.seq)
        }

    print(f"Loaded {len(genome_sequences)} sequences from genome")

    # Match genes
    candidates = []
    matched_gene_names = set()  # Track to avoid duplicates

    for gene in essential_genes:
        for seq_id, seq_data in genome_sequences.items():
            if match_gene_to_sequence(gene, seq_data['description']):
                # Avoid duplicate gene matches (keep best sequence)
                if gene['name'] in matched_gene_names:
                    continue

                # Skip very short sequences
                if seq_data['length'] < 300:
                    continue

                score = calculate_score(gene, literature_genes)

                # Determine evidence
                gene_names = [gene['name'].lower()] + [a.lower() for a in gene.get('aliases', [])]
                has_lit_support = any(name in literature_genes for name in gene_names)

                candidates.append({
                    'gene_id': seq_id,
                    'gene_name': gene['name'],
                    'function': gene.get('function', 'Unknown function'),
                    'score': score,
                    'evidence': {
                        'ortholog_match': True,
                        'literature_support': has_lit_support,
                        'essential_in_species': gene.get('essential_in', []),
                        'references': gene.get('references', [])
                    },
                    'sequence': seq_data['sequence'],
                    'sequence_length': seq_data['length']
                })

                matched_gene_names.add(gene['name'])
                break  # Move to next essential gene

    # Sort by score and take top results
    candidates.sort(key=lambda x: x['score'], reverse=True)
    top_candidates = candidates[:max_results]

    # Write output
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(top_candidates, f, indent=2)

    # Summary
    print(f"\n✓ Found {len(top_candidates)} essential gene matches")
    print(f"  (from {len(candidates)} total matches)")

    if top_candidates:
        print("\nTop 5 genes:")
        for i, cand in enumerate(top_candidates[:5], 1):
            lit_mark = "📚" if cand['evidence']['literature_support'] else ""
            print(f"  {i}. {cand['gene_name']}: {cand['score']:.2f} {lit_mark}")


def main():
    parser = argparse.ArgumentParser(
        description='Match essential genes against target genome'
    )
    parser.add_argument('--genome', required=True,
                        help='Path to genome FASTA file')
    parser.add_argument('--essential-db', required=True,
                        help='Path to essential genes JSON database')
    parser.add_argument('--literature', required=False,
                        help='Path to literature search JSON (optional)')
    parser.add_argument('--output', required=True,
                        help='Output JSON file path')
    parser.add_argument('--max-results', type=int, default=20,
                        help='Maximum number of genes to return')
    args = parser.parse_args()

    match_essential_genes(
        args.genome,
        args.essential_db,
        args.literature,
        args.output,
        args.max_results
    )


if __name__ == '__main__':
    main()
