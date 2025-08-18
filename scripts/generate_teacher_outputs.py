import json
import os
import pathlib

SRC = "training_data/core.jsonl"
DST = "training_data/teacher_outputs.jsonl"

PROMPT_TEMPLATE = "### Instruction:\n{instruction}\n\n### Input:\n{input}\n\n### Response:\n"

def _yield_prompts(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            ex = json.loads(line)
            yield ex

def _gen_teacher_outputs(prompts, model_name):
    try:
        from transformers import pipeline  # type: ignore
        nlp = pipeline("text-generation", model=model_name, trust_remote_code=True)
        for ex in prompts:
            prompt = PROMPT_TEMPLATE.format(instruction=ex.get("instruction", ""), input=ex.get("input", ""))
            out = nlp(prompt, max_new_tokens=256, temperature=0.2, top_p=0.9)[0]["generated_text"]
            text = out[len(prompt):].strip() if out.startswith(prompt) else out.strip()
            yield {
                "instruction": ex.get("instruction", ""),
                "input": ex.get("input", ""),
                "teacher_output": text,
                "tools_used": ex.get("tools_used", []),
            }
    except Exception:
        for ex in prompts:
            instr = ex.get("instruction", "")
            inp = ex.get("input", "")
            tool_hint = ""
            if ex.get("tools_used"):
                tool_hint = f" [tools: {','.join(ex['tools_used'])}]"
            text = f"[teacher-stub]{tool_hint} {instr} {inp}".strip()
            yield {
                "instruction": instr,
                "input": inp,
                "teacher_output": text,
                "tools_used": ex.get("tools_used", []),
            }

def main():
    src = os.environ.get("KD_SRC", SRC)
    dst = os.environ.get("KD_DST", DST)
    teacher_model = os.environ.get("TEACHER_MODEL", "").strip()

    prompts = list(_yield_prompts(src))
    if teacher_model:
        outputs = list(_gen_teacher_outputs(prompts, teacher_model))
    else:
        outputs = list(_gen_teacher_outputs(prompts, model_name=None))

    pathlib.Path(dst).parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        for ex in outputs:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"Wrote {len(outputs)} examples to {dst}")

if __name__ == "__main__":
    main()
