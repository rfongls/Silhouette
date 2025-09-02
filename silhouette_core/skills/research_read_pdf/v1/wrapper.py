import json
from pypdf import PdfReader


def _split_into_sections(text, min_len=400, max_len=1200):
    paras = [p.strip() for p in (text or "").split("\n") if p.strip()]
    cur = ""; out = []
    for p in paras:
        if len(cur) + len(p) < max_len:
            cur = f"{cur}\n{p}".strip()
        else:
            if len(cur) >= min_len:
                out.append(cur)
            cur = p
    if cur:
        out.append(cur)
    return out


def tool(pdf_path: str) -> str:
    """
    Input: local path to a PDF in docs/corpus/
    Output: JSON list: [{"doc_id":"file.pdf","section_id":"s1","text":"..."}, ...]
    """
    reader = PdfReader(pdf_path)
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    sections = _split_into_sections(text)
    doc_id = pdf_path.split("/")[-1]
    out = [{"doc_id": doc_id, "section_id": f"s{i+1}", "text": sec} for i, sec in enumerate(sections)]
    return json.dumps(out)

