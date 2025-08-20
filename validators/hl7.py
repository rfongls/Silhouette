def validate_hl7_minimal(hl7_text: str) -> None:
    if not hl7_text.startswith("MSH"):
        raise ValueError("MSH segment missing")
    if "PID|" not in hl7_text:
        raise ValueError("PID segment missing")
