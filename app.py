from __future__ import annotations

import copy
import html
import json
import secrets
from datetime import date
from pathlib import Path
import random

import streamlit as st

from certichain_core import (
    ZERO_HASH,
    append_event,
    create_certificate_pdf,
    find_certificate_by_hash,
    load_state,
    new_certificate_record,
    record_verification,
    registration_details,
    save_state,
    sha256_bytes,
    verify_chain,
    verify_integrity,
    verify_registry,
)

APP_DIR = Path(__file__).resolve().parent
SAMPLES_DIR = APP_DIR / "samples"
ISSUED_DIR = APP_DIR / "data" / "issued"
PAGES = ["Dashboard", "Verify certificate", "Issue demo certificate", "Ledger explorer"]

st.set_page_config(
    page_title="CertiChain — Certificate Verification",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# The theme is defined in .streamlit/config.toml; these refinements create a consistent product UI.
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"], [data-testid="stMarkdownContainer"] { font-family: 'Manrope', sans-serif; }
    .stApp { background: #08111f; }
    [data-testid="stHeader"] { background: rgba(8,17,31,.88); }
    [data-testid="stSidebar"] { background: #0c1627; border-right: 1px solid #213047; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #9fadc4; }
    [data-testid="stSidebar"] .block-container { padding-top: 1.55rem; }
    .block-container { max-width: 1480px; padding-top: 1.6rem; padding-bottom: 3.2rem; }
    .brand { display:flex; gap:11px; align-items:center; margin: 0 0 8px 0; }
    .brand-mark { width:39px; height:39px; border-radius:13px; display:flex; align-items:center; justify-content:center; background:linear-gradient(145deg,#7cf0bf,#27b991); color:#072014; font-weight:900; font-size:24px; box-shadow:0 7px 22px rgba(39,185,145,.16); }
    .brand-name { color:#f2f6ff; font-weight:800; font-size:1.34rem; letter-spacing:-.055em; line-height:1.1; }
    .brand-sub { color:#6f819d; font-size:.62rem; letter-spacing:.16em; font-weight:800; margin-top:5px; }
    .eyebrow { font-size:.69rem; letter-spacing:.17em; color:#69e9b5; font-weight:800; text-transform:uppercase; margin-bottom:11px; }
    .hero { position:relative; overflow:hidden; background: radial-gradient(circle at 86% 20%,rgba(65,224,166,.13),transparent 28%), linear-gradient(120deg,#13223a 0%,#0e192b 56%,#101c2e 100%); border:1px solid #293b55; border-radius:22px; padding:31px 34px 30px 34px; margin:0 0 23px 0; }
    .hero:after { content:''; position:absolute; width:235px; height:235px; right:-100px; bottom:-158px; border:1px solid rgba(106,232,181,.16); border-radius:50%; box-shadow:0 0 0 28px rgba(106,232,181,.025),0 0 0 58px rgba(106,232,181,.02); }
    .hero h1 { color:#f4f7ff; font-size:clamp(2rem,3.4vw,3.05rem); font-weight:800; letter-spacing:-.065em; line-height:1.08; margin:0 0 12px 0; max-width:850px; }
    .hero p { color:#aab8cd; max-width:850px; line-height:1.75; margin:0; font-size:.94rem; }
    .hero-tag { display:inline-flex; align-items:center; gap:7px; border:1px solid #2c624f; background:rgba(29,100,75,.23); color:#8cf4c8; border-radius:999px; font-size:.68rem; font-weight:800; letter-spacing:.08em; padding:6px 10px; margin-bottom:15px; }
    .dot { width:6px; height:6px; display:inline-block; border-radius:50%; background:#65edb2; box-shadow:0 0 9px rgba(101,237,178,.7); }
    .stat-card { min-height:138px; border-radius:17px; border:1px solid #26364e; padding:19px 20px 17px; background:linear-gradient(150deg,#121f33,#0e1929); }
    .stat-label { color:#9aaac1; font-size:.72rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }
    .stat-value { color:#f3f7ff; font-size:2.05rem; font-weight:800; letter-spacing:-.055em; line-height:1.25; margin-top:10px; }
    .stat-note { color:#6be6b4; font-size:.72rem; font-weight:600; margin-top:4px; }
    .surface { background:#0e1929; border:1px solid #26364e; border-radius:17px; padding:20px 22px; margin-bottom:15px; }
    .surface-title { color:#f0f5ff; font-size:1.02rem; font-weight:800; letter-spacing:-.025em; margin-bottom:6px; }
    .surface-sub { color:#92a2bb; font-size:.82rem; line-height:1.65; }
    .sample-card { background:linear-gradient(145deg,#111f33,#0d1727); border:1px solid #293a53; border-radius:16px; padding:17px 17px 15px; height:100%; }
    .sample-kind { color:#69e8b4; text-transform:uppercase; letter-spacing:.12em; font-size:.63rem; font-weight:800; }
    .sample-title { color:#eff4ff; font-size:1rem; font-weight:800; margin:8px 0 6px; line-height:1.35; }
    .sample-person { color:#a9b6c9; font-size:.81rem; margin-bottom:12px; }
    .tiny-label { color:#71839e; font-size:.62rem; text-transform:uppercase; letter-spacing:.12em; font-weight:800; margin:11px 0 5px; }
    .hash { color:#8bf2c5; font-family:'DM Mono',monospace; overflow-wrap:anywhere; font-size:.72rem; line-height:1.7; }
    .mono { font-family:'DM Mono',monospace; }
    .pill-good { display:inline-block; color:#83f1c4; background:#102e24; border:1px solid #2b614b; border-radius:7px; padding:5px 8px; font-size:.7rem; font-weight:800; }
    .pill-warn { display:inline-block; color:#ffcf87; background:#332718; border:1px solid #65502f; border-radius:7px; padding:5px 8px; font-size:.7rem; font-weight:800; }
    .pill-bad { display:inline-block; color:#ffaaaa; background:#351d29; border:1px solid #743b4a; border-radius:7px; padding:5px 8px; font-size:.7rem; font-weight:800; }
    .step-number { color:#6ae8b4; font-size:.78rem; font-weight:900; letter-spacing:.08em; margin-bottom:10px; }
    .step-title { color:#edf3ff; font-size:.92rem; font-weight:800; margin-bottom:7px; }
    .step-copy { color:#9baac1; font-size:.78rem; line-height:1.7; }
    .activity-line { border-left:2px solid #2d6650; padding:2px 0 14px 15px; margin-left:5px; }
    .activity-event { color:#eaf1ff; font-size:.83rem; font-weight:800; }
    .activity-meta { color:#7e90aa; font-size:.69rem; margin-top:4px; }
    .callout { background:#10251f; border:1px solid #24533f; border-radius:13px; padding:14px 16px; color:#b6f7dc; font-size:.82rem; line-height:1.65; margin:12px 0; }
    .notice { background:#201d19; border:1px solid #5c4b34; border-radius:13px; padding:14px 16px; color:#efd3a4; font-size:.8rem; line-height:1.65; margin:12px 0; }
    .plain-note { color:#9aabc3; font-size:.77rem; line-height:1.7; }
    div.stButton > button, div.stDownloadButton > button { min-height:2.7rem; border-radius:10px; font-weight:800; transition:all .18s ease; }
    div.stButton > button[kind="primary"], div.stDownloadButton > button[kind="primary"] { background:#65e8b2; border:1px solid #65e8b2; color:#071b12; }
    div.stButton > button[kind="primary"]:hover, div.stDownloadButton > button[kind="primary"]:hover { background:#87f2c4; border-color:#87f2c4; color:#071b12; }
    div.stButton > button[kind="secondary"], div.stDownloadButton > button[kind="secondary"] { background:#15243a; border:1px solid #334660; color:#eaf1ff; }
    [data-testid="stDataFrame"] { border:1px solid #2a3a52; border-radius:12px; overflow:hidden; }
    [data-testid="stExpander"] { border-color:#293a53 !important; border-radius:12px !important; }
    [data-baseweb="tab-list"] { gap:8px; }
    [data-baseweb="tab"] { background:#101c2d; border-radius:9px 9px 0 0; }
    [data-testid="stAlert"] { border-radius:12px; }
    hr { border-color:#25364d; }
    footer { visibility:hidden; }
    #MainMenu { visibility:hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def hero(kicker: str, title: str, description: str) -> None:
    st.markdown(
        f"<div class='hero'><div class='eyebrow'>{esc(kicker)}</div><div class='hero-tag'><span class='dot'></span> CERTIFICATE INTEGRITY LAB · DEMO ENVIRONMENT</div><h1>{esc(title)}</h1><p>{esc(description)}</p></div>",
        unsafe_allow_html=True,
    )


def stat_card(label: str, value: object, note: str) -> None:
    st.markdown(
        f"<div class='stat-card'><div class='stat-label'>{esc(label)}</div><div class='stat-value'>{esc(value)}</div><div class='stat-note'>{esc(note)}</div></div>",
        unsafe_allow_html=True,
    )


def surface(title: str, subtitle: str | None = None) -> None:
    sub = f"<div class='surface-sub'>{esc(subtitle)}</div>" if subtitle else ""
    st.markdown(f"<div class='surface'><div class='surface-title'>{esc(title)}</div>{sub}</div>", unsafe_allow_html=True)


def short_hash(value: str, length: int = 18) -> str:
    return value if len(value) <= length else value[:length] + "…"


def event_title(event_type: str) -> str:
    labels = {
        "DEMO_CERTIFICATE_REGISTERED": "Sample certificate registered",
        "DEMO_CERTIFICATE_ISSUED": "Demo certificate issued",
        "CERTIFICATE_MATCHED": "Certificate file matched",
        "VERIFICATION_NO_MATCH": "Verification returned no match",
    }
    return labels.get(event_type, event_type.replace("_", " ").title())


def event_reference(block: dict) -> str:
    details = block.get("details", {})
    return str(details.get("certificate_id") or details.get("file_name") or "Ledger event")


def set_navigation(target: str) -> None:
    # Streamlit callbacks run before widgets are rebuilt, so changing the radio state here is safe.
    st.session_state["navigation"] = target


def navigation_button(label: str, target: str, primary: bool = False, key: str | None = None) -> None:
    st.button(
        label,
        use_container_width=True,
        type="primary" if primary else "secondary",
        key=key,
        on_click=set_navigation,
        args=(target,),
    )


def render_verification_result(result: dict, state: dict, ledger_path: Path) -> None:
    if result.get("match"):
        cert = result["match"]
        st.markdown("<div class='callout'><b>EXACT FILE MATCH</b><br>The uploaded bytes have the same SHA-256 fingerprint as a credential registered in this demo registry.</div>", unsafe_allow_html=True)
        left, right = st.columns([1.2, 1])
        with left:
            st.markdown("<div class='surface'><div class='tiny-label'>VERIFICATION RESULT</div><h2 style='color:#81efbd;margin:4px 0 6px'>MATCH FOUND</h2><div class='surface-sub'>The fingerprint matches a registered sample or demo credential.</div></div>", unsafe_allow_html=True)
        with right:
            st.markdown(
                f"<div class='surface'><div class='tiny-label'>REGISTRY ENTRY</div><div class='surface-title'>{esc(cert['name'])}</div><div class='surface-sub'>{esc(cert['recipient'])} · {esc(cert['issuer'])}</div><div class='tiny-label'>CERTIFICATE ID</div><div class='hash'>{esc(cert['id'])}</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown("<div class='notice'><b>NO EXACT MATCH</b><br>This file's fingerprint is not present in the current registry. It may be unregistered, edited, re-exported, or otherwise different. This result alone does not establish fraud.</div>", unsafe_allow_html=True)
    with st.expander("Inspect fingerprint and ledger receipt", expanded=True):
        st.markdown("<div class='tiny-label'>SHA-256 OF UPLOADED FILE</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='hash'>{esc(result['file_hash'])}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='tiny-label'>LEDGER BLOCK #{result['block_index']}</div><div class='hash'>{esc(result['block_hash'])}</div>", unsafe_allow_html=True)
        st.caption(f"Filename: {result['file_name']} · The uploaded file's content was not saved by the verification action.")


def process_verification(file_bytes: bytes, filename: str, state: dict, ledger_path: Path) -> dict:
    digest = sha256_bytes(file_bytes)
    match = find_certificate_by_hash(state, digest)
    block = record_verification(state, filename, digest, match)
    save_state(ledger_path, state)
    return {
        "file_name": Path(filename).name,
        "file_hash": digest,
        "match": match,
        "block_index": block["index"],
        "block_hash": block["block_hash"],
    }


# Load the persistent local ledger. Corrupt JSON is handled with a clear recovery instruction.
try:
    state, LEDGER_PATH = load_state(APP_DIR)
except Exception as exc:
    st.error("CertiChain could not load its ledger.")
    st.code(str(exc))
    st.info("Back up the `data` folder before replacing or resetting `data/ledger.json`.")
    st.stop()

chain_ok, chain_message = verify_chain(state.get("chain", []))
registry_ok, registry_message = verify_registry(state)
integrity_ok = chain_ok and registry_ok

if "navigation" not in st.session_state:
    st.session_state["navigation"] = "Dashboard"

with st.sidebar:
    st.markdown(
        "<div class='brand'><div class='brand-mark'>C</div><div><div class='brand-name'>CertiChain</div><div class='brand-sub'>CERTIFICATE INTEGRITY LAB</div></div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    st.caption("Certificate verification demo")
    st.markdown("---")
    page = st.radio("WORKSPACE", PAGES, key="navigation", label_visibility="visible")
    st.markdown("---")
    st.markdown("<div class='tiny-label'>LOCAL LEDGER HEALTH</div>", unsafe_allow_html=True)
    if integrity_ok:
        st.markdown("<div class='pill-good'>● INTEGRITY CHECK PASSED</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='pill-bad'>● INTEGRITY ISSUE FOUND</div>", unsafe_allow_html=True)
    st.caption(f"{len(state['chain'])} blocks · {len(state['certificates'])} registered files")
    st.markdown("---")
    st.markdown("<div class='plain-note'>SHA-256 · Linked records · Demo certificates</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# DASHBOARD
# -----------------------------------------------------------------------------
if page == "Dashboard":
    hero(
        "CERTIFICATE VERIFICATION",
        "Check a certificate file.",
        "Compare its SHA-256 fingerprint with registered demo certificates. Inspect the linked record history.",
    )

    blocks = state["chain"]
    registrations = sum(1 for b in blocks if b["event_type"] in {"DEMO_CERTIFICATE_REGISTERED", "DEMO_CERTIFICATE_ISSUED"})
    matches = sum(1 for b in blocks if b["event_type"] == "CERTIFICATE_MATCHED")
    attempts = sum(1 for b in blocks if b["event_type"] in {"CERTIFICATE_MATCHED", "VERIFICATION_NO_MATCH"})
    success_rate = f"{round(matches / attempts * 100)}%" if attempts else "—"

    metric_cols = st.columns(4, gap="medium")
    with metric_cols[0]: stat_card("Registered credentials", len(state["certificates"]), "Fictional demo registry")
    with metric_cols[1]: stat_card("Ledger blocks", len(blocks), "Append-only event history")
    with metric_cols[2]: stat_card("Successful matches", matches, f"{success_rate} match rate across checks")
    with metric_cols[3]: stat_card("Integrity status", "PASS" if integrity_ok else "REVIEW", "Chain + registry checks")

    st.write("")
    left, right = st.columns([1.16, 0.84], gap="large")
    with left:
        surface("Start a live demonstration", "A short route from certificate file to auditable record.")
        action_left, action_right = st.columns(2)
        with action_left:
            navigation_button("Verify a certificate  →", "Verify certificate", primary=True, key="dash_verify")
        with action_right:
            navigation_button("Generate demo certificate  →", "Issue demo certificate", key="dash_issue")
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        step1, step2, step3 = st.columns(3, gap="small")
        with step1:
            st.markdown("<div class='surface' style='height:156px'><div class='step-number'>01 / FINGERPRINT</div><div class='step-title'>Hash the file</div><div class='step-copy'>SHA-256 converts the exact file bytes into a fixed-length fingerprint.</div></div>", unsafe_allow_html=True)
        with step2:
            st.markdown("<div class='surface' style='height:156px'><div class='step-number'>02 / COMPARE</div><div class='step-title'>Check registry</div><div class='step-copy'>The fingerprint is compared against registered demo files.</div></div>", unsafe_allow_html=True)
        with step3:
            st.markdown("<div class='surface' style='height:156px'><div class='step-number'>03 / RECORD</div><div class='step-title'>Link the event</div><div class='step-copy'>The result is recorded in a hash-linked history for inspection.</div></div>", unsafe_allow_html=True)
    with right:
        surface("System integrity", "The app recalculates the record chain instead of trusting a saved status flag.")
        if integrity_ok:
            st.markdown("<div class='callout'><b>ALL CHECKS PASSED</b><br>The record hashes, previous-hash links, and registry references are consistent.</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='notice'><b>INTEGRITY CHECK NEEDS REVIEW</b><br>{esc(chain_message if not chain_ok else registry_message)}</div>", unsafe_allow_html=True)
        latest_hash = blocks[-1]["block_hash"] if blocks else ZERO_HASH
        st.markdown("<div class='tiny-label'>LATEST BLOCK FINGERPRINT</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='hash'>{esc(latest_hash)}</div>", unsafe_allow_html=True)
        st.markdown("<div class='tiny-label'>GENESIS PREVIOUS HASH</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='hash'>{ZERO_HASH}</div>", unsafe_allow_html=True)

    st.write("")
    st.markdown("## Sample certificates")
    st.caption("Download a PDF, then verify the unchanged file.")
    manifest = json.loads((SAMPLES_DIR / "manifest.json").read_text(encoding="utf-8"))
    sample_cols = st.columns(3, gap="medium")
    for index, sample in enumerate(manifest):
        with sample_cols[index % 3]:
            certificate = next((c for c in state["certificates"] if c["id"] == sample["id"]), None)
            st.markdown(
                f"<div class='sample-card'><div class='sample-kind'>PRELOADED SAMPLE · PDF</div><div class='sample-title'>{esc(sample['name'])}</div><div class='sample-person'>{esc(sample['recipient'])}</div><div class='tiny-label'>CERTIFICATE ID</div><div class='hash'>{esc(sample['id'])}</div><div class='tiny-label'>SHA-256 FINGERPRINT</div><div class='hash'>{esc(short_hash(certificate['file_hash'], 24) if certificate else 'Not registered')}</div></div>",
                unsafe_allow_html=True,
            )
            sample_path = SAMPLES_DIR / sample["file_name"]
            st.download_button(
                "Download sample PDF",
                data=sample_path.read_bytes(),
                file_name=sample["file_name"],
                mime="application/pdf",
                key=f"download_{sample['id']}",
                use_container_width=True,
            )

    st.write("")
    surface("Recent ledger activity", "The newest events appear first. Open the explorer to inspect full record data.")
    recent = []
    for block in reversed(blocks[-6:]):
        details = block.get("details", {})
        result = details.get("result", "—")
        recent.append({
            "Block": block["index"],
            "Event": event_title(block["event_type"]),
            "Reference": event_reference(block),
            "Result": result,
            "Block hash": short_hash(block["block_hash"], 18),
        })
    if recent:
        st.dataframe(recent, hide_index=True, use_container_width=True)
    else:
        st.caption("No ledger activity yet.")
    st.markdown("<div class='notice'><b>Demo limitation:</b> a match confirms identical file bytes, not the real-world identity of an issuer. This is not a decentralized blockchain.</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# VERIFY CERTIFICATE
# -----------------------------------------------------------------------------
elif page == "Verify certificate":
    hero(
        "VERIFY",
        "Check a certificate.",
        "Upload a file or test a sample. CertiChain compares its SHA-256 fingerprint with the registry.",
    )
    st.markdown("<div class='surface'><div class='surface-title'>Choose a verification route</div><div class='surface-sub'>For a guaranteed demo, use one of the bundled PDFs unchanged. Any change to the file bytes creates a different fingerprint.</div></div>", unsafe_allow_html=True)
    upload_tab, sample_tab = st.tabs(["Upload a file", "Test a preloaded sample"])
    with upload_tab:
        uploaded = st.file_uploader("Certificate file", type=["pdf", "png", "jpg", "jpeg", "txt"], help="Supported demo formats: PDF, PNG, JPEG, or TXT. The app records the hash and outcome, not the uploaded file contents.")
        if uploaded is not None:
            file_bytes = uploaded.getvalue()
            digest = sha256_bytes(file_bytes)
            meta1, meta2 = st.columns([1, 2])
            with meta1:
                st.markdown("<div class='surface'><div class='tiny-label'>FILE NAME</div><div class='surface-title' style='overflow-wrap:anywhere'>" + esc(uploaded.name) + "</div><div class='surface-sub'>" + f"{len(file_bytes):,}" + " bytes</div></div>", unsafe_allow_html=True)
            with meta2:
                st.markdown("<div class='surface'><div class='tiny-label'>COMPUTED SHA-256</div><div class='hash'>" + esc(digest) + "</div><div class='surface-sub' style='margin-top:8px'>This digest changes if even one file byte changes.</div></div>", unsafe_allow_html=True)
            if st.button("Run certificate verification", type="primary", use_container_width=True, key="upload_verify"):
                result = process_verification(file_bytes, uploaded.name, state, LEDGER_PATH)
                st.session_state["last_upload_result"] = result
            last_result = st.session_state.get("last_upload_result")
            if last_result and last_result.get("file_hash") == digest:
                render_verification_result(last_result, state, LEDGER_PATH)
        else:
            st.markdown("<div class='surface'><div class='surface-title'>Waiting for a file</div><div class='surface-sub'>Choose a certificate above. You can also use the sample-testing tab to see a successful verification without browsing for a file.</div></div>", unsafe_allow_html=True)

    with sample_tab:
        manifest = json.loads((SAMPLES_DIR / "manifest.json").read_text(encoding="utf-8"))
        sample_by_label = {f"{item['name']} · {item['recipient']}": item for item in manifest}
        selected_label = st.selectbox("Select a registered sample", list(sample_by_label.keys()), key="sample_to_verify")
        selected_sample = sample_by_label[selected_label]
        sample_path = SAMPLES_DIR / selected_sample["file_name"]
        sample_bytes = sample_path.read_bytes()
        st.markdown(
            f"<div class='surface'><div class='surface-title'>{esc(selected_sample['name'])}</div><div class='surface-sub'>Recipient: {esc(selected_sample['recipient'])} · Issuer: {esc(selected_sample['issuer'])}</div><div class='tiny-label'>EXPECTED FILE FINGERPRINT</div><div class='hash'>{esc(sha256_bytes(sample_bytes))}</div></div>",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Verify this sample", type="primary", use_container_width=True, key="sample_verify"):
                result = process_verification(sample_bytes, selected_sample["file_name"], state, LEDGER_PATH)
                st.session_state["last_sample_result"] = result
        with c2:
            st.download_button("Download selected PDF", sample_bytes, file_name=selected_sample["file_name"], mime="application/pdf", use_container_width=True, key="sample_download_verify")
        result = st.session_state.get("last_sample_result")
        if result and result.get("file_hash") == sha256_bytes(sample_bytes):
            render_verification_result(result, state, LEDGER_PATH)

    st.markdown("<div class='notice'>A no-match means the exact file bytes are not registered. A match does not prove issuer identity.</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# ISSUE DEMO CERTIFICATE
# -----------------------------------------------------------------------------
elif page == "Issue demo certificate":
    hero(
        "ONE-CLICK CREDENTIAL CREATION",
        "Issue a demo certificate.",
        "Generate a fictional PDF credential automatically, calculate its file fingerprint, register the credential, and write an issuance event to the hash-linked ledger. No manual data-entry form is required.",
    )
    left, right = st.columns([1.1, 0.9], gap="large")
    with left:
        st.markdown("<div class='surface'><div class='surface-title'>Automatic generation</div><div class='surface-sub'>CertiChain selects a fictional recipient and learning track, creates a unique demonstration ID, renders a downloadable PDF, and registers its fingerprint.</div><div style='height:12px'></div><div class='step-title'>Included in every generated certificate</div><div class='step-copy'>• Unique demo certificate ID<br>• Course and fictional recipient<br>• Issue date and demonstration issuer<br>• QR code containing demo metadata<br>• Explicit notice that it is not an official qualification</div></div>", unsafe_allow_html=True)
        if st.button("Generate and register certificate", type="primary", use_container_width=True, key="generate_certificate"):
            recipient_pool = ["Mira Kapoor", "Dev Sharma", "Ishita Rao", "Kabir Malhotra", "Anaya Singh", "Arjun Das"]
            course_pool = [
                ("Applied Python Fundamentals", "Completed the introductory applied Python learning track."),
                ("Data Literacy Essentials", "Completed the demonstration programme in data literacy."),
                ("Responsible AI Foundations", "Completed a fictional introductory course in responsible AI."),
                ("Cybersecurity Awareness", "Completed the demonstration learning track in cybersecurity awareness."),
                ("Digital Product Design", "Completed the fictional digital product design learning programme."),
            ]
            course, description = random.choice(course_pool)
            cert_id = f"CC-DEMO-{date.today().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"
            metadata = {
                "id": cert_id,
                "name": course,
                "recipient": random.choice(recipient_pool),
                "issuer": "CertiChain Demo Academy",
                "issued_on": date.today().isoformat(),
                "description": description,
                "certificate_type": "generated_demo",
            }
            pdf_bytes = create_certificate_pdf(metadata)
            certificate = new_certificate_record(metadata, pdf_bytes, "Generated demo")
            state["certificates"].append(certificate)
            block = append_event(state, "DEMO_CERTIFICATE_ISSUED", registration_details(certificate, "One-click fictional credential generated in the classroom demo."))
            ISSUED_DIR.mkdir(parents=True, exist_ok=True)
            (ISSUED_DIR / certificate["file_name"]).write_bytes(pdf_bytes)
            save_state(LEDGER_PATH, state)
            st.session_state["last_issued_id"] = cert_id
            st.session_state["last_issued_block"] = block["index"]
            st.rerun()
    with right:
        st.markdown("<div class='surface'><div class='surface-title'>What happens under the hood?</div><div class='step-number'>01</div><div class='step-copy'>A PDF is created from generated demo metadata.</div><hr><div class='step-number'>02</div><div class='step-copy'>SHA-256 fingerprints the exact PDF bytes.</div><hr><div class='step-number'>03</div><div class='step-copy'>The registry metadata and file hash are committed to a new linked record.</div><hr><div class='step-number'>04</div><div class='step-copy'>The new PDF becomes downloadable and can be checked on the verification page.</div></div>", unsafe_allow_html=True)

    last_issued_id = st.session_state.get("last_issued_id")
    if last_issued_id:
        issued_cert = next((c for c in state["certificates"] if c["id"] == last_issued_id), None)
        if issued_cert:
            issued_path = ISSUED_DIR / issued_cert["file_name"]
            if issued_path.exists():
                st.write("")
                st.markdown("## Your generated credential")
                lcol, rcol = st.columns([1.2, 0.8], gap="large")
                with lcol:
                    st.markdown(
                        f"<div class='surface'><div class='pill-good'>REGISTERED SUCCESSFULLY</div><div class='surface-title' style='font-size:1.25rem;margin-top:12px'>{esc(issued_cert['name'])}</div><div class='surface-sub'>Recipient: {esc(issued_cert['recipient'])} · Issuer: {esc(issued_cert['issuer'])}</div><div class='tiny-label'>CERTIFICATE ID</div><div class='hash'>{esc(issued_cert['id'])}</div><div class='tiny-label'>FILE SHA-256</div><div class='hash'>{esc(issued_cert['file_hash'])}</div><div class='tiny-label'>REGISTRY METADATA HASH</div><div class='hash'>{esc(issued_cert['registry_hash'])}</div></div>",
                        unsafe_allow_html=True,
                    )
                    st.download_button("Download generated certificate PDF", issued_path.read_bytes(), file_name=issued_cert["file_name"], mime="application/pdf", type="primary", use_container_width=True)
                    st.button(
                        "Go verify this certificate →",
                        use_container_width=True,
                        key="verify_last_issued",
                        on_click=set_navigation,
                        args=("Verify certificate",),
                    )
                with rcol:
                    st.markdown("<div class='surface'><div class='surface-title'>Ledger receipt</div><div class='surface-sub'>The certificate registration is included in a new block linked to the previous block's hash.</div><div class='tiny-label'>EVENT</div><div class='hash'>DEMO_CERTIFICATE_ISSUED</div><div class='tiny-label'>BLOCK NUMBER</div><div class='hash'>" + esc(st.session_state.get("last_issued_block", "—")) + "</div></div>", unsafe_allow_html=True)
    st.markdown("<div class='notice'>Demo certificates are fictional. Their QR code contains metadata, not a digital signature.</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# LEDGER EXPLORER
# -----------------------------------------------------------------------------
elif page == "Ledger explorer":
    hero(
        "LEDGER EXPLORER",
        "Inspect linked records.",
        "Review block hashes, previous-hash links, and run a safe tampering test.",
    )
    chain_ok, chain_message = verify_chain(state["chain"])
    registry_ok, registry_message = verify_registry(state)
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1: stat_card("Chain hash checks", "PASS" if chain_ok else "FAIL", chain_message[:58])
    with c2: stat_card("Registry consistency", "PASS" if registry_ok else "FAIL", registry_message[:58])
    with c3: stat_card("Ledger entries", len(state["chain"]), "Ordered records from the genesis link")

    if state["chain"]:
        latest = state["chain"][-1]
        with st.expander("Latest block details", expanded=True):
            a, b = st.columns([1, 1], gap="large")
            with a:
                st.markdown(f"<div class='tiny-label'>BLOCK #{latest['index']} · {esc(event_title(latest['event_type']))}</div><div class='tiny-label'>PREVIOUS HASH</div><div class='hash'>{esc(latest['previous_hash'])}</div>", unsafe_allow_html=True)
            with b:
                st.markdown(f"<div class='tiny-label'>TIMESTAMP (UTC)</div><div class='hash'>{esc(latest['timestamp'])}</div><div class='tiny-label'>BLOCK HASH</div><div class='hash'>{esc(latest['block_hash'])}</div>", unsafe_allow_html=True)

    st.markdown("## Ledger activity")
    all_types = sorted({block["event_type"] for block in state["chain"]})
    options = ["All events"] + [event_title(event_type) for event_type in all_types]
    selected_filter = st.selectbox("Filter by event", options, key="ledger_event_filter")
    rows = []
    ordered_blocks = list(reversed(state["chain"]))
    for block in ordered_blocks:
        label = event_title(block["event_type"])
        if selected_filter != "All events" and selected_filter != label:
            continue
        details = block.get("details", {})
        rows.append({
            "Block": block["index"],
            "Timestamp (UTC)": block["timestamp"],
            "Event": label,
            "Reference": event_reference(block),
            "Result": details.get("result", "—"),
            "Previous hash": short_hash(block["previous_hash"], 16),
            "Block hash": short_hash(block["block_hash"], 16),
        })
    if rows:
        st.dataframe(rows, hide_index=True, use_container_width=True)
    else:
        st.info("No events match that filter.")

    with st.expander("Inspect the full data for one block"):
        if state["chain"]:
            block_index = st.selectbox("Select block", options=list(range(len(state["chain"]))), format_func=lambda i: f"Block {state['chain'][i]['index']} · {event_title(state['chain'][i]['event_type'])}", key="block_inspector")
            st.json(state["chain"][block_index])
        else:
            st.caption("There are no blocks to inspect.")

    st.download_button(
        "Export ledger and registry JSON",
        data=json.dumps(state, indent=2, ensure_ascii=False) + "\n",
        file_name="certichain-ledger-export.json",
        mime="application/json",
        use_container_width=False,
    )

    st.write("")
    st.markdown("## Tamper-detection demonstration")
    st.markdown("<div class='surface-sub'>This test changes a copy of a record in memory and checks it against the original hash. Your actual ledger file is not changed.</div>", unsafe_allow_html=True)
    if st.button("Run simulated record-tampering test", type="primary", key="run_tamper_demo"):
        if len(state["chain"]) < 1:
            st.info("Create at least one ledger record before running the simulation.")
        else:
            simulated_chain = copy.deepcopy(state["chain"])
            original_note = simulated_chain[0].setdefault("details", {}).get("note", "Original record")
            simulated_chain[0]["details"]["note"] = str(original_note) + " [SIMULATED ALTERATION]"
            sim_ok, sim_message = verify_chain(simulated_chain)
            st.session_state["tamper_demo_result"] = {"valid": sim_ok, "message": sim_message}
    demo_result = st.session_state.get("tamper_demo_result")
    if demo_result:
        if not demo_result["valid"]:
            st.markdown(f"<div class='callout'><b>EXPECTED RESULT: ALTERATION DETECTED</b><br>{esc(demo_result['message'])}<br>The actual saved ledger remains untouched.</div>", unsafe_allow_html=True)
        else:
            st.error("The simulation unexpectedly passed. Review the hash-chain logic.")

    st.markdown("<div class='notice'><b>Limit:</b> this prototype stores records in one JSON file. A real blockchain needs independent nodes and consensus.</div>", unsafe_allow_html=True)
