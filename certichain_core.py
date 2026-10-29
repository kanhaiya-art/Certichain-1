"""Core cryptographic, registry, ledger, and certificate-generation logic for CertiChain.

This is an educational local prototype. Its hash-linked ledger is tamper-evident,
not a distributed or consensus-backed production blockchain.
"""
from __future__ import annotations

import hashlib
import hmac
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import qrcode

ZERO_HASH = "0" * 64
SCHEMA_VERSION = 1
REGISTRY_FIELDS = (
    "id",
    "name",
    "recipient",
    "issuer",
    "issued_on",
    "description",
    "file_hash",
    "file_name",
    "certificate_type",
)
REGISTRATION_EVENTS = {"DEMO_CERTIFICATE_REGISTERED", "DEMO_CERTIFICATE_ISSUED"}


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase hexadecimal SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    """Serialize JSON consistently so the same record always hashes the same way."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def registry_payload(certificate: dict[str, Any]) -> dict[str, Any]:
    return {field: certificate.get(field) for field in REGISTRY_FIELDS}


def registry_digest(certificate: dict[str, Any]) -> str:
    """Hash the canonical registry metadata for one credential."""
    return sha256_bytes(canonical_json(registry_payload(certificate)))


def block_digest(block_without_hash: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json(block_without_hash))


def append_event(state: dict[str, Any], event_type: str, details: dict[str, Any]) -> dict[str, Any]:
    """Append one hash-linked event to a ledger in memory."""
    chain = state["chain"]
    previous_hash = chain[-1]["block_hash"] if chain else ZERO_HASH
    block = {
        "index": len(chain) + 1,
        "timestamp": utc_now_iso(),
        "event_type": event_type,
        "details": details,
        "previous_hash": previous_hash,
    }
    block["block_hash"] = block_digest(block)
    chain.append(block)
    return block


def verify_chain(chain: list[dict[str, Any]]) -> tuple[bool, str]:
    """Recompute every block hash and every previous-hash link."""
    previous_hash = ZERO_HASH
    for expected_index, block in enumerate(chain, start=1):
        if block.get("index") != expected_index:
            return False, f"Record {expected_index} has an invalid sequence number."
        if block.get("previous_hash") != previous_hash:
            return False, f"Record {expected_index} does not link to its predecessor."
        stored_hash = block.get("block_hash")
        unsigned = {key: value for key, value in block.items() if key != "block_hash"}
        if not isinstance(stored_hash, str) or not hmac.compare_digest(stored_hash, block_digest(unsigned)):
            return False, f"Record {expected_index} does not match its stored SHA-256 hash."
        previous_hash = stored_hash
    return True, "All block hashes and previous-hash links are valid."


def verify_registry(state: dict[str, Any]) -> tuple[bool, str]:
    """Check that certificate metadata agrees with its hash-linked registration event."""
    certificates = state.get("certificates", [])
    chain = state.get("chain", [])
    events: dict[str, dict[str, Any]] = {}
    for block in chain:
        if block.get("event_type") not in REGISTRATION_EVENTS:
            continue
        details = block.get("details", {})
        cert_id = details.get("certificate_id")
        if not cert_id or cert_id in events:
            return False, "A registration event has a missing or duplicate certificate ID."
        events[cert_id] = details

    certs_by_id: dict[str, dict[str, Any]] = {}
    for certificate in certificates:
        cert_id = certificate.get("id")
        if not cert_id or cert_id in certs_by_id:
            return False, "The certificate registry contains a missing or duplicate ID."
        if certificate.get("registry_hash") != registry_digest(certificate):
            return False, f"Registry metadata for {cert_id} has changed."
        certs_by_id[cert_id] = certificate

    if set(certs_by_id) != set(events):
        return False, "The registry and certificate-registration events do not contain the same IDs."

    for cert_id, certificate in certs_by_id.items():
        event = events[cert_id]
        if event.get("registry_hash") != certificate.get("registry_hash"):
            return False, f"Registry record {cert_id} does not match its registration event."
        if event.get("file_hash") != certificate.get("file_hash"):
            return False, f"The file fingerprint for {cert_id} differs from its registration event."
    return True, "Every registry entry matches its hash-linked registration event."


def verify_integrity(state: dict[str, Any]) -> tuple[bool, str]:
    chain_ok, chain_message = verify_chain(state.get("chain", []))
    if not chain_ok:
        return False, chain_message
    registry_ok, registry_message = verify_registry(state)
    if not registry_ok:
        return False, registry_message
    return True, "Chain and certificate registry integrity checks passed."


def save_state(ledger_path: Path, state: dict[str, Any]) -> None:
    """Atomically write the local demo ledger to avoid partial JSON writes."""
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = ledger_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp_path.replace(ledger_path)


def new_certificate_record(metadata: dict[str, Any], pdf_bytes: bytes, status: str) -> dict[str, Any]:
    certificate = {
        **metadata,
        "file_hash": sha256_bytes(pdf_bytes),
        "file_name": metadata.get("file_name", f"{metadata['id']}.pdf"),
        "certificate_type": metadata.get("certificate_type", "sample"),
        "status": status,
    }
    certificate["registry_hash"] = registry_digest(certificate)
    return certificate


def registration_details(certificate: dict[str, Any], note: str) -> dict[str, Any]:
    return {
        "certificate_id": certificate["id"],
        "certificate_name": certificate["name"],
        "recipient": certificate["recipient"],
        "issuer": certificate["issuer"],
        "issued_on": certificate["issued_on"],
        "file_name": certificate["file_name"],
        "file_hash": certificate["file_hash"],
        "registry_hash": certificate["registry_hash"],
        "note": note,
    }


def create_initial_state(app_dir: Path) -> dict[str, Any]:
    """Create the initial registry from the sample PDF files bundled with the project."""
    samples_dir = app_dir / "samples"
    manifest_path = samples_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Sample manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    state: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now_iso(),
        "certificates": [],
        "chain": [],
    }
    for item in manifest:
        file_path = samples_dir / item["file_name"]
        if not file_path.exists():
            raise FileNotFoundError(f"Sample certificate not found: {file_path}")
        pdf_bytes = file_path.read_bytes()
        certificate = new_certificate_record(item, pdf_bytes, "Preloaded sample")
        state["certificates"].append(certificate)
        append_event(
            state,
            "DEMO_CERTIFICATE_REGISTERED",
            registration_details(certificate, "Bundled fictional certificate for the teaching demonstration."),
        )
    return state


def load_state(app_dir: Path) -> tuple[dict[str, Any], Path]:
    """Load the ledger, initializing it from bundled samples on first run."""
    data_dir = app_dir / "data"
    ledger_path = data_dir / "ledger.json"
    data_dir.mkdir(parents=True, exist_ok=True)
    if not ledger_path.exists():
        state = create_initial_state(app_dir)
        save_state(ledger_path, state)
        return state, ledger_path
    state = json.loads(ledger_path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or not isinstance(state.get("certificates"), list) or not isinstance(state.get("chain"), list):
        raise ValueError("The ledger JSON has an invalid structure. Back it up before resetting it.")
    return state, ledger_path


def find_certificate_by_hash(state: dict[str, Any], digest: str) -> dict[str, Any] | None:
    for certificate in state.get("certificates", []):
        known_hash = certificate.get("file_hash", "")
        if isinstance(known_hash, str) and hmac.compare_digest(known_hash, digest):
            return certificate
    return None


def record_verification(
    state: dict[str, Any], file_name: str, file_hash: str, matched_certificate: dict[str, Any] | None
) -> dict[str, Any]:
    """Record the result without storing the uploaded file's contents."""
    matched = matched_certificate is not None
    return append_event(
        state,
        "CERTIFICATE_MATCHED" if matched else "VERIFICATION_NO_MATCH",
        {
            "file_name": Path(file_name).name[:180],
            "uploaded_file_hash": file_hash,
            "result": "MATCH" if matched else "NO_MATCH",
            "matched_certificate_id": matched_certificate["id"] if matched_certificate else None,
            "note": "Only the file hash, filename, and result are recorded; the upload is not saved by this verification action.",
        },
    )


def make_qr_png(payload: str) -> bytes:
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=5, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#14213A", back_color="#FFFFFF")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def create_certificate_pdf(metadata: dict[str, Any]) -> bytes:
    """Generate a polished landscape PDF certificate clearly labelled as a demo."""
    page_width, page_height = landscape(A4)
    output = io.BytesIO()
    doc_id = str(metadata.get("id", "CC-DEMO-UNKNOWN"))
    course = str(metadata.get("name", "Digital Skills Completion"))
    recipient = str(metadata.get("recipient", "Demo Recipient"))
    issuer = str(metadata.get("issuer", "CertiChain Demo Academy"))
    issued_on = str(metadata.get("issued_on", datetime.now().date().isoformat()))
    description = str(metadata.get("description", "Completed the demonstration learning track."))

    c = canvas.Canvas(output, pagesize=(page_width, page_height), pageCompression=1)
    c.setTitle(f"{course} — {doc_id}")
    c.setAuthor("CertiChain Educational Demonstration")
    c.setSubject("Fictional sample certificate for a blockchain and SHA-256 classroom project")

    navy = colors.HexColor("#111D35")
    navy_soft = colors.HexColor("#233552")
    teal = colors.HexColor("#0E9F83")
    mint = colors.HexColor("#B8F4DC")
    ink = colors.HexColor("#17243B")
    muted = colors.HexColor("#66748B")
    paper = colors.HexColor("#F7F9FC")
    gold = colors.HexColor("#C7A45A")

    # Background and precise double-line border.
    c.setFillColor(paper)
    c.rect(0, 0, page_width, page_height, stroke=0, fill=1)
    c.setFillColor(navy)
    c.rect(0, page_height - 10, page_width, 10, stroke=0, fill=1)
    c.setFillColor(teal)
    c.rect(0, page_height - 14, page_width, 4, stroke=0, fill=1)
    c.setStrokeColor(navy_soft)
    c.setLineWidth(1.15)
    c.rect(22, 22, page_width - 44, page_height - 44, stroke=1, fill=0)
    c.setStrokeColor(colors.HexColor("#D3DCE8"))
    c.setLineWidth(0.65)
    c.rect(28, 28, page_width - 56, page_height - 56, stroke=1, fill=0)

    # Corner accents and understated ornament.
    for x, y in ((43, 43), (page_width - 43, 43), (43, page_height - 43), (page_width - 43, page_height - 43)):
        c.setFillColor(gold)
        c.circle(x, y, 3.2, stroke=0, fill=1)
    c.setFillColor(navy)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(54, page_height - 51, "C E R T I C H A I N")
    c.setFillColor(muted)
    c.setFont("Helvetica", 7.5)
    c.drawString(54, page_height - 65, "CREDENTIAL INTEGRITY · EDUCATIONAL PROTOTYPE")

    # Demo ribbon.
    ribbon_w, ribbon_h = 146, 24
    ribbon_x, ribbon_y = page_width - 54 - ribbon_w, page_height - 62
    c.setFillColor(mint)
    c.roundRect(ribbon_x, ribbon_y, ribbon_w, ribbon_h, 7, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#086C59"))
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(ribbon_x + ribbon_w / 2, ribbon_y + 8, "DEMO CERTIFICATE")

    center = page_width * 0.5
    c.setFillColor(teal)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(center, page_height - 126, "CERTIFICATE OF COMPLETION")
    c.setFillColor(navy)
    c.setFont("Helvetica-Bold", 29)
    c.drawCentredString(center, page_height - 164, "Certificate of Achievement")
    c.setStrokeColor(gold)
    c.setLineWidth(1.5)
    c.line(center - 67, page_height - 180, center + 67, page_height - 180)

    c.setFillColor(muted)
    c.setFont("Helvetica", 11)
    c.drawCentredString(center, page_height - 211, "This certificate is presented to")
    c.setFillColor(navy)
    c.setFont("Helvetica-Bold", 25)
    c.drawCentredString(center, page_height - 246, recipient)

    c.setStrokeColor(colors.HexColor("#D6E0EA"))
    c.setLineWidth(0.8)
    c.line(center - 170, page_height - 258, center + 170, page_height - 258)

    c.setFillColor(muted)
    c.setFont("Helvetica", 10)
    c.drawCentredString(center, page_height - 286, "for completing the demonstration programme")
    c.setFillColor(teal)
    c.setFont("Helvetica-Bold", 17)
    c.drawCentredString(center, page_height - 313, course[:74])

    c.setFillColor(muted)
    c.setFont("Helvetica", 8.5)
    # Keep the description to one well-formed line to avoid overflow on long metadata.
    if len(description) > 110:
        description = description[:107].rstrip() + "..."
    c.drawCentredString(center, page_height - 334, description)

    # Metadata band.
    band_x, band_y, band_w, band_h = 104, 82, page_width - 208, 58
    c.setFillColor(colors.HexColor("#EDF2F8"))
    c.roundRect(band_x, band_y, band_w, band_h, 9, stroke=0, fill=1)
    c.setFillColor(muted)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(band_x + 18, band_y + 37, "ISSUED BY")
    c.drawString(band_x + 18, band_y + 17, "CERTIFICATE ID")
    c.drawCentredString(band_x + band_w * 0.57, band_y + 37, "ISSUE DATE")
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(band_x + 80, band_y + 37, issuer[:34])
    c.setFont("Courier-Bold", 8)
    c.drawString(band_x + 80, band_y + 17, doc_id[:36])
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(band_x + band_w * 0.57, band_y + 17, issued_on)

    # QR encodes demo metadata only; it is not a digital signature.
    qr_payload = f"CERTICHAIN-DEMO\nID:{doc_id}\nPROGRAM:{course}\nRECIPIENT:{recipient}\nISSUED:{issued_on}"
    qr_png = make_qr_png(qr_payload)
    qr_image = io.BytesIO(qr_png)
    qr_size = 63
    qr_x, qr_y = page_width - 54 - qr_size, 68
    c.setFillColor(colors.white)
    c.roundRect(qr_x - 5, qr_y - 5, qr_size + 10, qr_size + 10, 6, stroke=0, fill=1)
    c.drawImage(ImageReader(qr_image), qr_x, qr_y, width=qr_size, height=qr_size, preserveAspectRatio=True, mask="auto")
    c.setFillColor(muted)
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 15, "DEMO METADATA QR")

    # Explicit safety/educational notice.
    c.setFillColor(colors.HexColor("#8D3F38"))
    c.setFont("Helvetica-Bold", 7.4)
    c.drawCentredString(center, 48, "FICTIONAL SAMPLE · NOT AN OFFICIAL QUALIFICATION OR IDENTITY DOCUMENT")
    c.showPage()
    c.save()
    return output.getvalue()
