# CertiChain

A mobile-friendly Streamlit project demonstrating certificate file verification with SHA-256 and a hash-linked event ledger.

## Features
- Dashboard with three fictional sample certificates and ledger health
- Upload a PDF, image, or text file and compare its SHA-256 fingerprint
- Verify a bundled sample without manual data entry
- Generate and register a fictional demo certificate PDF
- Explore and export ledger records
- Run a safe tampering simulation that leaves the saved ledger unchanged

## Deploy from a phone
1. Extract `CertiChain_Project.zip`.
2. In GitHub, create/open your repository and upload the **contents** of the `CertiChain_Project` folder, not the ZIP itself. Keep `app.py`, `certichain_core.py`, and `requirements.txt` at the repository root. Include `.streamlit/` and `samples/`.
3. Open Streamlit Community Cloud and create an app from your repository.
4. Select your branch (usually `main`) and set **Main file path** to `app.py`.
5. Deploy and open the public app URL.

## Run locally
```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Quick demonstration
1. Download a sample PDF from the dashboard.
2. Open **Verify certificate** and upload the unchanged PDF. The file should match.
3. Open **Issue demo certificate**, generate a fictional certificate, download it, then verify it.
4. Open **Ledger explorer** and run the tampering simulation. The altered copy should fail integrity checks; the saved ledger is not changed.

## Tests
```bash
python -m unittest discover -s tests -v
```

## Technical limits
This is an educational, blockchain-inspired prototype. It implements SHA-256 fingerprints, hash-linked records, and integrity checks, but it is **not** a decentralized blockchain: it has no independent nodes or consensus. The ledger is a local JSON file; cloud filesystem changes may not persist across app restarts. A matching fingerprint proves byte-for-byte equality with a registered file, not the real-world identity of the issuer. All included certificates are fictional. Do not upload private certificates.
