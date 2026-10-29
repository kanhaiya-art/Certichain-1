# CertiChain — 3-minute live demonstration notes

## Opening (20 seconds)

“My project is CertiChain, an educational prototype for certificate file-integrity verification. It demonstrates SHA-256 fingerprinting and a hash-linked ledger. The sample credentials are fictional, and the app is intentionally transparent about what its results prove.”

## 1. Dashboard (30 seconds)

Point to the three preloaded sample certificates, the registry count, ledger block count, and integrity status. Explain that a fingerprint is calculated from file bytes, rather than from the filename or the way the certificate looks.

## 2. Verify a sample (35 seconds)

Open **Verify certificate → Test a preloaded sample**. Select a sample and click **Verify this sample**. Show the full SHA-256 digest, the exact match result, and the new block receipt. Explain that the verification event is recorded automatically.

## 3. Issue a new demo credential (40 seconds)

Open **Issue demo certificate** and click **Generate and register certificate**. Download the PDF. Point out the unique ID, QR metadata, file fingerprint, and the clear notice that this is a fictional demonstration certificate.

## 4. Verify the generated file (30 seconds)

Go to **Verify certificate → Upload a file**, upload the PDF, and click **Run certificate verification**. Explain that a newly registered file should now match its stored fingerprint.

## 5. Show tamper detection (35 seconds)

Open **Ledger explorer**, show the previous-hash link and current block hash, then click **Run simulated record-tampering test**. The app changes a copy of an existing block without changing its hash. The integrity check should detect the mismatch; the saved ledger remains untouched.

## Closing (20 seconds)

“The demo shows how hashes can help detect content changes and how linking records adds an audit trail. It does not prove issuer identity, provide decentralized consensus, or guarantee that a qualification is legally valid. A production version would need authenticated issuers, digital signatures, revocation, privacy protections, and an appropriate trust model.”

## Likely teacher questions

**What is SHA-256?** A cryptographic hash function that produces a 256-bit digest, normally displayed as 64 hexadecimal characters.

**Why does the file need to be identical?** This prototype hashes exact bytes. A re-export or scan changes bytes even when the visible text looks the same, so it may produce a no-match.

**Why call it blockchain-inspired rather than a full blockchain?** It implements hash-linked records but does not have independently operated nodes, consensus, or decentralized governance.

**What does a successful match prove?** It proves the uploaded bytes match a file fingerprint currently registered in this demo system. It does not independently authenticate the issuer or the qualification.
