from fastapi import FastAPI
from pydantic import BaseModel
from silhouette_core.intent_engine import IntentEngine
from silhouette_core.memory_core import append_to_memory, query_memory
from silhouette_core.tone_parser import detect_tone
from silhouette_core.embedding_engine import query_knowledge

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

@app.get("/search")
def search_knowledge(q: str):
    return query_knowledge(prompt=q)
