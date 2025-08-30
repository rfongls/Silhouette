# HL7 QA Runbook

- Run the validator as shown in [hl7_testing.md](hl7_testing.md).
- Reports write to `artifacts/hl7/`; add this folder to `.gitignore`.
- Messages that exceed error thresholds or hit unknown segments land in `artifacts/hl7/deadletter/` with a short reason.
- Review metrics and dead letters before promoting messages past QA gates.
