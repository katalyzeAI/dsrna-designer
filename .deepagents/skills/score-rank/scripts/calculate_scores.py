#!/usr/bin/env python3
"""Calculate final efficacy and safety scores for dsRNA candidates."""

import json
import argparse
from pathlib import Path


def calculate_gc_score(gc_content: float) -> float:
    """Score GC content (optimal 35-50%)."""
    if 0.35 <= gc_content <= 0.50:
        return 1.0
    elif 0.30 <= gc_content <= 0.55:
        return 0.7
    else:
        return 0.3


def calculate_safety_score(max_match: int) -> float:
    """Calculate safety score based on max BLAST match length."""
    if max_match >= 19:
        return 0.0
    elif max_match >= 15:
        return 0.7
    else:
        return 1.0


def calculate_scores(
    candidates_path: str,
    blast_results_path: str,
    essential_genes_path: str,
    output_path: str
) -> None:
    """Calculate and rank all candidates."""

    # Load data
    with open(candidates_path) as f:
        candidates = json.load(f)

    with open(blast_results_path) as f:
        blast_data = json.load(f)
        blast_results = blast_data.get('results', [])

    with open(essential_genes_path) as f:
        genes = json.load(f)

    # Create lookups
    blast_lookup = {r['candidate_id']: r for r in blast_results}
    gene_lookup = {g['gene_name']: g['score'] for g in genes}

    print(f"Scoring {len(candidates)} candidates...")

    scored_candidates = []

    for candidate in candidates:
        cand_id = candidate.get('id', 'unknown')
        gene_name = candidate.get('gene_name', '')

        # Get BLAST results
        blast = blast_lookup.get(cand_id, {})

        # --- Efficacy Score Components ---

        # 1. GC content (30%)
        gc = candidate.get('gc_content', 0.4)
        gc_score = calculate_gc_score(gc)

        # 2. Poly-N penalty (20%)
        has_poly_n = candidate.get('has_poly_n', False)
        poly_n_score = 0.0 if has_poly_n else 1.0

        # 3. Position/design score (20%)
        design_score = candidate.get('design_score', 0)
        position_score = min(design_score / 5.0, 1.0)

        # 4. Gene essentiality (30%)
        gene_essentiality = gene_lookup.get(gene_name, 0.5)

        # Combined efficacy
        efficacy = (
            0.3 * gc_score +
            0.2 * poly_n_score +
            0.2 * position_score +
            0.3 * gene_essentiality
        )

        # --- Safety Score ---
        max_match = blast.get('max_match', 0)
        safety = calculate_safety_score(max_match)
        safety_status = blast.get('safety_status', 'unknown')

        # --- Combined Score ---
        combined = efficacy * safety

        # Build scored candidate record
        scored_candidate = {
            **candidate,
            'efficacy_score': round(efficacy, 3),
            'efficacy_breakdown': {
                'gc_score': round(gc_score, 2),
                'poly_n_score': round(poly_n_score, 2),
                'position_score': round(position_score, 2),
                'gene_score': round(gene_essentiality, 2)
            },
            'safety_score': round(safety, 3),
            'combined_score': round(combined, 3),
            'human_max_match': blast.get('human_max_match', 0),
            'honeybee_max_match': blast.get('honeybee_max_match', 0),
            'safety_status': safety_status
        }

        scored_candidates.append(scored_candidate)

    # Sort by combined score (descending)
    scored_candidates.sort(key=lambda x: x['combined_score'], reverse=True)

    # Write output
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(scored_candidates, f, indent=2)

    # Summary
    print(f"\n✓ Ranked {len(scored_candidates)} candidates")

    if scored_candidates:
        print("\nTop 5 candidates:")
        print("-" * 70)
        print(f"{'Rank':<5} {'ID':<20} {'Efficacy':<10} {'Safety':<10} {'Combined':<10} {'Status'}")
        print("-" * 70)

        for i, cand in enumerate(scored_candidates[:5], 1):
            status_icon = {
                'safe': '✅',
                'caution': '⚠️ ',
                'reject': '❌'
            }.get(cand['safety_status'], '?')

            print(f"{i:<5} {cand['id']:<20} {cand['efficacy_score']:<10.3f} "
                  f"{cand['safety_score']:<10.3f} {cand['combined_score']:<10.3f} "
                  f"{status_icon}")

        # Statistics
        top = scored_candidates[0]
        print(f"\nTop candidate: {top['id']} (score: {top['combined_score']:.3f})")

        # Score distribution
        scores = [c['combined_score'] for c in scored_candidates]
        safe_count = sum(1 for c in scored_candidates if c['safety_status'] == 'safe')

        print(f"\nScore distribution:")
        print(f"  Max: {max(scores):.3f}")
        print(f"  Min: {min(scores):.3f}")
        print(f"  Safe candidates: {safe_count}/{len(scored_candidates)}")


def main():
    parser = argparse.ArgumentParser(
        description='Calculate final scores for dsRNA candidates'
    )
    parser.add_argument('--candidates', required=True,
                        help='Path to candidates JSON')
    parser.add_argument('--blast-results', required=True,
                        help='Path to BLAST results JSON')
    parser.add_argument('--essential-genes', required=True,
                        help='Path to essential genes JSON')
    parser.add_argument('--output', required=True,
                        help='Output JSON file path')
    args = parser.parse_args()

    calculate_scores(
        args.candidates,
        args.blast_results,
        args.essential_genes,
        args.output
    )


if __name__ == '__main__':
    main()
