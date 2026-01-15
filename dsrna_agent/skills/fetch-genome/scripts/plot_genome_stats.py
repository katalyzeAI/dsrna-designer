#!/usr/bin/env python3
"""Generate genome statistics visualizations."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from Bio import SeqIO

# Set style
plt.style.use('seaborn-v0_8-whitegrid')


def calculate_gc(sequence: str) -> float:
    """Calculate GC content of a sequence."""
    seq = str(sequence).upper()
    if not seq:
        return 0
    gc_count = seq.count('G') + seq.count('C')
    return gc_count / len(seq)


def plot_genome_stats(genome_fasta: str, output_dir: str) -> dict:
    """Generate genome statistics and plots."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Parsing genome from {genome_fasta}...")

    # Parse genome and calculate stats
    sequences = list(SeqIO.parse(genome_fasta, 'fasta'))

    if not sequences:
        print("ERROR: No sequences found in FASTA file")
        return {}

    lengths = [len(seq.seq) for seq in sequences]
    gc_contents = [calculate_gc(seq.seq) for seq in sequences]

    print(f"Found {len(sequences)} sequences")

    # Statistics
    stats = {
        'total_sequences': len(sequences),
        'total_length': sum(lengths),
        'mean_length': float(np.mean(lengths)),
        'median_length': float(np.median(lengths)),
        'min_length': int(min(lengths)),
        'max_length': int(max(lengths)),
        'mean_gc': float(np.mean(gc_contents)),
        'median_gc': float(np.median(gc_contents)),
        'std_gc': float(np.std(gc_contents))
    }

    # --- Plot 1: GC Distribution ---
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.hist(gc_contents, bins=50, edgecolor='black', alpha=0.7, color='#3498db')
    ax.axvline(stats['mean_gc'], color='#e74c3c', linestyle='--', linewidth=2,
               label=f"Mean: {stats['mean_gc']:.1%}")
    ax.axvline(stats['median_gc'], color='#2ecc71', linestyle=':', linewidth=2,
               label=f"Median: {stats['median_gc']:.1%}")

    ax.set_xlabel('GC Content', fontsize=12)
    ax.set_ylabel('Number of CDS', fontsize=12)
    ax.set_title('GC Content Distribution Across All CDS', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)

    # Format x-axis as percentage
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0%}'))

    plt.tight_layout()
    plt.savefig(output_dir / 'genome_gc_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved genome_gc_distribution.png")

    # --- Plot 2: Length Distribution ---
    fig, ax = plt.subplots(figsize=(10, 6))

    # Use log-scale bins for better visualization
    bins = np.logspace(np.log10(max(10, min(lengths))),
                       np.log10(max(lengths)), 50)

    ax.hist(lengths, bins=bins, edgecolor='black', alpha=0.7, color='#9b59b6')
    ax.axvline(stats['mean_length'], color='#e74c3c', linestyle='--', linewidth=2,
               label=f"Mean: {stats['mean_length']:,.0f} bp")
    ax.axvline(stats['median_length'], color='#2ecc71', linestyle=':', linewidth=2,
               label=f"Median: {stats['median_length']:,.0f} bp")

    ax.set_xscale('log')
    ax.set_xlabel('CDS Length (bp)', fontsize=12)
    ax.set_ylabel('Number of CDS', fontsize=12)
    ax.set_title('CDS Length Distribution', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_dir / 'genome_length_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved genome_length_distribution.png")

    # --- Save Stats JSON ---
    with open(output_dir / 'genome_stats.json', 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"  ✓ Saved genome_stats.json")

    # Print summary
    print(f"\n{'='*50}")
    print(f"Genome Statistics:")
    print(f"  Total CDS: {stats['total_sequences']:,}")
    print(f"  Total length: {stats['total_length']:,} bp")
    print(f"  Mean length: {stats['mean_length']:,.0f} bp")
    print(f"  Mean GC: {stats['mean_gc']:.1%}")
    print(f"{'='*50}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Generate genome statistics visualizations'
    )
    parser.add_argument('--genome', required=True,
                        help='Path to genome FASTA file')
    parser.add_argument('--output-dir', required=True,
                        help='Output directory for plots')
    args = parser.parse_args()

    plot_genome_stats(args.genome, args.output_dir)


if __name__ == '__main__':
    main()
