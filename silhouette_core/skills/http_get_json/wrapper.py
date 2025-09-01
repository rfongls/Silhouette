import json
import urllib.error
import urllib.request

def tool(url: str, timeout: float = 5.0) -> str:
    """
    Fetch JSON from a URL with a timeout. Returns a compact JSON string or an error JSON.
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = r.read()
            try:
                obj = json.loads(data.decode("utf-8"))
                return json.dumps(obj, separators=(",", ":"))
            except Exception:
                return json.dumps({"error": "non-json-response", "len": len(data)})
    except urllib.error.URLError as e:
        return json.dumps({"error": "url-error", "msg": str(e)})
