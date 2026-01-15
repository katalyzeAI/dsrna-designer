#!/usr/bin/env python3
"""Screen dsRNA candidates against human and honeybee genomes using BLAST."""

import subprocess
import json
import tempfile
import os
import argparse
from pathlib import Path
from datetime import datetime


def check_blast_installation() -> bool:
    """Check if BLAST+ is installed."""
    try:
        result = subprocess.run(
            ['blastn', '-version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_database_exists(db_path: str) -> bool:
    """Check if BLAST database files exist."""
    # Check for at least one of the expected extensions
    extensions = ['.nhr', '.nin', '.nsq', '.ndb', '.nto']
    for ext in extensions:
        if Path(f"{db_path}{ext}").exists():
            return True
    return False


def run_blast_query(query_file: str, db_path: str, timeout: int = 60) -> int:
    """Run BLAST and return maximum alignment length."""
    try:
        result = subprocess.run(
            [
                'blastn',
                '-query', query_file,
                '-db', db_path,
                '-word_size', '7',
                '-outfmt', '6 qseqid sseqid length',
                '-max_target_seqs', '100',
                '-evalue', '10'
            ],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if not result.stdout.strip():
            return 0

        max_length = 0
        for line in result.stdout.strip().split('\n'):
            parts = line.split('\t')
            if len(parts) >= 3:
                try:
                    length = int(parts[2])
                    max_length = max(max_length, length)
                except ValueError:
                    continue

        return max_length

    except subprocess.TimeoutExpired:
        print(f"  Warning: BLAST query timed out for {query_file}")
        return -1
    except Exception as e:
        print(f"  Error running BLAST: {e}")
        return 0


def classify_safety(max_match: int) -> tuple[str, bool]:
    """Classify safety status based on match length."""
    if max_match >= 19:
        return 'reject', False
    elif max_match >= 15:
        return 'caution', True
    else:
        return 'safe', True


def blast_screen_candidates(
    candidates_path: str,
    blast_db_dir: str,
    output_path: str
) -> None:
    """Screen all candidates against human and honeybee databases."""

    # Check BLAST installation
    if not check_blast_installation():
        print("ERROR: BLAST+ is not installed or not in PATH")
        print("Install with: brew install blast (macOS) or apt install ncbi-blast+ (Ubuntu)")
        return

    # Check databases
    blast_db_path = Path(blast_db_dir)
    human_db = blast_db_path / 'human_cds'
    honeybee_db = blast_db_path / 'honeybee_cds'

    if not check_database_exists(str(human_db)):
        print(f"ERROR: Human database not found at {human_db}")
        print("Run ./setup_blast_db.sh to create databases")
        return

    if not check_database_exists(str(honeybee_db)):
        print(f"ERROR: Honeybee database not found at {honeybee_db}")
        print("Run ./setup_blast_db.sh to create databases")
        return

    # Load candidates
    with open(candidates_path) as f:
        candidates = json.load(f)

    print(f"Screening {len(candidates)} candidates against:")
    print(f"  - Human CDS: {human_db}")
    print(f"  - Honeybee CDS: {honeybee_db}")

    results = []

    for i, candidate in enumerate(candidates, 1):
        cand_id = candidate.get('id', f'candidate_{i}')
        sequence = candidate.get('sequence', '')

        print(f"\n[{i}/{len(candidates)}] Screening {cand_id}...")

        if not sequence:
            results.append({
                'candidate_id': cand_id,
                'error': 'No sequence provided',
                'human_max_match': 0,
                'honeybee_max_match': 0,
                'max_match': 0,
                'safety_status': 'error',
                'safe': False
            })
            continue

        # Write temp query file
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.fa', delete=False
        ) as f:
            f.write(f">{cand_id}\n{sequence}\n")
            query_file = f.name

        try:
            # Run BLAST against both databases
            human_max = run_blast_query(query_file, str(human_db))
            honeybee_max = run_blast_query(query_file, str(honeybee_db))

            # Handle errors
            if human_max < 0 or honeybee_max < 0:
                results.append({
                    'candidate_id': cand_id,
                    'error': 'BLAST timeout',
                    'human_max_match': max(0, human_max),
                    'honeybee_max_match': max(0, honeybee_max),
                    'max_match': max(0, human_max, honeybee_max),
                    'safety_status': 'error',
                    'safe': False
                })
                continue

            # Calculate overall max and safety
            max_match = max(human_max, honeybee_max)
            status, safe = classify_safety(max_match)

            results.append({
                'candidate_id': cand_id,
                'human_max_match': human_max,
                'honeybee_max_match': honeybee_max,
                'max_match': max_match,
                'safety_status': status,
                'safe': safe
            })

            # Status indicator
            if status == 'safe':
                print(f"  ✅ Safe (max match: {max_match} bp)")
            elif status == 'caution':
                print(f"  ⚠️  Caution (max match: {max_match} bp)")
            else:
                print(f"  ❌ Reject (max match: {max_match} bp)")

        finally:
            os.unlink(query_file)

    # Compile output
    output = {
        'success': True,
        'screening_date': datetime.now().isoformat(),
        'databases_used': ['human_cds', 'honeybee_cds'],
        'thresholds': {
            'safe': '<15 bp',
            'caution': '15-18 bp',
            'reject': '>=19 bp'
        },
        'results': results
    }

    # Write output
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    # Summary
    safe_count = sum(1 for r in results if r.get('safety_status') == 'safe')
    caution_count = sum(1 for r in results if r.get('safety_status') == 'caution')
    reject_count = sum(1 for r in results if r.get('safety_status') == 'reject')

    print(f"\n{'='*50}")
    print(f"✓ Screened {len(results)} candidates")
    print(f"  ✅ Safe: {safe_count}")
    print(f"  ⚠️  Caution: {caution_count}")
    print(f"  ❌ Rejected: {reject_count}")


def main():
    parser = argparse.ArgumentParser(
        description='Screen dsRNA candidates with BLAST'
    )
    parser.add_argument('--candidates', required=True,
                        help='Path to candidates JSON')
    parser.add_argument('--blast-db-dir', required=True,
                        help='Directory containing BLAST databases')
    parser.add_argument('--output', required=True,
                        help='Output JSON file path')
    args = parser.parse_args()

    blast_screen_candidates(args.candidates, args.blast_db_dir, args.output)


if __name__ == '__main__':
    main()
