#!/usr/bin/env python3
"""Generate essential gene identification visualizations."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Set style
plt.style.use('seaborn-v0_8-whitegrid')


def plot_gene_results(genes_path: str, output_dir: str) -> None:
    """Generate gene identification plots."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    with open(genes_path) as f:
        genes = json.load(f)

    if not genes:
        print("No genes found in results")
        return

    # --- Plot 1: Gene Ranking ---
    fig, ax = plt.subplots(figsize=(12, 8))

    # Take top 10 genes
    top_genes = genes[:10]

    gene_names = [g['gene_name'] for g in top_genes]
    scores = [g['score'] for g in top_genes]

    # Color by literature support
    colors = []
    for g in top_genes:
        if g.get('evidence', {}).get('literature_support', False):
            colors.append('#27ae60')  # Green for literature support
        else:
            colors.append('#3498db')  # Blue for orthology only

    y_pos = np.arange(len(gene_names))

    bars = ax.barh(y_pos, scores, color=colors, edgecolor='black', alpha=0.8)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(gene_names, fontsize=11)
    ax.invert_yaxis()

    ax.set_xlabel('Essentiality Score', fontsize=12)
    ax.set_xlim(0, 1.1)
    ax.set_title('Top Essential Gene Candidates', fontsize=14, fontweight='bold')

    # Add score labels
    for bar, score in zip(bars, scores):
        ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height()/2,
                f'{score:.2f}', va='center', fontsize=10)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#27ae60', edgecolor='black', label='Literature + Orthology'),
        Patch(facecolor='#3498db', edgecolor='black', label='Orthology only')
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_dir / 'gene_ranking.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved gene_ranking.png")

    # --- Plot 2: Evidence Breakdown ---
    fig, ax = plt.subplots(figsize=(12, 6))

    gene_names = [g['gene_name'] for g in top_genes]

    # Calculate score components
    base_scores = [0.5] * len(top_genes)  # Base orthology
    lit_scores = [0.3 if g.get('evidence', {}).get('literature_support') else 0
                  for g in top_genes]
    species_scores = [min(0.2, len(g.get('evidence', {}).get('essential_in_species', [])) * 0.05)
                      for g in top_genes]

    x = np.arange(len(gene_names))
    width = 0.6

    # Stacked bars
    ax.bar(x, base_scores, width, label='Orthology Match (0.5)', color='#3498db')
    ax.bar(x, lit_scores, width, bottom=base_scores, label='Literature Support (+0.3)',
           color='#27ae60')
    ax.bar(x, species_scores, width,
           bottom=[b + l for b, l in zip(base_scores, lit_scores)],
           label='Multi-species Essential (+0.2 max)', color='#e74c3c')

    ax.set_ylabel('Score Components', fontsize=12)
    ax.set_xlabel('Gene', fontsize=12)
    ax.set_title('Evidence Breakdown by Gene', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(gene_names, rotation=45, ha='right', fontsize=10)
    ax.set_ylim(0, 1.2)
    ax.legend(loc='upper right', fontsize=9)

    plt.tight_layout()
    plt.savefig(output_dir / 'gene_evidence_breakdown.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved gene_evidence_breakdown.png")

    # --- Plot 3: CDS Length Distribution ---
    fig, ax = plt.subplots(figsize=(10, 6))

    lengths = [g.get('sequence_length', 0) for g in genes if g.get('sequence_length', 0) > 0]

    if lengths:
        ax.hist(lengths, bins=20, edgecolor='black', alpha=0.7, color='#9b59b6')
        ax.axvline(np.mean(lengths), color='#e74c3c', linestyle='--', linewidth=2,
                   label=f"Mean: {np.mean(lengths):,.0f} bp")

        ax.set_xlabel('CDS Length (bp)', fontsize=12)
        ax.set_ylabel('Number of Genes', fontsize=12)
        ax.set_title('CDS Length Distribution of Identified Genes',
                     fontsize=14, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_dir / 'gene_length_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved gene_length_distribution.png")

    # Print summary
    lit_supported = sum(1 for g in genes if g.get('evidence', {}).get('literature_support'))
    print(f"\n{'='*50}")
    print(f"Gene Identification Results:")
    print(f"  Total genes identified: {len(genes)}")
    print(f"  Literature-supported: {lit_supported}")
    print(f"  Top gene: {genes[0]['gene_name']} (score: {genes[0]['score']:.2f})")
    print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate gene identification visualizations'
    )
    parser.add_argument('--genes', required=True,
                        help='Path to essential genes JSON')
    parser.add_argument('--output-dir', required=True,
                        help='Output directory for plots')
    args = parser.parse_args()

    plot_gene_results(args.genes, args.output_dir)


if __name__ == '__main__':
    main()
