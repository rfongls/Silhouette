# HL7–FHIR Workflows

Common v2 triggers and the FHIR resources they produce. Each example translates a sample HL7 message to a FHIR bundle.

## ADT A01/A04 — Admit or Register Patient
Creates **Patient** and **Encounter** with class, status, and period.

**Windows CMD**
```bat
python -m silhouette_core.cli fhir translate --in "tests\data\hl7\adt_a01.hl7" --map "maps\adt_uscore.yaml" --bundle transaction --out out --dry-run
```
**PowerShell**
```powershell
python -m silhouette_core.cli fhir translate `
  --in "tests\data\hl7\adt_a01.hl7" `
  --map "maps\adt_uscore.yaml" `
  --bundle transaction `
  --out out `
  --dry-run
```
**Bash**
```bash
python -m silhouette_core.cli fhir translate \
  --in tests/data/hl7/adt_a01.hl7 \
  --map maps/adt_uscore.yaml \
  --bundle transaction \
  --out out \
  --dry-run
```
Outputs: `Patient.ndjson`, `Encounter.ndjson`, `out/fhir/bundles/adt_a01.json`.

## ADT A02/A03/A08/A11/A13 — Encounter Updates
Uses **maps/adt_update_uscore.yaml** to update or cancel encounters and patient fields.

**Windows CMD**
```bat
python -m silhouette_core.cli fhir translate --in "tests\data\hl7\adt_a08.hl7" --map "maps\adt_update_uscore.yaml" --bundle transaction --out out --dry-run
```
**PowerShell**
```powershell
python -m silhouette_core.cli fhir translate `
  --in "tests\data\hl7\adt_a08.hl7" `
  --map "maps\adt_update_uscore.yaml" `
  --bundle transaction `
  --out out `
  --dry-run
```
**Bash**
```bash
python -m silhouette_core.cli fhir translate \
  --in tests/data/hl7/adt_a08.hl7 \
  --map maps/adt_update_uscore.yaml \
  --bundle transaction \
  --out out \
  --dry-run
```
Updates `Encounter.status` and patient demographics; A11/A13 cancel encounters.

## ADT A40 — Patient Merge
Merges a patient record: the losing **Patient** is marked `active=false` and linked via `link.type=replaced-by`.

**Windows CMD**
```bat
python -m silhouette_core.cli fhir translate --in "tests\data\hl7\adt_a40.hl7" --map "maps\adt_update_uscore.yaml" --bundle transaction --out out --dry-run
```
**PowerShell**
```powershell
python -m silhouette_core.cli fhir translate `
  --in "tests\data\hl7\adt_a40.hl7" `
  --map "maps\adt_update_uscore.yaml" `
  --bundle transaction `
  --out out `
  --dry-run
```
**Bash**
```bash
python -m silhouette_core.cli fhir translate \
  --in tests/data/hl7/adt_a40.hl7 \
  --map maps/adt_update_uscore.yaml \
  --bundle transaction \
  --out out \
  --dry-run
```
Resulting bundle updates both patient records; expect `Patient.ndjson` with link to survivor.

## ORU R01 — Laboratory Result
Creates **DiagnosticReport**, **Observation**, and **Specimen** with LOINC and UCUM codes; corrections set `status=corrected`.

**Windows CMD**
```bat
python -m silhouette_core.cli fhir translate --in "tests\data\hl7\oru_r01.hl7" --map "maps\oru_uscore.yaml" --bundle transaction --out out --dry-run
```
**PowerShell**
```powershell
python -m silhouette_core.cli fhir translate `
  --in "tests\data\hl7\oru_r01.hl7" `
  --map "maps\oru_uscore.yaml" `
  --bundle transaction `
  --out out `
  --dry-run
```
**Bash**
```bash
python -m silhouette_core.cli fhir translate \
  --in tests/data/hl7/oru_r01.hl7 \
  --map maps/oru_uscore.yaml \
  --bundle transaction \
  --out out \
  --dry-run
```
Outputs Observations linked to the DiagnosticReport and optional Specimen.

## ORM/OML O01 — Orders
Generates a **ServiceRequest** (`intent=order`); resulting Observations reference it via `basedOn`.

**Windows CMD**
```bat
python -m silhouette_core.cli fhir translate --in "tests\data\hl7\orm_o01.hl7" --map "maps\orm_uscore.yaml" --bundle transaction --out out --dry-run
```
**PowerShell**
```powershell
python -m silhouette_core.cli fhir translate `
  --in "tests\data\hl7\orm_o01.hl7" `
  --map "maps\orm_uscore.yaml" `
  --bundle transaction `
  --out out `
  --dry-run
```
**Bash**
```bash
python -m silhouette_core.cli fhir translate \
  --in tests/data/hl7/orm_o01.hl7 \
  --map maps/orm_uscore.yaml \
  --bundle transaction \
  --out out \
  --dry-run
```
Produces `ServiceRequest.ndjson` and bundle reflecting the order.

## SIU S12 — Scheduling
Creates an **Appointment** with **Organization**, **Practitioner**, **PractitionerRole**, and **Location** participants; handles status transitions.

**Windows CMD**
```bat
python -m silhouette_core.cli fhir translate --in "tests\data\hl7\siu_s12.hl7" --map "maps\siu_uscore.yaml" --bundle transaction --out out --dry-run
```
**PowerShell**
```powershell
python -m silhouette_core.cli fhir translate `
  --in "tests\data\hl7\siu_s12.hl7" `
  --map "maps\siu_uscore.yaml" `
  --bundle transaction `
  --out out `
  --dry-run
```
**Bash**
```bash
python -m silhouette_core.cli fhir translate \
  --in tests/data/hl7/siu_s12.hl7 \
  --map maps/siu_uscore.yaml \
  --bundle transaction \
  --out out \
  --dry-run
```
Expect `Appointment.ndjson` plus participant resources.

## VXU V04 — Immunization History
Outputs **Immunization** resources with CVX codes and occurrence data.

**Windows CMD**
```bat
python -m silhouette_core.cli fhir translate --in "tests\data\hl7\vxu_v04.hl7" --map "maps\vxu_uscore.yaml" --bundle transaction --out out --dry-run
```
**PowerShell**
```powershell
python -m silhouette_core.cli fhir translate `
  --in "tests\data\hl7\vxu_v04.hl7" `
  --map "maps\vxu_uscore.yaml" `
  --bundle transaction `
  --out out `
  --dry-run
```
**Bash**
```bash
python -m silhouette_core.cli fhir translate \
  --in tests/data/hl7/vxu_v04.hl7 \
  --map maps/vxu_uscore.yaml \
  --bundle transaction \
  --out out \
  --dry-run
```
Generates `Immunization.ndjson`.

## RDE O11 — Medication Dispense
Produces **MedicationRequest**, **MedicationDispense**, and **MedicationAdministration** with RxNorm codes when available.

**Windows CMD**
```bat
python -m silhouette_core.cli fhir translate --in "tests\data\hl7\rde_o11.hl7" --map "maps\rde_uscore.yaml" --bundle transaction --out out --dry-run
```
**PowerShell**
```powershell
python -m silhouette_core.cli fhir translate `
  --in "tests\data\hl7\rde_o11.hl7" `
  --map "maps\rde_uscore.yaml" `
  --bundle transaction `
  --out out `
  --dry-run
```
**Bash**
```bash
python -m silhouette_core.cli fhir translate \
  --in tests/data/hl7/rde_o11.hl7 \
  --map maps/rde_uscore.yaml \
  --bundle transaction \
  --out out \
  --dry-run
```
Expect medication request/dispense/administration NDJSON files.

## MDM T02 — Document Management
Creates **DocumentReference** with a **Binary** payload; `DocumentReference.content.attachment.data` must be base64.

**Windows CMD**
```bat
python -m silhouette_core.cli fhir translate --in "tests\data\hl7\mdm_t02.hl7" --map "maps\mdm_uscore.yaml" --bundle transaction --out out --dry-run
```
**PowerShell**
```powershell
python -m silhouette_core.cli fhir translate `
  --in "tests\data\hl7\mdm_t02.hl7" `
  --map "maps\mdm_uscore.yaml" `
  --bundle transaction `
  --out out `
  --dry-run
```
**Bash**
```bash
python -m silhouette_core.cli fhir translate \
  --in tests/data/hl7/mdm_t02.hl7 \
  --map maps/mdm_uscore.yaml \
  --bundle transaction \
  --out out \
  --dry-run
```
Outputs `DocumentReference.ndjson` and `Binary.ndjson`; ensure attachments are base64 encoded.

## DFT P03 — Financial Transactions
Emits **ChargeItem** and **Account** resources linking codes and quantities to the patient.

**Windows CMD**
```bat
python -m silhouette_core.cli fhir translate --in "tests\data\hl7\dft_p03.hl7" --map "maps\dft_uscore.yaml" --bundle transaction --out out --dry-run
```
**PowerShell**
```powershell
python -m silhouette_core.cli fhir translate `
  --in "tests\data\hl7\dft_p03.hl7" `
  --map "maps\dft_uscore.yaml" `
  --bundle transaction `
  --out out `
  --dry-run
```
**Bash**
```bash
python -m silhouette_core.cli fhir translate \
  --in tests/data/hl7/dft_p03.hl7 \
  --map maps/dft_uscore.yaml \
  --bundle transaction \
  --out out \
  --dry-run
```
Generates `ChargeItem.ndjson` and `Account.ndjson`.
