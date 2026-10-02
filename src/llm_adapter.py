"""MODEL ADAPTER - lớp DUY NHẤT biết tên nhà cung cấp/model.
Đổi model = đổi tham số dòng lệnh, không sửa logic/evals/guardrails.
Chỉ dùng thư viện chuẩn (urllib) để không phải cài gì thêm.
"""
import json
import os
import time
import urllib.error
import urllib.request


def _post(url, headers, body, timeout=180, retries=6):
    data = json.dumps(body).encode("utf-8")
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:600]
            if e.code in (500, 502, 503, 504) and attempt < retries - 1:
                wait = 15 * (attempt + 1)
                print(f"  HTTP {e.code}, đợi {wait}s rồi thử lại ({attempt + 1}/{retries - 1})...")
                time.sleep(wait)
                continue
            raise RuntimeError(f"HTTP {e.code}: {msg}") from None


def call_llm(system: str, user: str, provider: str, model: str,
             base_url: str = None, api_key: str = None, max_tokens: int = 4000) -> str:
    if provider == "anthropic":
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("Thiếu ANTHROPIC_API_KEY")
        res = _post((base_url or "https://api.anthropic.com") + "/v1/messages",
                    {"x-api-key": key, "anthropic-version": "2023-06-01"},
                    {"model": model, "max_tokens": max_tokens, "temperature": 0,
                     "system": system, "messages": [{"role": "user", "content": user}]})
        return "".join(b.get("text", "") for b in res["content"])
    if provider == "openai":  # mọi API tương thích OpenAI: OpenAI, DeepSeek, Gemini (endpoint tương thích)...
        key = api_key or os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("Thiếu LLM_API_KEY (hoặc OPENAI_API_KEY)")
        base = (base_url or "https://api.openai.com/v1").rstrip("/")
        res = _post(base + "/chat/completions", {"Authorization": f"Bearer {key}"},
                    {"model": model, "temperature": 0, "max_tokens": max_tokens,
                     "messages": [{"role": "system", "content": system},
                                  {"role": "user", "content": user}]})
        return res["choices"][0]["message"]["content"]
    raise ValueError(f"provider không hỗ trợ: {provider}")
