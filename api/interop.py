from fastapi import APIRouter
from pydantic import BaseModel
from skills.hl7_drafter import draft_message, send_message

router = APIRouter()

class HL7Request(BaseModel):
    message_type: str
    json_data: dict | None = None
    host: str
    port: int

@router.post("/interop/hl7/send")
async def interop_hl7_send(req: HL7Request):
    data = req.json_data or {}
    message = draft_message(req.message_type, data)
    ack = await send_message(req.host, req.port, message)
    return {"message": message, "ack": ack}
