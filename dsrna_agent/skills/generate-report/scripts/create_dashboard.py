#!/usr/bin/env python3
"""Generate summary dashboard for final report."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Set style
plt.style.use('seaborn-v0_8-whitegrid')


def load_json_safe(path: str) -> dict | list:
    """Safely load JSON file, return empty dict/list on error."""
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def create_dashboard(data_dir: str, output_path: str) -> None:
    """Create multi-panel summary dashboard."""

    data_dir = Path(data_dir)

    # Load all data
    ranked = load_json_safe(data_dir / 'ranked_candidates.json')
    genes = load_json_safe(data_dir / 'essential_genes.json')
    blast = load_json_safe(data_dir / 'blast_results.json')
    genome_stats = load_json_safe(data_dir / 'figures' / 'genome_stats.json')

    if not ranked:
        print("No ranked candidates found")
        return

    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))

    # Title
    fig.suptitle('dsRNA Design Summary Dashboard', fontsize=18, fontweight='bold', y=0.98)

    # --- Panel 1: Top 3 Candidates (top left) ---
    ax1 = fig.add_subplot(2, 2, 1)

    top3 = ranked[:3] if isinstance(ranked, list) else []

    if top3:
        cand_ids = [c['id'] for c in top3]
        combined_scores = [c['combined_score'] for c in top3]

        colors = ['#27ae60', '#3498db', '#9b59b6']
        bars = ax1.barh(range(len(top3)), combined_scores, color=colors, edgecolor='black')

        ax1.set_yticks(range(len(top3)))
        ax1.set_yticklabels(cand_ids, fontsize=12)
        ax1.set_xlabel('Combined Score', fontsize=11)
        ax1.set_title('🏆 Top 3 Candidates', fontsize=14, fontweight='bold')
        ax1.set_xlim(0, 1)
        ax1.invert_yaxis()

        # Add score labels
        for bar, score in zip(bars, combined_scores):
            ax1.text(score + 0.02, bar.get_y() + bar.get_height()/2,
                     f'{score:.3f}', va='center', fontsize=11, fontweight='bold')

        # Add rank badges
        for i, (bar, cand) in enumerate(zip(bars, top3)):
            status = cand.get('safety_status', 'unknown')
            icon = '✅' if status == 'safe' else '⚠️' if status == 'caution' else '❌'
            ax1.text(-0.05, bar.get_y() + bar.get_height()/2,
                     f'{i+1}. {icon}', va='center', ha='right', fontsize=12)

    # --- Panel 2: Safety Statistics (top right) ---
    ax2 = fig.add_subplot(2, 2, 2)

    blast_results = blast.get('results', []) if isinstance(blast, dict) else []

    if blast_results:
        safe = sum(1 for r in blast_results if r.get('safety_status') == 'safe')
        caution = sum(1 for r in blast_results if r.get('safety_status') == 'caution')
        reject = sum(1 for r in blast_results if r.get('safety_status') == 'reject')

        sizes = [safe, caution, reject]
        labels = [f'Safe\n({safe})', f'Caution\n({caution})', f'Reject\n({reject})']
        colors_pie = ['#27ae60', '#f39c12', '#e74c3c']
        explode = (0.05, 0, 0)

        # Only include non-zero slices
        non_zero = [(s, l, c, e) for s, l, c, e in zip(sizes, labels, colors_pie, explode) if s > 0]
        if non_zero:
            sizes, labels, colors_pie, explode = zip(*non_zero)
            ax2.pie(sizes, explode=explode, labels=labels, colors=colors_pie,
                    autopct='%1.0f%%', shadow=True, startangle=90,
                    textprops={'fontsize': 11})

        ax2.set_title('🛡️ Safety Profile', fontsize=14, fontweight='bold')
    else:
        ax2.text(0.5, 0.5, 'No safety data', ha='center', va='center', fontsize=14)
        ax2.set_title('🛡️ Safety Profile', fontsize=14, fontweight='bold')

    # --- Panel 3: Gene Scores (bottom left) ---
    ax3 = fig.add_subplot(2, 2, 3)

    if genes and isinstance(genes, list):
        top_genes = genes[:5]
        gene_names = [g['gene_name'] for g in top_genes]
        gene_scores = [g['score'] for g in top_genes]

        colors_genes = plt.cm.viridis(np.linspace(0.3, 0.8, len(top_genes)))
        ax3.barh(range(len(top_genes)), gene_scores, color=colors_genes, edgecolor='black')

        ax3.set_yticks(range(len(top_genes)))
        ax3.set_yticklabels(gene_names, fontsize=11)
        ax3.set_xlabel('Essentiality Score', fontsize=11)
        ax3.set_title('🧬 Target Gene Scores', fontsize=14, fontweight='bold')
        ax3.set_xlim(0, 1)
        ax3.invert_yaxis()

        # Mark literature support
        for i, g in enumerate(top_genes):
            if g.get('evidence', {}).get('literature_support'):
                ax3.text(g['score'] + 0.02, i, '📚', va='center', fontsize=12)

    # --- Panel 4: Workflow Summary (bottom right) ---
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.axis('off')

    # Create summary text
    summary_lines = []

    # Genome stats
    if genome_stats:
        summary_lines.append(f"📊 Genome: {genome_stats.get('total_sequences', 'N/A'):,} CDS")
        summary_lines.append(f"   Mean GC: {genome_stats.get('mean_gc', 0):.1%}")

    # Genes
    if genes:
        summary_lines.append(f"\n🧬 Genes: {len(genes)} essential genes identified")
        lit_support = sum(1 for g in genes if g.get('evidence', {}).get('literature_support'))
        summary_lines.append(f"   Literature support: {lit_support}")

    # Candidates
    if ranked:
        summary_lines.append(f"\n🧪 Candidates: {len(ranked)} designed")
        safe_cands = sum(1 for c in ranked if c.get('safety_status') == 'safe')
        summary_lines.append(f"   Safe candidates: {safe_cands}")

    # Top recommendation
    if ranked:
        top = ranked[0]
        summary_lines.append(f"\n{'='*40}")
        summary_lines.append(f"🏆 TOP RECOMMENDATION")
        summary_lines.append(f"{'='*40}")
        summary_lines.append(f"   {top['id']}")
        summary_lines.append(f"   Target: {top['gene_name']}")
        summary_lines.append(f"   Score: {top['combined_score']:.3f}")
        summary_lines.append(f"   Status: {top.get('safety_status', 'N/A').upper()}")

    summary_text = '\n'.join(summary_lines)

    ax4.text(0.1, 0.95, summary_text, transform=ax4.transAxes,
             fontsize=12, verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    ax4.set_title('📋 Workflow Summary', fontsize=14, fontweight='bold',
                  loc='left', x=0.1)

    # Adjust layout
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"✓ Saved dashboard to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Create summary dashboard'
    )
    parser.add_argument('--data-dir', required=True,
                        help='Directory containing output JSON files')
    parser.add_argument('--output', required=True,
                        help='Output path for dashboard PNG')
    args = parser.parse_args()

    create_dashboard(args.data_dir, args.output)


if __name__ == '__main__':
    main()
