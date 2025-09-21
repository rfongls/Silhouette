# Interop UI Flow

Panels: Samples, Generate, De‑ID, Validate, Translate, MLLP, Full Pipeline.  
Chips: `.module-btn[data-panel="..."]` with `active` + `aria-expanded`.

**Universal behavior:** selecting a pipeline action collapses all other panels, focuses the target, scrolls it into view, and reveals its tray. This matches the Interop dashboard design. :contentReference[oaicite:8]{index=8}

Trays order (contextual):
- After De‑ID: Validate → Send MLLP → HL7→FHIR
- After Validate: Edit & Re‑Run → Send MLLP → HL7→FHIR
- After MLLP: Re‑Send → HL7→FHIR → View Reports
