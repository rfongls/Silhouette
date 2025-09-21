# Security & Privacy

- **PHI at rest**: HL7 text exists in `message_versions.message_text` and `mllp_sends.message_text` (and optional ACK payload).
- **Storage**: encrypted disk (BitLocker/FileVault). If needed, migrate to **SQLCipher** (same schema).
- **Access**: limit DB file and reporting endpoints.
- **Retention**: purge at 30 days (see runbook).
- **Errors**: avoid raw PHI in `errors.payload_json`; scrub or hash identifiers if needed.
