# Prior Authorization (FHIR + X12 278/275)

```mermaid
flowchart TD
  A[Provider System] --> B[Silhouette FHIR Intake]
  B --> C[PA Bundle (FHIR PAS profile)]
  C --> D[X12 278 Translator]
  D --> E[Payer Gateway]
  E --> F[Response (278/275 attachments)]
  F --> G[Normalize to FHIR + Status]
  G --> H[Notify Provider / Update PM Task]
```

**Notes**

* Attach clinical docs via 275; map to PAS profiles.
* Track status + reasons; surface denials for appeal kits.
