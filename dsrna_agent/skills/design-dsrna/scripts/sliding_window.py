#!/usr/bin/env python3
"""Design dsRNA candidates using sliding window algorithm."""

import json
import re
import argparse
from pathlib import Path


def calculate_gc_content(sequence: str) -> float:
    """Calculate GC content of a sequence."""
    seq = sequence.upper()
    gc_count = seq.count('G') + seq.count('C')
    return gc_count / len(seq) if seq else 0


def has_poly_n_run(sequence: str, min_length: int = 4) -> bool:
    """Check if sequence has poly-N runs (4+ consecutive same base)."""
    pattern = r'([ATGC])\1{' + str(min_length - 1) + r',}'
    return bool(re.search(pattern, sequence.upper()))


def score_window(
    sequence: str,
    start: int,
    end: int,
    gene_length: int
) -> dict:
    """Score a window based on design criteria."""
    window_seq = sequence[start:end].upper()
    gc = calculate_gc_content(window_seq)
    poly_n = has_poly_n_run(window_seq)

    score = 0
    score_breakdown = {}

    # GC content scoring
    if 0.35 <= gc <= 0.50:
        score += 2
        score_breakdown['gc'] = 2
    elif 0.30 <= gc <= 0.55:
        score += 1
        score_breakdown['gc'] = 1
    else:
        score_breakdown['gc'] = 0

    # Poly-N penalty
    if not poly_n:
        score += 1
        score_breakdown['poly_n'] = 1
    else:
        score_breakdown['poly_n'] = 0

    # Position scoring (avoid ends)
    if start >= 75:
        score += 1
        score_breakdown['start_pos'] = 1
    else:
        score_breakdown['start_pos'] = 0

    if end <= gene_length - 50:
        score += 1
        score_breakdown['end_pos'] = 1
    else:
        score_breakdown['end_pos'] = 0

    return {
        'start': start,
        'end': end,
        'sequence': window_seq,
        'gc_content': round(gc, 3),
        'has_poly_n': poly_n,
        'score': score,
        'score_breakdown': score_breakdown
    }


def design_candidates_for_gene(
    gene: dict,
    window_length: int = 300,
    step_size: int = 50,
    num_candidates: int = 3
) -> list[dict]:
    """Design dsRNA candidates for a single gene."""
    sequence = gene.get('sequence', '')
    gene_name = gene.get('gene_name', 'unknown')
    gene_id = gene.get('gene_id', 'unknown')
    gene_length = len(sequence)

    # Skip genes that are too short
    if gene_length < window_length:
        print(f"  Skipping {gene_name}: too short ({gene_length} < {window_length})")
        return []

    # Score all windows
    windows = []
    for start in range(0, gene_length - window_length + 1, step_size):
        end = start + window_length
        window = score_window(sequence, start, end, gene_length)
        windows.append(window)

    # Sort by score (descending)
    windows.sort(key=lambda x: x['score'], reverse=True)

    # Select top non-overlapping windows
    selected = []
    used_positions = set()

    for window in windows:
        if len(selected) >= num_candidates:
            break

        window_positions = set(range(window['start'], window['end']))
        if not window_positions.intersection(used_positions):
            candidate_id = f"{gene_name}_{len(selected) + 1}"

            selected.append({
                'id': candidate_id,
                'gene_name': gene_name,
                'gene_id': gene_id,
                'sequence': window['sequence'],
                'start': window['start'],
                'end': window['end'],
                'length': window_length,
                'gc_content': window['gc_content'],
                'has_poly_n': window['has_poly_n'],
                'design_score': window['score'],
                'score_breakdown': window['score_breakdown']
            })

            used_positions.update(window_positions)

    return selected


def design_all_candidates(
    genes_path: str,
    output_path: str,
    num_genes: int = 5,
    candidates_per_gene: int = 3,
    window_length: int = 300
) -> None:
    """Design dsRNA candidates for top N genes."""

    # Load genes
    with open(genes_path) as f:
        all_genes = json.load(f)

    # Take top N genes
    top_genes = all_genes[:num_genes]

    print(f"Designing candidates for top {len(top_genes)} genes")
    print(f"  Window length: {window_length} bp")
    print(f"  Candidates per gene: {candidates_per_gene}")

    # Design candidates for each gene
    all_candidates = []
    for gene in top_genes:
        gene_name = gene.get('gene_name', 'unknown')
        print(f"\nProcessing {gene_name}...")

        candidates = design_candidates_for_gene(
            gene,
            window_length=window_length,
            num_candidates=candidates_per_gene
        )

        all_candidates.extend(candidates)
        print(f"  Designed {len(candidates)} candidates")

    # Write output
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(all_candidates, f, indent=2)

    # Summary
    print(f"\n✓ Designed {len(all_candidates)} total candidates")

    if all_candidates:
        gc_values = [c['gc_content'] for c in all_candidates]
        scores = [c['design_score'] for c in all_candidates]
        print(f"  GC range: {min(gc_values):.1%} - {max(gc_values):.1%}")
        print(f"  Score range: {min(scores)} - {max(scores)}")

        # Count by gene
        genes = set(c['gene_name'] for c in all_candidates)
        print(f"  Genes covered: {len(genes)}")


def main():
    parser = argparse.ArgumentParser(
        description='Design dsRNA candidates using sliding window'
    )
    parser.add_argument('--genes', required=True,
                        help='Path to essential genes JSON')
    parser.add_argument('--num-genes', type=int, default=5,
                        help='Number of top genes to process')
    parser.add_argument('--candidates-per-gene', type=int, default=3,
                        help='Number of candidates per gene')
    parser.add_argument('--length', type=int, default=300,
                        help='dsRNA candidate length in bp')
    parser.add_argument('--output', required=True,
                        help='Output JSON file path')
    args = parser.parse_args()

    design_all_candidates(
        args.genes,
        args.output,
        num_genes=args.num_genes,
        candidates_per_gene=args.candidates_per_gene,
        window_length=args.length
    )


if __name__ == '__main__':
    main()
