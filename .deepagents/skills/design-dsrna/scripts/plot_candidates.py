#!/usr/bin/env python3
"""Generate dsRNA candidate design visualizations."""

import argparse
import json
from pathlib import Path
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np

# Set style
plt.style.use('seaborn-v0_8-whitegrid')


def plot_candidate_results(candidates_path: str, genes_path: str, output_dir: str) -> None:
    """Generate candidate design plots."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    with open(candidates_path) as f:
        candidates = json.load(f)

    with open(genes_path) as f:
        genes = json.load(f)

    if not candidates:
        print("No candidates found")
        return

    # Create gene length lookup
    gene_lengths = {g['gene_name']: g.get('sequence_length', 0) for g in genes}

    # --- Plot 1: Candidate Locations on Genes ---
    fig, ax = plt.subplots(figsize=(14, 8))

    # Group candidates by gene
    by_gene = defaultdict(list)
    for c in candidates:
        by_gene[c['gene_name']].append(c)

    gene_names = list(by_gene.keys())
    y_positions = {name: i for i, name in enumerate(gene_names)}

    colors = plt.cm.Set2(np.linspace(0, 1, len(gene_names)))
    gene_colors = {name: colors[i] for i, name in enumerate(gene_names)}

    # Draw gene bars and candidates
    for gene_name, gene_candidates in by_gene.items():
        y = y_positions[gene_name]
        gene_len = gene_lengths.get(gene_name, 3000)

        # Draw gene as thin bar
        ax.barh(y, gene_len, height=0.3, color='lightgray', edgecolor='black', alpha=0.5)

        # Draw candidates as thicker colored bars
        for c in gene_candidates:
            ax.barh(y, c['end'] - c['start'], left=c['start'], height=0.6,
                    color=gene_colors[gene_name], edgecolor='black', alpha=0.8)

            # Label with candidate number
            cand_num = c['id'].split('_')[-1]
            ax.text(c['start'] + (c['end'] - c['start'])/2, y,
                    cand_num, ha='center', va='center', fontsize=9, fontweight='bold')

    ax.set_yticks(list(y_positions.values()))
    ax.set_yticklabels(list(y_positions.keys()), fontsize=11)
    ax.set_xlabel('Position in CDS (bp)', fontsize=12)
    ax.set_title('dsRNA Candidate Positions Along Target Genes',
                 fontsize=14, fontweight='bold')

    # Add legend explaining bars
    ax.text(0.02, 0.98, 'Gray bar = Full CDS\nColored bars = dsRNA candidates (300bp)',
            transform=ax.transAxes, fontsize=9, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    plt.tight_layout()
    plt.savefig(output_dir / 'candidate_locations.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved candidate_locations.png")

    # --- Plot 2: GC Content Distribution ---
    fig, ax = plt.subplots(figsize=(10, 6))

    gc_values = [c['gc_content'] for c in candidates]

    ax.hist(gc_values, bins=15, edgecolor='black', alpha=0.7, color='#3498db')

    # Add optimal range shading
    ax.axvspan(0.35, 0.50, alpha=0.2, color='green', label='Optimal (35-50%)')
    ax.axvline(np.mean(gc_values), color='#e74c3c', linestyle='--', linewidth=2,
               label=f"Mean: {np.mean(gc_values):.1%}")

    ax.set_xlabel('GC Content', fontsize=12)
    ax.set_ylabel('Number of Candidates', fontsize=12)
    ax.set_title('GC Content Distribution of dsRNA Candidates',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)

    # Format x-axis as percentage
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0%}'))

    plt.tight_layout()
    plt.savefig(output_dir / 'candidate_gc_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved candidate_gc_distribution.png")

    # --- Plot 3: Design Score Heatmap ---
    fig, ax = plt.subplots(figsize=(12, 8))

    # Get score breakdowns
    cand_ids = [c['id'] for c in candidates]

    # Score components
    score_components = ['gc', 'poly_n', 'start_pos', 'end_pos']
    component_labels = ['GC Content', 'No Poly-N', 'Good Start', 'Good End']

    # Build matrix
    matrix = []
    for c in candidates:
        breakdown = c.get('score_breakdown', {})
        row = [breakdown.get(comp, 0) for comp in score_components]
        matrix.append(row)

    matrix = np.array(matrix)

    # Create heatmap
    im = ax.imshow(matrix.T, aspect='auto', cmap='RdYlGn', vmin=0, vmax=2)

    ax.set_xticks(np.arange(len(cand_ids)))
    ax.set_xticklabels(cand_ids, rotation=45, ha='right', fontsize=9)
    ax.set_yticks(np.arange(len(component_labels)))
    ax.set_yticklabels(component_labels, fontsize=11)

    ax.set_xlabel('Candidate', fontsize=12)
    ax.set_title('Design Score Components by Candidate', fontsize=14, fontweight='bold')

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Score', fontsize=11)

    # Add text annotations
    for i in range(len(component_labels)):
        for j in range(len(cand_ids)):
            val = matrix[j, i]
            ax.text(j, i, f'{val:.0f}', ha='center', va='center',
                    color='white' if val > 1 else 'black', fontsize=8)

    plt.tight_layout()
    plt.savefig(output_dir / 'candidate_scores_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved candidate_scores_heatmap.png")

    # Print summary
    print(f"\n{'='*50}")
    print(f"Candidate Design Results:")
    print(f"  Total candidates: {len(candidates)}")
    print(f"  Genes covered: {len(by_gene)}")
    print(f"  GC range: {min(gc_values):.1%} - {max(gc_values):.1%}")
    print(f"  Mean design score: {np.mean([c['design_score'] for c in candidates]):.1f}/5")
    print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate candidate design visualizations'
    )
    parser.add_argument('--candidates', required=True,
                        help='Path to candidates JSON')
    parser.add_argument('--genes', required=True,
                        help='Path to essential genes JSON')
    parser.add_argument('--output-dir', required=True,
                        help='Output directory for plots')
    args = parser.parse_args()

    plot_candidate_results(args.candidates, args.genes, args.output_dir)


if __name__ == '__main__':
    main()
