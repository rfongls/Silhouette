def validate_ccd_minimal(xml_text: str) -> None:
    if "<ClinicalDocument" not in xml_text:
        raise ValueError("Not a CDA ClinicalDocument")
    if "recordTarget" not in xml_text:
        raise ValueError("recordTarget missing")
