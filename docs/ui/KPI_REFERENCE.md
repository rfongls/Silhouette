# KPI Reference

## Security
- **Gate**: `allowed / total` over recent gate decisions (last result surfaced)
- **Recon**:
  - **services** = discovered service count (latest recon)
  - **hosts** = unique host count (latest recon)
  - **ports** = unique port count (latest recon)
  - **CVEs** = total CVEs across services (latest recon)
  - **KEV** = count of CVEs flagged as KEV
  - **Severities** = Critical / High / Medium / Low, from CVSS if present
- **Netforensics**:
  - **alerts** = number of alerts
  - **packets** = max packets across recent artifacts

## Interoperability
- **Send (ACK)**: ACK successes over recent sends (last result surfaced)
- **Translate**: OK / Fail based on `rc`
- **Validate**: OK / Fail based on `rc`

## Trend indices
We record compact timestamped points in:
```
out/security/ui/index.json
out/interop/ui/index.json
```
Keeping up to ~200 points for lightweight sparklines.

