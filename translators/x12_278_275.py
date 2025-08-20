def translate_fhir_pas_to_278(pas_bundle: dict) -> str:
    # Stub: build an 278 request using identifiers pulled from PAS profile
    ctrl = pas_bundle.get("identifier", [{"value":"CTRL9999"}])[0]["value"]
    return f"ISA*00* *00* *ZZ*PROV *ZZ*PAYER *240101*0100*^*00501*000000123*0*T*:~" \
           f"GS*HI*PROV*PAYER*20240101*0100*1*X*005010X217~" \
           f"ST*278*{ctrl}*005010X217~" \
           "SE*3*{ctrl}~" \
           "GE*1*1~IEA*1*000000123~"

def attach_275(xml_attachment: str) -> str:
    # Return placeholder indicating 275 attachment packaged out-of-band (transport dependent).
    return f"<!-- 275 attachment submitted separately (length={len(xml_attachment)}) -->"
