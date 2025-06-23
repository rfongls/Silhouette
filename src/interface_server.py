from fastapi import FastAPI, Request
from pydantic import BaseModel
from src.intent_engine import IntentEngine
from src.memory_core import append_to_memory, query_memory
from src.tone_parser import detect_tone

app = FastAPI()
engine = IntentEngine()

class InputText(BaseModel):
    text: str

@app.post("/intent")
def get_intent(input: InputText):
    return engine.classify(input.text)

@app.post("/tone")
def get_tone(input: InputText):
    return detect_tone(input.text)

@app.post("/memory")
def save_memory(input: InputText):
    append_to_memory({"text": input.text})
    return {"status": "saved"}

@app.get("/memory")
def search_memory(q: str):
    return query_memory(q)
