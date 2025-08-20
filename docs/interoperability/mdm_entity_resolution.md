# MDM Entity Resolution (Patients/Providers/Orgs)

```mermaid
flowchart LR
  A[Incoming Records] --> B[Standardize/Normalize]
  B --> C[Blocking/Indexing (phonetic, tokens)]
  C --> D[Matching (rules + ML)]
  D -->|Match| E[Link to Master Entity]
  D -->|No Match| F[Create New Master]
  E --> G[Publish Golden Record]
  F --> G
```

**Notes**

* Deterministic + probabilistic rules; survivorship policies.
* Publish master identifiers back to downstream systems.
