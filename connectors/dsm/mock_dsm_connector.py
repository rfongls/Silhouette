class MockDSMConnector:
    def receive(self) -> dict:
        return {"mime":"message/rfc822", "attachmentType":"C-CDA", "contentRef":"mock://ccd/123456"}
