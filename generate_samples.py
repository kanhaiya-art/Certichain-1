"""Regenerate the bundled, fictional sample certificate PDFs and manifest."""
import json
from pathlib import Path
from certichain_core import create_certificate_pdf

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"
SAMPLES.mkdir(exist_ok=True)

samples = [
    {
        "id": "CC-DEMO-2026-001",
        "name": "Foundations of Python",
        "recipient": "Aarav Mehta",
        "issuer": "CertiChain Demo Academy",
        "issued_on": "2026-08-12",
        "description": "Completed the foundational Python programming learning track.",
        "certificate_type": "sample",
        "file_name": "CC-DEMO-2026-001-python.pdf",
    },
    {
        "id": "CC-DEMO-2026-002",
        "name": "Introduction to Data Analytics",
        "recipient": "Sara Khan",
        "issuer": "CertiChain Demo Academy",
        "issued_on": "2026-09-03",
        "description": "Completed the introductory data analytics learning programme.",
        "certificate_type": "sample",
        "file_name": "CC-DEMO-2026-002-analytics.pdf",
    },
    {
        "id": "CC-DEMO-2026-003",
        "name": "Cybersecurity Essentials",
        "recipient": "Rohan Verma",
        "issuer": "Open Skills Lab (Demo)",
        "issued_on": "2026-09-21",
        "description": "Completed a demonstration course in cybersecurity fundamentals.",
        "certificate_type": "sample",
        "file_name": "CC-DEMO-2026-003-cybersecurity.pdf",
    },
]
for sample in samples:
    (SAMPLES / sample["file_name"]).write_bytes(create_certificate_pdf(sample))
(SAMPLES / "manifest.json").write_text(json.dumps(samples, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Generated {len(samples)} sample PDF certificates in {SAMPLES}")
