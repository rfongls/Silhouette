def parse_270(edi_text: str) -> dict:
    # Very lightweight segment splitter; real impl should use X12 lib.
    segs = [s for s in edi_text.split('~') if s.strip()]
    return {"segments": segs, "type": "270"}

def generate_271_response(request: dict) -> str:
    # Echo minimal 271 acknowledging eligibility
    return "ISA*00* *00* *ZZ*SENDER *ZZ*PAYER *240101*0100*^*00501*000000001*0*T*:~" \
           "GS*HB*SENDER*PAYER*20240101*0100*1*X*005010X279A1~" \
           "ST*271*0001*005010X279A1~" \
           "BHT*0022*11*9999*20240101*0100~" \
           "SE*4*0001~" \
           "GE*1*1~IEA*1*000000001~"
