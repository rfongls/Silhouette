class MockPayerGateway:
    def submit_270(self, edi_270: str) -> str:
        return "MOCK-271-OK"
    def submit_278(self, edi_278: str, attachment_hint: str | None = None) -> str:
        return "MOCK-278-ACCEPTED"
