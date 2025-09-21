# Validate Reporting

**What we log** (task row + content snapshot):
- `action='validate'`, `status`, `elapsed_ms`
- `details_json` includes `{ error_count, warning_count, profile, top_errors[] }`
- `message_versions` stores the validated HL7 text

**Panel UX**
- “Validated against: **HL7 vX · Profile**”
- “Print report” → printable metadata + result block
- Link to **/reports/validate** (time‑window charts/search)

The UI style mirrors the Interop dashboard chips, trays, and tokens. :contentReference[oaicite:6]{index=6}
````
