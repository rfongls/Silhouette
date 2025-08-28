def validate_hl7_minimal(hl7_text: str) -> None:
    if not hl7_text.startswith("MSH"):
        raise ValueError("MSH segment missing")
    if "PID|" not in hl7_text:
        raise ValueError("PID segment missing")


def validate_hl7_structural(hl7_text: str) -> None:
    """Use hl7apy to perform dictionary-based structural validation."""
    from hl7apy.parser import parse_message

    parse_message(hl7_text, validation_level=2)


class HL7Validator:
    """Simple HL7 validator facade."""

    def validate(self, payload: str, **opts: dict) -> dict:
        validate_hl7_minimal(payload)
        return {"valid": True}
