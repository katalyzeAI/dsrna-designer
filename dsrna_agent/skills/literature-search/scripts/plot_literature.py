#!/usr/bin/env python3
"""Generate literature search visualizations."""

import argparse
import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Set style
plt.style.use('seaborn-v0_8-whitegrid')


def plot_literature_results(literature_path: str, output_dir: str) -> None:
    """Generate literature analysis plots."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    with open(literature_path) as f:
        data = json.load(f)

    # Handle both formats
    if isinstance(data, dict):
        papers = data.get('papers', [])
        summary = data.get('summary', {})
    else:
        papers = data
        summary = {}

    if not papers:
        print("No papers found in literature search results")
        # Create placeholder plot
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, 'No literature found\nfor this species',
                ha='center', va='center', fontsize=14, transform=ax.transAxes)
        ax.set_title('Gene Mentions in RNAi Literature', fontsize=14, fontweight='bold')
        plt.savefig(output_dir / 'literature_gene_frequency.png', dpi=300, bbox_inches='tight')
        plt.close()
        return

    # Count gene mentions
    all_genes = []
    for paper in papers:
        all_genes.extend(paper.get('gene_names', []))

    gene_counts = Counter(all_genes)

    # --- Plot 1: Gene Frequency Bar Chart ---
    fig, ax = plt.subplots(figsize=(12, 8))

    if gene_counts:
        # Get top 15 genes
        top_genes = gene_counts.most_common(15)
        genes = [g[0] for g in top_genes]
        counts = [g[1] for g in top_genes]

        # Horizontal bar chart
        y_pos = np.arange(len(genes))
        colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(genes)))

        bars = ax.barh(y_pos, counts, color=colors, edgecolor='black', alpha=0.8)

        ax.set_yticks(y_pos)
        ax.set_yticklabels(genes, fontsize=11)
        ax.invert_yaxis()  # Top gene at top

        ax.set_xlabel('Number of Papers Mentioning Gene', fontsize=12)
        ax.set_title('Most Frequently Targeted Genes in RNAi Literature',
                     fontsize=14, fontweight='bold')

        # Add count labels
        for bar, count in zip(bars, counts):
            ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                    str(count), va='center', fontsize=10)

    else:
        ax.text(0.5, 0.5, 'No gene mentions extracted',
                ha='center', va='center', fontsize=14, transform=ax.transAxes)

    plt.tight_layout()
    plt.savefig(output_dir / 'literature_gene_frequency.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved literature_gene_frequency.png")

    # --- Generate Summary Text ---
    summary_lines = [
        f"Literature Search Summary",
        f"{'='*40}",
        f"",
        f"Total papers found: {len(papers)}",
        f"Papers with gene mentions: {sum(1 for p in papers if p.get('gene_names'))}",
        f"Unique genes identified: {len(gene_counts)}",
        f"",
        f"Top Gene Targets:",
        f"-" * 30,
    ]

    for gene, count in gene_counts.most_common(10):
        summary_lines.append(f"  {gene}: {count} papers")

    summary_lines.extend([
        f"",
        f"Sample Papers:",
        f"-" * 30,
    ])

    for paper in papers[:5]:
        pmid = paper.get('pmid', 'N/A')
        title = paper.get('title', 'No title')[:80]
        if len(paper.get('title', '')) > 80:
            title += '...'
        summary_lines.append(f"  PMID:{pmid}")
        summary_lines.append(f"    {title}")

    summary_text = '\n'.join(summary_lines)

    with open(output_dir / 'literature_summary.txt', 'w') as f:
        f.write(summary_text)
    print(f"  ✓ Saved literature_summary.txt")

    # Print summary
    print(f"\n{'='*50}")
    print(f"Literature Search Results:")
    print(f"  Total papers: {len(papers)}")
    print(f"  Unique genes: {len(gene_counts)}")
    if gene_counts:
        print(f"  Top genes: {', '.join(g for g, _ in gene_counts.most_common(5))}")
    print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate literature search visualizations'
    )
    parser.add_argument('--literature', required=True,
                        help='Path to literature search JSON')
    parser.add_argument('--output-dir', required=True,
                        help='Output directory for plots')
    args = parser.parse_args()

    plot_literature_results(args.literature, args.output_dir)


if __name__ == '__main__':
    main()
