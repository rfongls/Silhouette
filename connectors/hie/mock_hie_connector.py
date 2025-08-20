from typing import List, Dict
from skills.audit import fhir_audit_event, emit_and_persist


class MockHIEConnector:
    def query_documents(self, patient_id: str) -> List[Dict]:
        results = [
            {"type": "CCD", "url": "mock://ccd/123456"},
            {"type": "FHIR", "url": "mock://fhir/Bundle/abc"},
        ]
        evt = fhir_audit_event(
            action="read",
            outcome="success",
            who="MockHIEConnector",
            what=f"RLS query for patient_id={patient_id}",
        )
        emit_and_persist(evt)
        return results
