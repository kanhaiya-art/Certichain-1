# CertiChain: Blockchain-Inspired Certificate Integrity Verification

## Abstract

CertiChain is an educational software prototype that demonstrates how cryptographic hashing and hash-linked event records can support file-integrity checks for digital certificates. The application calculates a SHA-256 fingerprint for an uploaded certificate file, compares it with a registry of fingerprints for fictional credentials, records the verification result, and allows users to inspect the resulting ledger. It also creates downloadable demo credentials and includes a controlled alteration simulation to demonstrate tamper detection.

## Problem statement

Digital credentials are easy to copy and may be modified or presented without useful provenance. A viewer can often read the visible information, but visual inspection alone does not establish that a file matches a previously registered version. A verification system needs a reproducible way to identify exact file content and an auditable record of the checks that were performed.

## Objectives

1. Demonstrate the use of SHA-256 to create a fixed-length digital fingerprint of certificate file bytes.
2. Build a simple credential registry with predefined sample certificates and one-click demo issuance.
3. Compare uploaded file fingerprints with registered fingerprints without requiring a long manual data-entry form.
4. Store issuance and verification events in a hash-linked sequence.
5. Recompute block hashes and links to identify altered records.
6. Explain technical limitations and the difference between integrity checking and real-world issuer authentication.

## Tools and technology

- **Python:** application logic, file processing, and hashing.
- **Streamlit:** interactive web interface and navigation.
- **SHA-256 (`hashlib`):** file fingerprints and record digests.
- **Canonical JSON:** stable serialization for reproducible record hashes.
- **ReportLab:** creation of demo certificate PDFs.
- **QR Code library:** rendering an informational QR code that contains demo metadata; it is not a signature.
- **JSON file:** local persistence for registry metadata and hash-linked events.
- **`unittest`:** tests for hash-chain, registry, matching, and persistence behaviour.

## System design

### 1. Certificate issuance

The app generates fictional metadata, including a unique demo ID, course, recipient, issuer, and issue date. It renders a PDF explicitly marked as a fictional educational sample. The file bytes are hashed with SHA-256. The metadata and digest are registered and a `DEMO_CERTIFICATE_ISSUED` event is appended to the ledger.

### 2. Verification

The uploaded file is read by the application and hashed. The app compares this digest with registered fingerprints. A matching digest indicates an exact byte-for-byte match with one registered file. A no-match result may mean that the file is not registered or its bytes differ. The result is recorded as either `CERTIFICATE_MATCHED` or `VERIFICATION_NO_MATCH`.

### 3. Hash-linked event ledger

Each block contains an index, timestamp, event type, event details, previous block hash, and its own hash. The first block points to an all-zero genesis value. Each subsequent block references the hash of the previous block. During integrity checking, the application recomputes block hashes and confirms that every previous-hash reference is correct.

### 4. Registry consistency

Each registry entry receives a digest of selected metadata fields. The corresponding registration event contains that digest and the file fingerprint. The app checks that registry entries agree with their registration events, so a direct edit to a registry entry is also detectable.

## Workflow

```text
Preloaded PDF / generated PDF / uploaded file
                    |
                    v
          Calculate SHA-256
                    |
          +---------+---------+
          |                   |
          v                   v
   Match in registry?     No matching hash
          |                   |
          v                   v
      MATCH result       NO MATCH result
          +---------+---------+
                    |
                    v
          Append a ledger event
                    |
                    v
      Recompute block and registry integrity
```

## Testing and expected outcomes

- Each bundled sample PDF has a registered fingerprint calculated from its actual bytes.
- Uploading an unchanged sample PDF yields a match.
- Registering a newly generated demo certificate enables the generated PDF to match.
- An unregistered file yields a no-match result and a corresponding ledger event.
- Altering the content of a ledger block without recomputing hashes causes the chain check to fail.
- Altering registered metadata without updating its metadata digest causes the registry consistency check to fail.
- The simulated tampering test uses a copy, preserving the actual saved ledger.

## Limitations

The prototype illustrates cryptographic integrity; it does not constitute a distributed blockchain. The JSON ledger runs under one application's authority and has no network of independent validating nodes, consensus protocol, or decentralized governance. An administrator who can rewrite the entire JSON file can rebuild all hashes, so hashes alone do not provide immutable storage.

A file match does not prove that the issuer is authentic, that the recipient's identity is true, or that a qualification is legally recognized. The demo accepts exact-byte matches; a PDF re-export, scan, screenshot, or metadata change may alter the fingerprint. The QR code carries demonstration metadata only and is not digitally signed.

## Future improvements

- Authenticate institutions and protect issuer signing keys.
- Add digital signatures and a public-key validation workflow.
- Support credential revocation, expiry, and issuer status checks.
- Define data minimization, consent, retention, and access-control policies.
- Use independently operated validators or an established ledger where decentralized trust is genuinely necessary.
- Add privacy-preserving verification so a verifier does not need to expose unnecessary personal information.

## Conclusion

CertiChain makes the core concepts of hashing and linked records observable through an interactive workflow. Its main educational contribution is to show both the value and the limits of the technology: a digest can identify exact file content, and a linked ledger can expose modifications, but genuine credential trust also depends on issuer authentication, governance, privacy, and the way the system is operated.
