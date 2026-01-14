"""dsRNA Designer Tools - 7 tools for the RNAi design workflow."""

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx
from langchain_core.tools import tool

# Base URLs for NCBI APIs
NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_FTP_BASE = "https://ftp.ncbi.nlm.nih.gov"

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"


def slugify(name: str) -> str:
    """Convert species name to filesystem-safe slug."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def ensure_output_dir(species: str) -> Path:
    """Create and return the output directory for a species."""
    species_dir = OUTPUT_DIR / slugify(species)
    species_dir.mkdir(parents=True, exist_ok=True)
    return species_dir


@tool
def fetch_genome(species: str) -> dict[str, Any]:
    """Fetch CDS sequences for a species from NCBI.

    Downloads the coding sequences (CDS) for the target species from NCBI's
    RefSeq database. This provides the gene sequences needed for dsRNA design.

    Args:
        species: Scientific name (e.g., "Drosophila suzukii")

    Returns:
        Dictionary with:
        - success: Whether the fetch succeeded
        - genome_path: Path to downloaded FASTA file
        - taxid: NCBI Taxonomy ID
        - assembly_id: RefSeq assembly accession
        - gene_count: Number of CDS sequences downloaded
        - error: Error message if failed
    """
    output_dir = ensure_output_dir(species)
    genome_path = output_dir / "genome.fasta"

    try:
        # Step 1: Resolve species name to TaxID
        search_url = f"{NCBI_BASE}/esearch.fcgi"
        params = {
            "db": "taxonomy",
            "term": species,
            "retmode": "json",
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.get(search_url, params=params)
            response.raise_for_status()
            data = response.json()

        id_list = data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return {
                "success": False,
                "error": f"Species '{species}' not found in NCBI Taxonomy",
            }

        taxid = id_list[0]

        # Step 2: Find RefSeq assembly for this species
        assembly_params = {
            "db": "assembly",
            "term": f"txid{taxid}[Organism:exp] AND latest_refseq[filter]",
            "retmode": "json",
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.get(search_url, params=assembly_params)
            response.raise_for_status()
            data = response.json()

        assembly_ids = data.get("esearchresult", {}).get("idlist", [])
        if not assembly_ids:
            # Try without latest_refseq filter
            assembly_params["term"] = f"txid{taxid}[Organism:exp]"
            response = client.get(search_url, params=assembly_params)
            response.raise_for_status()
            data = response.json()
            assembly_ids = data.get("esearchresult", {}).get("idlist", [])

        if not assembly_ids:
            return {
                "success": False,
                "error": f"No genome assembly found for TaxID {taxid}",
            }

        assembly_id = assembly_ids[0]

        # Step 3: Get assembly summary to find FTP path
        summary_url = f"{NCBI_BASE}/esummary.fcgi"
        summary_params = {
            "db": "assembly",
            "id": assembly_id,
            "retmode": "json",
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.get(summary_url, params=summary_params)
            response.raise_for_status()
            data = response.json()

        result = data.get("result", {}).get(assembly_id, {})
        ftp_path = result.get("ftppath_refseq") or result.get("ftppath_genbank")
        accession = result.get("assemblyaccession", assembly_id)

        if not ftp_path:
            return {
                "success": False,
                "error": f"No FTP path found for assembly {assembly_id}",
            }

        # Step 4: Download CDS FASTA
        # Convert FTP path to HTTPS
        ftp_path = ftp_path.replace("ftp://", "https://")
        assembly_name = ftp_path.split("/")[-1]
        cds_url = f"{ftp_path}/{assembly_name}_cds_from_genomic.fna.gz"

        with httpx.Client(timeout=300.0, follow_redirects=True) as client:
            response = client.get(cds_url)
            if response.status_code == 404:
                # Try alternative: rna.fna.gz
                rna_url = f"{ftp_path}/{assembly_name}_rna.fna.gz"
                response = client.get(rna_url)

            response.raise_for_status()

            # Decompress and save
            import gzip

            content = gzip.decompress(response.content)
            genome_path.write_bytes(content)

        # Count sequences
        gene_count = content.decode().count(">")

        return {
            "success": True,
            "genome_path": str(genome_path),
            "taxid": taxid,
            "assembly_id": accession,
            "gene_count": gene_count,
        }

    except httpx.HTTPError as e:
        return {"success": False, "error": f"HTTP error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def literature_search(species: str) -> dict[str, Any]:
    """Search PubMed for known RNAi targets in this species.

    Queries PubMed for published research on RNAi/dsRNA in the target species
    and extracts gene names from abstracts.

    Args:
        species: Scientific name (e.g., "Drosophila suzukii")

    Returns:
        Dictionary with:
        - success: Whether the search succeeded
        - hits: List of {pmid, title, gene_names, abstract_snippet}
        - total_found: Total papers matching query
        - error: Error message if failed
    """
    output_dir = ensure_output_dir(species)

    try:
        # Search PubMed for RNAi papers on this species
        search_url = f"{NCBI_BASE}/esearch.fcgi"
        query = f'"{species}"[Title/Abstract] AND (RNAi OR dsRNA OR "RNA interference" OR "gene silencing")'

        params = {
            "db": "pubmed",
            "term": query,
            "retmax": 20,
            "retmode": "json",
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.get(search_url, params=params)
            response.raise_for_status()
            data = response.json()

        pmids = data.get("esearchresult", {}).get("idlist", [])
        total_found = int(data.get("esearchresult", {}).get("count", 0))

        if not pmids:
            return {
                "success": True,
                "hits": [],
                "total_found": 0,
                "message": f"No RNAi literature found for {species}",
            }

        # Fetch abstracts
        fetch_url = f"{NCBI_BASE}/efetch.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "rettype": "abstract",
            "retmode": "xml",
        }

        with httpx.Client(timeout=60.0) as client:
            response = client.get(fetch_url, params=fetch_params)
            response.raise_for_status()

        # Parse XML for abstracts
        import xml.etree.ElementTree as ET

        root = ET.fromstring(response.content)
        hits = []

        # Common RNAi target gene patterns
        gene_patterns = [
            r"\b(v-?ATPase|vha\d+|ATP6V\w+)\b",
            r"\b(chitin\s*synthase|ChS|CHS\d?)\b",
            r"\b(acetylcholinesterase|AChE|Ace)\b",
            r"\b(tubulin|TUB\w*)\b",
            r"\b(actin|ACT\d?)\b",
            r"\b(ribosomal\s*protein|Rp[LS]\d+)\b",
            r"\b(cytochrome\s*P450|CYP\w+)\b",
            r"\b(ecdysone\s*receptor|EcR)\b",
            r"\b(juvenile\s*hormone|JH\w*)\b",
            r"\b(trehalase|TRE\d?)\b",
            r"\b(laccase|Lac\d?)\b",
            r"\b(aquaporin|AQP\d?)\b",
        ]
        gene_regex = re.compile("|".join(gene_patterns), re.IGNORECASE)

        for article in root.findall(".//PubmedArticle"):
            pmid_elem = article.find(".//PMID")
            title_elem = article.find(".//ArticleTitle")
            abstract_elem = article.find(".//AbstractText")

            pmid = pmid_elem.text if pmid_elem is not None else ""
            title = title_elem.text if title_elem is not None else ""
            abstract = abstract_elem.text if abstract_elem is not None else ""

            # Extract gene names from title and abstract
            text = f"{title} {abstract}"
            gene_matches = gene_regex.findall(text)
            gene_names = list(set(match for match in gene_matches if match))

            hits.append(
                {
                    "pmid": pmid,
                    "title": title,
                    "gene_names": gene_names,
                    "abstract_snippet": abstract[:500] + "..."
                    if len(abstract) > 500
                    else abstract,
                }
            )

        # Save results
        results_path = output_dir / "literature_search.json"
        results_path.write_text(json.dumps(hits, indent=2))

        return {
            "success": True,
            "hits": hits,
            "total_found": total_found,
            "results_path": str(results_path),
        }

    except httpx.HTTPError as e:
        return {"success": False, "error": f"HTTP error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def identify_essential_genes(
    species: str, genome_path: str, literature_genes: list[str] | None = None
) -> dict[str, Any]:
    """Identify essential genes in the target species genome.

    Uses orthology to known essential genes and literature evidence to rank
    genes by their essentiality (likelihood that silencing kills the pest).

    Args:
        species: Scientific name for output directory
        genome_path: Path to CDS FASTA from fetch_genome
        literature_genes: Optional list of gene names from literature_search

    Returns:
        Dictionary with:
        - success: Whether identification succeeded
        - genes: List of {gene_id, gene_name, function, score, evidence, sequence}
        - error: Error message if failed
    """
    output_dir = ensure_output_dir(species)
    literature_genes = literature_genes or []

    try:
        # Load curated essential genes database
        essential_genes_path = DATA_DIR / "essential_genes.json"
        if not essential_genes_path.exists():
            return {
                "success": False,
                "error": f"Essential genes database not found at {essential_genes_path}",
            }

        with open(essential_genes_path) as f:
            essential_db = json.load(f)

        # Parse the target genome
        from Bio import SeqIO

        genome_sequences = {}
        for record in SeqIO.parse(genome_path, "fasta"):
            genome_sequences[record.id] = {
                "id": record.id,
                "description": record.description,
                "sequence": str(record.seq),
                "length": len(record.seq),
            }

        # Find matches between genome and essential genes
        # This is a simplified text-based matching - in production, use BLAST
        candidates = []

        for gene in essential_db.get("genes", []):
            gene_name = gene["name"].lower()
            aliases = [a.lower() for a in gene.get("aliases", [])]
            all_names = [gene_name] + aliases

            # Search genome annotations for matches
            for seq_id, seq_data in genome_sequences.items():
                desc_lower = seq_data["description"].lower()

                # Check if any gene name/alias appears in the sequence description
                matched = False
                for name in all_names:
                    if name in desc_lower or name.replace("-", "") in desc_lower:
                        matched = True
                        break

                if matched:
                    # Calculate score based on evidence
                    score = 0.5  # Base score for ortholog match

                    # Boost for literature support
                    if any(
                        name in [g.lower() for g in literature_genes]
                        for name in all_names
                    ):
                        score += 0.3

                    # Boost for being essential in multiple species
                    essential_count = len(gene.get("essential_in", []))
                    score += min(0.2, essential_count * 0.05)

                    candidates.append(
                        {
                            "gene_id": seq_id,
                            "gene_name": gene["name"],
                            "function": gene["function"],
                            "score": round(score, 2),
                            "evidence": {
                                "ortholog_match": True,
                                "literature_support": any(
                                    name in [g.lower() for g in literature_genes]
                                    for name in all_names
                                ),
                                "essential_in_species": gene.get("essential_in", []),
                                "references": gene.get("references", []),
                            },
                            "sequence": seq_data["sequence"],
                            "sequence_length": seq_data["length"],
                        }
                    )

        # Sort by score and take top 20
        candidates.sort(key=lambda x: x["score"], reverse=True)
        top_candidates = candidates[:20]

        # Save results
        results_path = output_dir / "essential_genes.json"
        results_path.write_text(json.dumps(top_candidates, indent=2))

        return {
            "success": True,
            "genes": top_candidates,
            "total_matches": len(candidates),
            "results_path": str(results_path),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def design_dsrna_candidates(
    gene_sequence: str,
    gene_name: str,
    gene_id: str,
    length: int = 300,
    num_candidates: int = 3,
) -> dict[str, Any]:
    """Design dsRNA sequences targeting a gene.

    Uses a sliding window approach to identify optimal dsRNA regions based on:
    - GC content (35-50% optimal)
    - Absence of poly-N runs
    - Position within CDS (avoiding UTR-proximal regions)

    Args:
        gene_sequence: CDS nucleotide sequence
        gene_name: Gene name for labeling
        gene_id: Gene identifier
        length: Target dsRNA length (200-500bp, default 300)
        num_candidates: Number of candidates to return (default 3)

    Returns:
        Dictionary with:
        - success: Whether design succeeded
        - candidates: List of {id, sequence, start, end, gc_content, score}
        - error: Error message if failed
    """
    try:
        seq = gene_sequence.upper()
        gene_length = len(seq)

        if gene_length < length:
            return {
                "success": False,
                "error": f"Gene sequence ({gene_length}bp) shorter than target length ({length}bp)",
            }

        # Sliding window analysis
        windows = []
        step = 50  # Slide by 50bp

        for start in range(0, gene_length - length + 1, step):
            end = start + length
            window_seq = seq[start:end]

            # Calculate GC content
            gc = (window_seq.count("G") + window_seq.count("C")) / length

            # Calculate score
            score = 0

            # GC content scoring (optimal 35-50%)
            if 0.35 <= gc <= 0.50:
                score += 2
            elif 0.30 <= gc <= 0.55:
                score += 1

            # Penalize poly-N runs (4+ consecutive same nucleotide)
            has_poly_n = bool(re.search(r"([ATGC])\1{3,}", window_seq))
            if not has_poly_n:
                score += 1

            # Position scoring - avoid first 75bp and last 50bp
            if start >= 75:
                score += 1
            if end <= gene_length - 50:
                score += 1

            windows.append(
                {
                    "start": start,
                    "end": end,
                    "sequence": window_seq,
                    "gc_content": round(gc, 3),
                    "has_poly_n": has_poly_n,
                    "score": score,
                }
            )

        # Sort by score and select top non-overlapping candidates
        windows.sort(key=lambda x: x["score"], reverse=True)

        candidates = []
        used_positions = set()

        for window in windows:
            if len(candidates) >= num_candidates:
                break

            # Check for overlap with already selected candidates
            window_positions = set(range(window["start"], window["end"]))
            if not window_positions.intersection(used_positions):
                candidate_id = f"{gene_name}_{len(candidates) + 1}"
                candidates.append(
                    {
                        "id": candidate_id,
                        "gene_name": gene_name,
                        "gene_id": gene_id,
                        "sequence": window["sequence"],
                        "start": window["start"],
                        "end": window["end"],
                        "length": length,
                        "gc_content": window["gc_content"],
                        "has_poly_n": window["has_poly_n"],
                        "design_score": window["score"],
                    }
                )
                used_positions.update(window_positions)

        return {
            "success": True,
            "candidates": candidates,
            "total_windows_analyzed": len(windows),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def run_offtarget_blast(
    candidates: list[dict], blast_db_dir: str | None = None
) -> dict[str, Any]:
    """Screen dsRNA candidates against human and honeybee genomes.

    Uses local BLAST+ to find potential off-target matches. Sequences with
    ≥19bp contiguous matches are flagged as unsafe per EPA guidelines.

    Args:
        candidates: List of candidate dicts with 'id' and 'sequence' keys
        blast_db_dir: Path to BLAST databases (default: data/blast_db)

    Returns:
        Dictionary with:
        - success: Whether BLAST succeeded
        - results: List of {candidate_id, human_max_match, honeybee_max_match, safe}
        - error: Error message if failed
    """
    if blast_db_dir is None:
        blast_db_dir = str(DATA_DIR / "blast_db")

    blast_db_path = Path(blast_db_dir)

    # Check if BLAST databases exist
    human_db = blast_db_path / "human_cds"
    honeybee_db = blast_db_path / "honeybee_cds"

    # Check for BLAST installation
    try:
        result = subprocess.run(
            ["blastn", "-version"], capture_output=True, text=True, check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {
            "success": False,
            "error": "BLAST+ not installed. Run: brew install blast",
        }

    # Check for databases
    if not any(blast_db_path.glob("human_cds.*")):
        return {
            "success": False,
            "error": f"Human BLAST database not found at {human_db}. Run setup_blast_db.sh first.",
        }

    if not any(blast_db_path.glob("honeybee_cds.*")):
        return {
            "success": False,
            "error": f"Honeybee BLAST database not found at {honeybee_db}. Run setup_blast_db.sh first.",
        }

    results = []

    try:
        for candidate in candidates:
            cand_id = candidate.get("id", "unknown")
            sequence = candidate.get("sequence", "")

            if not sequence:
                results.append(
                    {
                        "candidate_id": cand_id,
                        "error": "No sequence provided",
                        "safe": False,
                    }
                )
                continue

            # Create temp file for query
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".fa", delete=False
            ) as f:
                f.write(f">{cand_id}\n{sequence}\n")
                query_file = f.name

            try:
                human_max_match = _run_blast_query(query_file, str(human_db))
                honeybee_max_match = _run_blast_query(query_file, str(honeybee_db))

                # Determine safety based on EPA threshold (19bp)
                max_match = max(human_max_match, honeybee_max_match)
                if max_match >= 19:
                    safety_status = "reject"
                    safe = False
                elif max_match >= 15:
                    safety_status = "caution"
                    safe = True  # Caution but not rejected
                else:
                    safety_status = "safe"
                    safe = True

                results.append(
                    {
                        "candidate_id": cand_id,
                        "human_max_match": human_max_match,
                        "honeybee_max_match": honeybee_max_match,
                        "max_match": max_match,
                        "safety_status": safety_status,
                        "safe": safe,
                    }
                )
            finally:
                os.unlink(query_file)

        return {"success": True, "results": results}

    except Exception as e:
        return {"success": False, "error": str(e)}


def _run_blast_query(query_file: str, db_path: str) -> int:
    """Run BLAST query and return max contiguous match length."""
    try:
        result = subprocess.run(
            [
                "blastn",
                "-query",
                query_file,
                "-db",
                db_path,
                "-word_size",
                "7",
                "-outfmt",
                "6 qseqid sseqid length qstart qend sstart send",
                "-max_target_seqs",
                "100",
                "-evalue",
                "10",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if not result.stdout.strip():
            return 0

        # Parse BLAST output to find max alignment length
        max_length = 0
        for line in result.stdout.strip().split("\n"):
            parts = line.split("\t")
            if len(parts) >= 3:
                length = int(parts[2])
                max_length = max(max_length, length)

        return max_length

    except subprocess.TimeoutExpired:
        return -1  # Indicate timeout
    except Exception:
        return 0


@tool
def score_efficiency(
    candidates: list[dict], blast_results: list[dict], gene_scores: dict[str, float]
) -> dict[str, Any]:
    """Compute final efficacy and safety scores for dsRNA candidates.

    Combines sequence features, off-target analysis, and gene essentiality
    into a final ranking score.

    Args:
        candidates: dsRNA candidates from design_dsrna_candidates
        blast_results: Off-target results from run_offtarget_blast
        gene_scores: Dict mapping gene_name to essentiality score (0-1)

    Returns:
        Dictionary with:
        - success: Whether scoring succeeded
        - scored_candidates: Candidates with efficacy_score, safety_score, combined_score
        - error: Error message if failed
    """
    try:
        # Create lookup for blast results
        blast_lookup = {r["candidate_id"]: r for r in blast_results}

        scored = []
        for candidate in candidates:
            cand_id = candidate.get("id")
            gene_name = candidate.get("gene_name", "")

            # Get blast result for this candidate
            blast = blast_lookup.get(cand_id, {})

            # Calculate efficacy score (0-1)
            gc = candidate.get("gc_content", 0.4)
            gc_score = 1.0 if 0.35 <= gc <= 0.50 else (0.7 if 0.30 <= gc <= 0.55 else 0.3)

            poly_n_score = 0.0 if candidate.get("has_poly_n", False) else 1.0

            # Position score from design_score (max 5 points, normalize to 0-1)
            design_score = candidate.get("design_score", 0)
            position_score = min(design_score / 5.0, 1.0)

            # Gene essentiality
            gene_essentiality = gene_scores.get(gene_name, 0.5)

            efficacy = (
                0.3 * gc_score
                + 0.2 * poly_n_score
                + 0.2 * position_score
                + 0.3 * gene_essentiality
            )

            # Calculate safety score (0-1)
            max_match = blast.get("max_match", 0)
            if max_match >= 19:
                safety = 0.0
            elif max_match >= 15:
                safety = 0.7
            else:
                safety = 1.0

            # Combined score
            combined = efficacy * safety

            scored.append(
                {
                    **candidate,
                    "efficacy_score": round(efficacy, 3),
                    "safety_score": round(safety, 3),
                    "combined_score": round(combined, 3),
                    "human_max_match": blast.get("human_max_match", 0),
                    "honeybee_max_match": blast.get("honeybee_max_match", 0),
                    "safety_status": blast.get("safety_status", "unknown"),
                }
            )

        # Sort by combined score
        scored.sort(key=lambda x: x["combined_score"], reverse=True)

        return {"success": True, "scored_candidates": scored}

    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def generate_report(
    species: str, scored_candidates: list[dict], essential_genes: list[dict]
) -> dict[str, Any]:
    """Generate a comprehensive markdown report with ranked dsRNA candidates.

    Creates a detailed report suitable for scientific review and regulatory
    submission, including sequences, scores, and safety analysis.

    Args:
        species: Target species name
        scored_candidates: Candidates with scores from score_efficiency
        essential_genes: Gene information from identify_essential_genes

    Returns:
        Dictionary with:
        - success: Whether report generation succeeded
        - report_path: Path to generated markdown file
        - candidates_path: Path to JSON with all candidate data
        - error: Error message if failed
    """
    output_dir = ensure_output_dir(species)

    try:
        # Create gene lookup
        gene_lookup = {g["gene_id"]: g for g in essential_genes}

        # Filter to safe candidates
        safe_candidates = [c for c in scored_candidates if c.get("safety_score", 0) > 0]
        rejected_candidates = [
            c for c in scored_candidates if c.get("safety_score", 0) == 0
        ]

        # Generate markdown report
        report_lines = [
            f"# dsRNA Design Report: {species}",
            "",
            f"*Generated by dsRNA Designer*",
            "",
            "## Executive Summary",
            "",
            f"- **Target species:** {species}",
            f"- **Total candidates designed:** {len(scored_candidates)}",
            f"- **Safe candidates:** {len(safe_candidates)}",
            f"- **Rejected (off-target risk):** {len(rejected_candidates)}",
            "",
        ]

        if safe_candidates:
            top = safe_candidates[0]
            report_lines.extend(
                [
                    f"- **Top recommendation:** {top['id']} targeting {top['gene_name']}",
                    f"  - Combined score: {top['combined_score']}",
                    f"  - Max off-target match: {top.get('human_max_match', 0)}bp (human), "
                    f"{top.get('honeybee_max_match', 0)}bp (honeybee)",
                    "",
                ]
            )

        # Top candidates table
        report_lines.extend(
            [
                "## Top Candidates",
                "",
                "| Rank | ID | Target Gene | Efficacy | Safety | Combined | Status |",
                "|------|-----|-------------|----------|--------|----------|--------|",
            ]
        )

        for i, cand in enumerate(safe_candidates[:10], 1):
            status = "✅ Safe" if cand.get("safety_score", 0) == 1.0 else "⚠️ Caution"
            report_lines.append(
                f"| {i} | {cand['id']} | {cand['gene_name']} | "
                f"{cand['efficacy_score']:.2f} | {cand['safety_score']:.2f} | "
                f"{cand['combined_score']:.2f} | {status} |"
            )

        report_lines.append("")

        # Candidate details
        report_lines.extend(["## Candidate Details", ""])

        for i, cand in enumerate(safe_candidates[:5], 1):
            gene_info = gene_lookup.get(cand.get("gene_id"), {})
            report_lines.extend(
                [
                    f"### {i}. {cand['id']}",
                    "",
                    f"- **Target gene:** {cand['gene_name']}",
                    f"- **Function:** {gene_info.get('function', 'Unknown')}",
                    f"- **Position:** {cand.get('start', 0)}-{cand.get('end', 0)} ({cand.get('length', 0)}bp)",
                    f"- **GC content:** {cand.get('gc_content', 0) * 100:.1f}%",
                    f"- **Design score:** {cand.get('design_score', 0)}/5",
                    "",
                    "**Off-target analysis:**",
                    f"- Human: {cand.get('human_max_match', 0)}bp max match",
                    f"- Honeybee: {cand.get('honeybee_max_match', 0)}bp max match",
                    f"- Status: {cand.get('safety_status', 'unknown').upper()}",
                    "",
                    "**Sequence:**",
                    "```",
                    cand.get("sequence", ""),
                    "```",
                    "",
                ]
            )

        # Off-target analysis table
        report_lines.extend(
            [
                "## Off-Target Analysis",
                "",
                "| Candidate | Human (bp) | Honeybee (bp) | Status |",
                "|-----------|------------|---------------|--------|",
            ]
        )

        for cand in scored_candidates:
            status_map = {"safe": "✅ Safe", "caution": "⚠️ Caution", "reject": "❌ Reject"}
            status = status_map.get(cand.get("safety_status", ""), "Unknown")
            report_lines.append(
                f"| {cand['id']} | {cand.get('human_max_match', 0)} | "
                f"{cand.get('honeybee_max_match', 0)} | {status} |"
            )

        report_lines.append("")

        # Rejected candidates
        if rejected_candidates:
            report_lines.extend(
                [
                    "## Rejected Candidates",
                    "",
                    "The following candidates were rejected due to off-target risk (≥19bp match):",
                    "",
                ]
            )
            for cand in rejected_candidates:
                report_lines.append(
                    f"- **{cand['id']}** ({cand['gene_name']}): "
                    f"{cand.get('human_max_match', 0)}bp human, "
                    f"{cand.get('honeybee_max_match', 0)}bp honeybee"
                )
            report_lines.append("")

        # Methods
        report_lines.extend(
            [
                "## Methods",
                "",
                "### Data Sources",
                "- Genome: NCBI RefSeq",
                "- Essential genes: Database of Essential Genes (DEG), FlyBase",
                "- Off-target screening: Local BLAST+ against human (GRCh38) and honeybee (Amel_HAv3.1)",
                "",
                "### Design Parameters",
                "- dsRNA length: 300bp",
                "- Optimal GC content: 35-50%",
                "- Avoided regions: First 75bp, last 50bp of CDS",
                "- Safety threshold: <19bp contiguous match (EPA guideline)",
                "",
                "### Scoring",
                "- Efficacy score: GC content (30%), poly-N absence (20%), position (20%), gene essentiality (30%)",
                "- Safety score: 1.0 (<15bp match), 0.7 (15-18bp), 0.0 (≥19bp)",
                "- Combined score: Efficacy × Safety",
                "",
            ]
        )

        # Write report
        report_path = output_dir / "report.md"
        report_path.write_text("\n".join(report_lines))

        # Write candidates JSON
        candidates_path = output_dir / "candidates.json"
        candidates_path.write_text(json.dumps(scored_candidates, indent=2))

        return {
            "success": True,
            "report_path": str(report_path),
            "candidates_path": str(candidates_path),
            "safe_count": len(safe_candidates),
            "rejected_count": len(rejected_candidates),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
