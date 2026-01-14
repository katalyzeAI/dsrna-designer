#!/bin/bash
# Setup BLAST databases for off-target screening
# Downloads human and honeybee RefSeq CDS and builds BLAST databases

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BLAST_DB_DIR="$SCRIPT_DIR/data/blast_db"

echo "================================================"
echo "dsRNA Designer - BLAST Database Setup"
echo "================================================"

# Check for BLAST+ installation
if ! command -v makeblastdb &> /dev/null; then
    echo "ERROR: BLAST+ is not installed."
    echo "Install with: brew install blast"
    exit 1
fi

echo "BLAST+ found: $(blastn -version | head -1)"
echo ""

# Create directory
mkdir -p "$BLAST_DB_DIR"
cd "$BLAST_DB_DIR"

echo "Working directory: $BLAST_DB_DIR"
echo ""

# ================================================
# Human RefSeq CDS
# ================================================
HUMAN_RNA_URL="https://ftp.ncbi.nlm.nih.gov/refseq/H_sapiens/annotation/GRCh38_latest/refseq_identifiers/GRCh38_latest_rna.fna.gz"
HUMAN_FILE="GRCh38_latest_rna.fna"

if [ -f "human_cds.nhr" ] || [ -f "human_cds.nsq" ]; then
    echo "[Human] BLAST database already exists. Skipping download."
else
    echo "[Human] Downloading RefSeq transcripts (~150MB)..."
    curl -L -o "${HUMAN_FILE}.gz" "$HUMAN_RNA_URL"

    echo "[Human] Decompressing..."
    gunzip -f "${HUMAN_FILE}.gz"

    echo "[Human] Building BLAST database..."
    makeblastdb -in "$HUMAN_FILE" -dbtype nucl -out human_cds -title "Human RefSeq RNA (GRCh38)"

    echo "[Human] Cleaning up source file..."
    rm -f "$HUMAN_FILE"

    echo "[Human] Done!"
fi
echo ""

# ================================================
# Honeybee RefSeq CDS
# ================================================
HONEYBEE_RNA_URL="https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/003/254/395/GCF_003254395.2_Amel_HAv3.1/GCF_003254395.2_Amel_HAv3.1_rna.fna.gz"
HONEYBEE_FILE="GCF_003254395.2_Amel_HAv3.1_rna.fna"

if [ -f "honeybee_cds.nhr" ] || [ -f "honeybee_cds.nsq" ]; then
    echo "[Honeybee] BLAST database already exists. Skipping download."
else
    echo "[Honeybee] Downloading RefSeq transcripts (~15MB)..."
    curl -L -o "${HONEYBEE_FILE}.gz" "$HONEYBEE_RNA_URL"

    echo "[Honeybee] Decompressing..."
    gunzip -f "${HONEYBEE_FILE}.gz"

    echo "[Honeybee] Building BLAST database..."
    makeblastdb -in "$HONEYBEE_FILE" -dbtype nucl -out honeybee_cds -title "Honeybee RefSeq RNA (Amel_HAv3.1)"

    echo "[Honeybee] Cleaning up source file..."
    rm -f "$HONEYBEE_FILE"

    echo "[Honeybee] Done!"
fi
echo ""

# ================================================
# Verification
# ================================================
echo "================================================"
echo "Verification"
echo "================================================"

echo ""
echo "Checking databases..."

if [ -f "human_cds.nhr" ] || [ -f "human_cds.nsq" ]; then
    echo "✓ Human database: OK"
    blastdbcmd -db human_cds -info 2>/dev/null | head -3 || true
else
    echo "✗ Human database: MISSING"
fi

echo ""

if [ -f "honeybee_cds.nhr" ] || [ -f "honeybee_cds.nsq" ]; then
    echo "✓ Honeybee database: OK"
    blastdbcmd -db honeybee_cds -info 2>/dev/null | head -3 || true
else
    echo "✗ Honeybee database: MISSING"
fi

echo ""
echo "================================================"
echo "Setup complete!"
echo "================================================"
echo ""
echo "Database location: $BLAST_DB_DIR"
echo ""
echo "You can now run the dsRNA designer:"
echo "  deepagents run dsrna_agent \"Design dsRNA for Drosophila suzukii\""
echo ""
