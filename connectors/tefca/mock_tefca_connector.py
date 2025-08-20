from typing import Dict
from skills.audit import fhir_audit_event, emit_and_persist


class MockTEFCAConnector:
    def cross_qhin_query(self, demographics: Dict) -> Dict:
        payload = {"qhin": "MOCK-QHIN", "results": [{"docType": "CCD", "ref": "mock://ccd/123456"}]}
        evt = fhir_audit_event(
            action="search",
            outcome="success",
            who="MockTEFCAConnector",
            what=f"Cross-QHIN query for demographics keys={list(demographics.keys())}",
        )
        emit_and_persist(evt)
        return payload
