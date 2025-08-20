class MockHIEConnector:
    def query_documents(self, patient_id: str) -> list[dict]:
        # Return pointers to CCD + FHIR endpoints
        return [
            {"type": "CCD", "url": "mock://ccd/123456"},
            {"type": "FHIR", "url": "mock://fhir/Bundle/abc"}
        ]
