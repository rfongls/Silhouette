def validate_ccd_minimal(xml_text: str) -> None:
    if "<ClinicalDocument" not in xml_text:
        raise ValueError("Not a CDA ClinicalDocument")
    if "recordTarget" not in xml_text:
        raise ValueError("recordTarget missing")


class CDAValidator:
    """Simple CDA validator facade."""

    def validate(self, payload: str, **opts: dict) -> dict:
        validate_ccd_minimal(payload)
        return {"valid": True}
