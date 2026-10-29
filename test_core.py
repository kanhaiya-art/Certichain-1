import copy
import tempfile
import unittest
from pathlib import Path

from certichain_core import (
    ZERO_HASH,
    append_event,
    create_certificate_pdf,
    create_initial_state,
    find_certificate_by_hash,
    new_certificate_record,
    record_verification,
    registration_details,
    save_state,
    sha256_bytes,
    verify_chain,
    verify_integrity,
    verify_registry,
)

APP_DIR = Path(__file__).resolve().parents[1]


class CertiChainCoreTests(unittest.TestCase):
    def setUp(self):
        self.state = create_initial_state(APP_DIR)

    def test_initial_samples_are_registered_and_chain_is_valid(self):
        self.assertEqual(len(self.state["certificates"]), 3)
        self.assertEqual(len(self.state["chain"]), 3)
        self.assertTrue(verify_integrity(self.state)[0])
        self.assertEqual(self.state["chain"][0]["previous_hash"], ZERO_HASH)

    def test_sample_file_bytes_match_registry_hash(self):
        for certificate in self.state["certificates"]:
            sample_path = APP_DIR / "samples" / certificate["file_name"]
            self.assertTrue(sample_path.exists())
            self.assertEqual(sha256_bytes(sample_path.read_bytes()), certificate["file_hash"])
            self.assertTrue(sample_path.read_bytes().startswith(b"%PDF"))

    def test_hash_chain_detects_changed_block(self):
        altered = copy.deepcopy(self.state["chain"])
        altered[0]["details"]["note"] = "altered"
        ok, message = verify_chain(altered)
        self.assertFalse(ok)
        self.assertIn("hash", message.lower())

    def test_registry_integrity_detects_metadata_change(self):
        altered = copy.deepcopy(self.state)
        altered["certificates"][0]["recipient"] = "Edited Recipient"
        self.assertFalse(verify_registry(altered)[0])

    def test_verification_event_is_linked(self):
        cert = self.state["certificates"][0]
        block = record_verification(self.state, cert["file_name"], cert["file_hash"], cert)
        self.assertEqual(block["event_type"], "CERTIFICATE_MATCHED")
        self.assertTrue(verify_integrity(self.state)[0])

    def test_unknown_file_records_no_match_without_saving_content(self):
        digest = sha256_bytes(b"this is not a certificate")
        block = record_verification(self.state, "unknown.pdf", digest, None)
        self.assertEqual(block["event_type"], "VERIFICATION_NO_MATCH")
        self.assertEqual(block["details"]["uploaded_file_hash"], digest)
        self.assertNotIn("file_bytes", block["details"])
        self.assertTrue(verify_integrity(self.state)[0])

    def test_newly_issued_pdf_can_be_registered_and_matched(self):
        metadata = {
            "id": "CC-TEST-ISSUE-001",
            "name": "Test course",
            "recipient": "Test Recipient",
            "issuer": "CertiChain Demo Academy",
            "issued_on": "2026-10-28",
            "description": "A fictional test certificate.",
            "certificate_type": "generated_demo",
        }
        pdf_bytes = create_certificate_pdf(metadata)
        cert = new_certificate_record(metadata, pdf_bytes, "Generated demo")
        self.state["certificates"].append(cert)
        append_event(self.state, "DEMO_CERTIFICATE_ISSUED", registration_details(cert, "test issue"))
        self.assertEqual(find_certificate_by_hash(self.state, sha256_bytes(pdf_bytes))["id"], metadata["id"])
        self.assertTrue(verify_integrity(self.state)[0])

    def test_save_state_writes_json_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "data" / "ledger.json"
            save_state(target, self.state)
            self.assertTrue(target.exists())
            self.assertFalse(target.with_suffix(".tmp").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
