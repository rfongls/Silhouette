# HL7 QA Developer Guide

Profiles and rule sets live in `tests/hl7/rules/`, while translation maps reside under `maps/`.

- Extend `tests/hl7/rules/rules.yaml` with site-specific checks.
- Add or adjust map files in `maps/` when new segments are introduced.
- Place sample messages in `tests/data/hl7/` to build regression fixtures.

Use [hl7_testing.md](hl7_testing.md) to run the validator after making changes.
