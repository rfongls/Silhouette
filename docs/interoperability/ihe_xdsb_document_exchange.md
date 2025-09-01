# IHE XDS.b Document Exchange

```mermaid
flowchart LR
  A[Source EHR] -->|Provide & Register| B[XDS.b Registry/Repository]
  B --> C[Consumer (HIE App)]
  C -->|Query/Retrieve| B
  B --> D[Silhouette Normalizer]
  D --> E[FHIR Bundle + Index]
```

**Implementation Notes**

* Support Provide & Register and Retrieve Transactions.
* Convert C-CDA to FHIR resources; index metadata for RLS.
