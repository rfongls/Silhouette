class MockTEFCAConnector:
    def cross_qhin_query(self, demographics: dict) -> dict:
        return {"qhin": "MOCK-QHIN", "results": [{"docType":"CCD","ref":"mock://ccd/123456"}]}
