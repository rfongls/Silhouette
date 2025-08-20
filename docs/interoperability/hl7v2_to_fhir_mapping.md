# HL7 v2.x → FHIR Mapping

Use deterministic transforms with configurable rulesets per profile.
- Input: HL7 v2 ORU^R01/ADT^A01, etc.
- Output: FHIR Bundle (Patient, Encounter, Observation, Condition, Organization, Practitioner, etc.)

```mermaid
flowchart TD
  A[HL7 v2 Message (e.g., ORU^R01)] --> B[Segment Parser]
  B --> C{Routing by Trigger Event}
  C -->|ADT^A01| D[Map PID/PV1 -> Patient, Encounter]
  C -->|ORU^R01| E[Map OBR/OBX -> Observation/DiagnosticReport]
  D --> F[Bundle Assembly]
  E --> F
  F --> G[Validate FHIR Profiles]
  G --> H[Bundle Out (R4/R5)]
```

## Example Field Mapping (excerpt)

| HL7 v2               | FHIR Resource.field   |
| -------------------- | --------------------- |
| PID-3 (CX)           | Patient.identifier    |
| PID-5 (XPN)          | Patient.name          |
| PID-7 (DTM)          | Patient.birthDate     |
| PV1-19 (CX)          | Encounter.identifier  |
| OBR-4/OBX-3 (CE/CWE) | Observation.code      |
| OBX-5                | Observation.value[x]  |
