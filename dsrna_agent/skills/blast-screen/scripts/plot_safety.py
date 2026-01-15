#!/usr/bin/env python3
"""Generate safety analysis visualizations."""

import argparse
import json
from pathlib import Path
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Set style
plt.style.use('seaborn-v0_8-whitegrid')


def plot_safety_results(blast_results_path: str, candidates_path: str, output_dir: str) -> None:
    """Generate safety analysis plots."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    with open(blast_results_path) as f:
        blast_data = json.load(f)

    with open(candidates_path) as f:
        candidates = json.load(f)

    results = blast_data.get('results', [])

    if not results:
        print("No BLAST results found")
        return

    # Create candidate -> gene mapping
    gene_map = {c['id']: c['gene_name'] for c in candidates}

    # --- Plot 1: Safety Heatmap ---
    fig, ax = plt.subplots(figsize=(10, 8))

    # Prepare data for heatmap
    cand_ids = [r['candidate_id'] for r in results]
    human_matches = [r.get('human_max_match', 0) for r in results]
    honeybee_matches = [r.get('honeybee_max_match', 0) for r in results]

    heatmap_data = pd.DataFrame({
        'Human': human_matches,
        'Honeybee': honeybee_matches
    }, index=cand_ids)

    # Custom colormap: green (safe) -> yellow (caution) -> red (reject)
    cmap = sns.diverging_palette(120, 10, s=80, l=55, n=20, as_cmap=True)

    sns.heatmap(heatmap_data, annot=True, fmt='d', cmap='RdYlGn_r',
                vmin=0, vmax=25, ax=ax,
                cbar_kws={'label': 'Max Match Length (bp)'})

    # Add threshold lines in colorbar
    ax.set_xlabel('Non-Target Organism', fontsize=12)
    ax.set_ylabel('Candidate', fontsize=12)
    ax.set_title('Off-Target Match Lengths\n(Green=Safe, Yellow=Caution, Red=Reject)',
                 fontsize=14, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_dir / 'safety_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved safety_heatmap.png")

    # --- Plot 2: Match Length Distribution ---
    fig, ax = plt.subplots(figsize=(10, 6))

    all_matches = human_matches + honeybee_matches

    bins = np.arange(0, max(all_matches) + 3, 2)
    ax.hist(all_matches, bins=bins, edgecolor='black', alpha=0.7, color='#3498db')

    # Add threshold lines
    ax.axvline(15, color='orange', linestyle='--', linewidth=2,
               label='Caution threshold (15bp)')
    ax.axvline(19, color='red', linestyle='--', linewidth=2,
               label='Reject threshold (19bp)')

    # Shade regions
    ax.axvspan(0, 15, alpha=0.1, color='green')
    ax.axvspan(15, 19, alpha=0.1, color='orange')
    ax.axvspan(19, max(all_matches) + 5, alpha=0.1, color='red')

    ax.set_xlabel('Max Match Length (bp)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title('Distribution of Off-Target Match Lengths', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_dir / 'safety_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved safety_distribution.png")

    # --- Plot 3: Safety Status by Gene ---
    fig, ax = plt.subplots(figsize=(12, 6))

    # Group by gene and status
    gene_status = defaultdict(lambda: {'safe': 0, 'caution': 0, 'reject': 0})

    for r in results:
        gene = gene_map.get(r['candidate_id'], 'Unknown')
        status = r.get('safety_status', 'unknown')
        if status in gene_status[gene]:
            gene_status[gene][status] += 1

    genes = list(gene_status.keys())
    x = np.arange(len(genes))
    width = 0.25

    safe_counts = [gene_status[g]['safe'] for g in genes]
    caution_counts = [gene_status[g]['caution'] for g in genes]
    reject_counts = [gene_status[g]['reject'] for g in genes]

    ax.bar(x - width, safe_counts, width, label='Safe', color='#27ae60', edgecolor='black')
    ax.bar(x, caution_counts, width, label='Caution', color='#f39c12', edgecolor='black')
    ax.bar(x + width, reject_counts, width, label='Reject', color='#e74c3c', edgecolor='black')

    ax.set_ylabel('Number of Candidates', fontsize=12)
    ax.set_xlabel('Target Gene', fontsize=12)
    ax.set_title('Safety Status by Target Gene', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(genes, rotation=45, ha='right', fontsize=10)
    ax.legend(loc='upper right', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_dir / 'safety_by_gene.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved safety_by_gene.png")

    # Print summary
    safe_count = sum(1 for r in results if r.get('safety_status') == 'safe')
    caution_count = sum(1 for r in results if r.get('safety_status') == 'caution')
    reject_count = sum(1 for r in results if r.get('safety_status') == 'reject')

    print(f"\n{'='*50}")
    print(f"Safety Screening Results:")
    print(f"  ✅ Safe (<15bp): {safe_count}")
    print(f"  ⚠️  Caution (15-18bp): {caution_count}")
    print(f"  ❌ Rejected (≥19bp): {reject_count}")
    print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate safety analysis visualizations'
    )
    parser.add_argument('--blast-results', required=True,
                        help='Path to BLAST results JSON')
    parser.add_argument('--candidates', required=True,
                        help='Path to candidates JSON')
    parser.add_argument('--output-dir', required=True,
                        help='Output directory for plots')
    args = parser.parse_args()

    plot_safety_results(args.blast_results, args.candidates, args.output_dir)


if __name__ == '__main__':
    main()
