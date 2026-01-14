#!/usr/bin/env python3
"""Generate ranking and scoring visualizations."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Set style
plt.style.use('seaborn-v0_8-whitegrid')


def plot_ranking_results(ranked_path: str, output_dir: str) -> None:
    """Generate ranking analysis plots."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    with open(ranked_path) as f:
        candidates = json.load(f)

    if not candidates:
        print("No candidates found")
        return

    # --- Plot 1: Score Breakdown ---
    fig, ax = plt.subplots(figsize=(14, 8))

    # Take top 10 candidates
    top_cands = candidates[:10]

    cand_ids = [c['id'] for c in top_cands]
    efficacy_scores = [c['efficacy_score'] for c in top_cands]
    safety_scores = [c['safety_score'] for c in top_cands]
    combined_scores = [c['combined_score'] for c in top_cands]

    x = np.arange(len(cand_ids))
    width = 0.25

    ax.bar(x - width, efficacy_scores, width, label='Efficacy', color='#3498db', edgecolor='black')
    ax.bar(x, safety_scores, width, label='Safety', color='#27ae60', edgecolor='black')
    ax.bar(x + width, combined_scores, width, label='Combined', color='#9b59b6', edgecolor='black')

    ax.set_ylabel('Score', fontsize=12)
    ax.set_xlabel('Candidate', fontsize=12)
    ax.set_title('Score Breakdown: Top 10 Candidates', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(cand_ids, rotation=45, ha='right', fontsize=9)
    ax.set_ylim(0, 1.1)
    ax.legend(loc='upper right', fontsize=10)

    # Add combined score labels on top
    for i, score in enumerate(combined_scores):
        ax.text(i + width, score + 0.02, f'{score:.2f}', ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    plt.savefig(output_dir / 'score_breakdown.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved score_breakdown.png")

    # --- Plot 2: Efficacy vs Safety Scatter ---
    fig, ax = plt.subplots(figsize=(10, 8))

    efficacy_all = [c['efficacy_score'] for c in candidates]
    safety_all = [c['safety_score'] for c in candidates]

    # Color by safety status
    colors = []
    for c in candidates:
        status = c.get('safety_status', 'unknown')
        if status == 'safe':
            colors.append('#27ae60')
        elif status == 'caution':
            colors.append('#f39c12')
        else:
            colors.append('#e74c3c')

    scatter = ax.scatter(efficacy_all, safety_all, c=colors, s=100,
                         edgecolor='black', alpha=0.8)

    # Label top 5
    for i, c in enumerate(candidates[:5]):
        ax.annotate(c['id'], (c['efficacy_score'], c['safety_score']),
                    xytext=(5, 5), textcoords='offset points', fontsize=9,
                    fontweight='bold')

    ax.set_xlabel('Efficacy Score', fontsize=12)
    ax.set_ylabel('Safety Score', fontsize=12)
    ax.set_title('Efficacy vs Safety Trade-off', fontsize=14, fontweight='bold')
    ax.set_xlim(0, 1.1)
    ax.set_ylim(-0.1, 1.1)

    # Add quadrant labels
    ax.axhline(0.7, color='gray', linestyle=':', alpha=0.5)
    ax.axvline(0.7, color='gray', linestyle=':', alpha=0.5)

    ax.text(0.85, 0.85, 'OPTIMAL', ha='center', va='center', fontsize=12,
            color='green', fontweight='bold', alpha=0.7)
    ax.text(0.35, 0.85, 'Safe but\nLow Efficacy', ha='center', va='center',
            fontsize=10, color='gray', alpha=0.7)
    ax.text(0.85, 0.35, 'Effective but\nSafety Concerns', ha='center', va='center',
            fontsize=10, color='gray', alpha=0.7)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#27ae60', edgecolor='black', label='Safe'),
        Patch(facecolor='#f39c12', edgecolor='black', label='Caution'),
        Patch(facecolor='#e74c3c', edgecolor='black', label='Reject')
    ]
    ax.legend(handles=legend_elements, loc='lower left', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_dir / 'efficacy_vs_safety_scatter.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved efficacy_vs_safety_scatter.png")

    # --- Plot 3: Top 5 Radar Chart ---
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))

    categories = ['GC Score', 'No Poly-N', 'Position', 'Gene Score', 'Safety']
    num_vars = len(categories)

    # Compute angle for each category
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]  # Complete the circle

    # Plot each candidate
    colors_radar = plt.cm.Set1(np.linspace(0, 1, 5))

    for i, c in enumerate(candidates[:5]):
        breakdown = c.get('efficacy_breakdown', {})
        values = [
            breakdown.get('gc_score', 0),
            breakdown.get('poly_n_score', 0),
            breakdown.get('position_score', 0),
            breakdown.get('gene_score', 0),
            c.get('safety_score', 0)
        ]
        values += values[:1]  # Complete the circle

        ax.plot(angles, values, 'o-', linewidth=2, label=c['id'], color=colors_radar[i])
        ax.fill(angles, values, alpha=0.1, color=colors_radar[i])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=11)
    ax.set_ylim(0, 1.1)
    ax.set_title('Top 5 Candidates: Multi-dimensional Comparison',
                 fontsize=14, fontweight='bold', y=1.08)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0), fontsize=10)

    plt.tight_layout()
    plt.savefig(output_dir / 'top_candidates_radar.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved top_candidates_radar.png")

    # Print summary
    top = candidates[0]
    print(f"\n{'='*50}")
    print(f"Ranking Results:")
    print(f"  Top candidate: {top['id']}")
    print(f"    Gene: {top['gene_name']}")
    print(f"    Efficacy: {top['efficacy_score']:.3f}")
    print(f"    Safety: {top['safety_score']:.3f}")
    print(f"    Combined: {top['combined_score']:.3f}")
    print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate ranking visualizations'
    )
    parser.add_argument('--ranked', required=True,
                        help='Path to ranked candidates JSON')
    parser.add_argument('--output-dir', required=True,
                        help='Output directory for plots')
    args = parser.parse_args()

    plot_ranking_results(args.ranked, args.output_dir)


if __name__ == '__main__':
    main()
