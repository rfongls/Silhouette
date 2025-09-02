# Mapping Profiles

| Map file | messageTypes | Target resources | Notes |
| --- | --- | --- | --- |
| `adt_uscore.yaml` | ADT^A01, ADT^A04 | Patient, Encounter | class/status, period, patient identifiers |
| `adt_update_uscore.yaml` | ADT^A02, ADT^A03, ADT^A08, ADT^A11, ADT^A13, ADT^A40 | Patient, Encounter | updates, cancels, merges |
| `dft_uscore.yaml` | DFT^P03 | ChargeItem, Account | codes and quantities |
| `mdm_uscore.yaml` | MDM^T02 | DocumentReference, Binary | attachments must be base64 |
| `orm_uscore.yaml` | ORM^O01 | ServiceRequest | order intent |
| `oru_uscore.yaml` | ORU^R01 | Patient, DiagnosticReport, Observation, Specimen | LOINC/UCUM, result links |
| `rde_uscore.yaml` | RDE^O11 | MedicationRequest, MedicationDispense, MedicationAdministration | RxNorm where available |
| `siu_uscore.yaml` | SIU^S12 | Appointment, Organization, Practitioner, PractitionerRole, Location | participants and statuses |
| `vxu_uscore.yaml` | VXU^V04 | Patient, Immunization | vaccination history |
