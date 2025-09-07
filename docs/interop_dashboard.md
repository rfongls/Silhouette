# Interop Dashboard

## MLLP Send

`/api/interop/mllp/send` accepts `messages` either as a JSON array of HL7 strings or as a single string containing one or more HL7 messages separated by blank lines. The server splits on blank lines and sends each message individually.

### Dev MLLP Echo (local testing)

For a quick local ACK’ing listener:

```bash
python scripts/dev_mllp_echo.py --host 127.0.0.1 --port 2575
```

Then POST to the API:

```bash
curl -s http://localhost:8000/api/interop/mllp/send \
  -H "Content-Type: application/json" \
  -d '{"host":"127.0.0.1","port":2575,"messages":"MSH|^~\\\\&|SIL|HOSP|REC|HUB|202501010000||ADT^A01|X|P|2.4\\r\\nPID|1||12345^^^HOSP^MR||DOE^JOHN\\r\\n"}'
```

The echo server returns one ACK per frame and includes the inbound `MSH-10` value in `MSA-2`.

### Quick Start (Generate → FHIR → Validate)

- Choose **Version** and **Trigger**, set an optional **seed**, and toggles for **Unique IDs**, **Enrich clinical**, **De-identify**.
- Click **Run Pipeline** to render a 3-column result:
  - Left: generated HL7
  - Middle: FHIR result (via Silhouette CLI if installed; otherwise a stub with a clear note)
  - Right: Validation summary

Templates should exist under templates/hl7/<version> for the triggers you select.

### Map Selection (Trigger → Map)

Quick Start automatically selects a mapping file under `/maps/` based on the trigger. Examples:

| Trigger  | Map file |
|----------|--------------------------------|
| ADT_A01  | `maps/adt_uscore.yaml` |
| ADT_A08  | `maps/adt_update_uscore.yaml` |
| ADT_A31  | `maps/adt_merge_uscore.yaml` |
| ORM_O01  | `maps/orm_uscore.yaml` |
| ORU_R01  | `maps/oru_uscore.yaml` |
| RDE_O11  | `maps/rde_uscore.yaml` |
| VXU_V04  | `maps/vxu_uscore.yaml` |
| MDM_T02  | `maps/mdm_uscore.yaml` |
| SIU_S12  | `maps/siu_uscore.yaml` |
| DFT_P03  | `maps/dft_uscore.yaml` |
| BAR_P01  | `maps/bar_uscore.yaml` |
| COVERAGE | `maps/coverage_uscore.yaml` |

Wildcards like `OMX_*`, `ORX_*`, or `RESEARCH_*` resolve to their family map. To change defaults, edit `MAP_INDEX` in `api/interop.py`.

