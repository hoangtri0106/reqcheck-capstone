"""Lớp 4 - Output Validation Gate (chạy bằng CODE).
Bằng chứng phải quan sát được: file này kiểm tra JSON, schema, trích dẫn nguyên văn và số liệu bịa.
"""
import json
import re
import unicodedata

STATUSES = {"OK", "NEEDS_CLARIFICATION", "REFUSED"}
Q_TYPES = {"missing", "ambiguous", "contradiction", "illogical"}
AC_TYPES = {"happy", "boundary", "negative"}
ZW = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u200e\u200f\u2060\ufeff"), None)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "").translate(ZW)
    s = re.sub(r"[“”\"'‘’]", "", s)
    return re.sub(r"\s+", " ", s).strip().casefold()


def parse_output(raw: str, strict: bool = False):
    """Trả về (dict|None, lỗi|None).
    strict=True : chỉ chấp nhận đầu ra là MỘT khối JSON (cho phép bọc ```json```), mọi chữ thừa đều là lỗi.
    strict=False: chịu được lời chào/phần suy nghĩ rò rỉ; lấy đối tượng JSON hợp lệ CUỐI CÙNG có khóa 'status'."""
    if raw is None:
        return None, "NO_OUTPUT"
    t = raw.strip()
    t0 = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.IGNORECASE)
    if strict:
        try:
            return json.loads(t0), None
        except json.JSONDecodeError as e:
            return None, f"INVALID_JSON: {e}"
    # bỏ phần "suy nghĩ" rò rỉ (<thought>...</thought>): JSON nháp nằm trong đó KHÔNG được tính là câu trả lời
    t = re.sub(r"<thought>.*?</thought>", "", t, flags=re.DOTALL | re.IGNORECASE)
    if "<thought>" in t.lower():
        return None, "INVALID_JSON: đầu ra bị cắt cụt ngay trong phần suy nghĩ, chưa có câu trả lời cuối"
    dec = json.JSONDecoder()
    best = None
    for m in re.finditer(r"\{", t):
        try:
            obj, _ = dec.raw_decode(t[m.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "status" in obj:
            best = obj
    if best is None:
        return None, "INVALID_JSON: không tìm thấy đối tượng JSON hoàn chỉnh (có thể bị cắt cụt)"
    return best, None


def is_clean_json(raw: str) -> bool:
    """Đầu ra có đúng là chỉ một khối JSON không (tuân thủ 'chỉ trả JSON')?"""
    return parse_output(raw, strict=True)[0] is not None


def _nums(text: str):
    out = set()
    # bỏ qua số dính liền chữ cái (mã định danh như YC2, R1, AC3) để nhãn không làm nhiễu phép kiểm tra
    for m in re.findall(r"(?<![^\W\d_])\d+(?:[.,]\d+)*", text or ""):
        digits = re.sub(r"[.,]", "", m)
        out.add(str(int(digits)))
    return out


def _quote_in_doc(quote: str, doc_n: str) -> bool:
    segs = [s for s in re.split(r"…|\.\.\.", quote) if len(norm(s)) >= 3]
    return bool(segs) and all(norm(s) in doc_n for s in segs)


def validate_output(out: dict, doc: str, boundary_tolerance: bool = True):
    """Trả về list lỗi (rỗng = hợp lệ)."""
    errs = []
    if not isinstance(out, dict):
        return ["SCHEMA: đầu ra không phải object"]
    for k in ("status", "refusal_reason", "questions", "requirements", "acceptance_criteria", "warnings"):
        if k not in out:
            errs.append(f"SCHEMA: thiếu trường '{k}'")
    if errs:
        return errs
    if out["status"] not in STATUSES:
        errs.append(f"SCHEMA: status '{out['status']}' không hợp lệ")
    for name in ("questions", "requirements", "acceptance_criteria", "warnings"):
        if not isinstance(out[name], list):
            errs.append(f"SCHEMA: '{name}' phải là danh sách")
    if errs:
        return errs

    doc_n = norm(doc)
    doc_nums = _nums(doc)

    for q in out["questions"]:
        if not isinstance(q, dict) or q.get("type") not in Q_TYPES or not q.get("question"):
            errs.append(f"SCHEMA: câu hỏi sai định dạng: {str(q)[:60]}")
            continue
        quotes = q.get("quotes", [])
        if not isinstance(quotes, list):
            errs.append("SCHEMA: 'quotes' phải là danh sách")
            continue
        for qt in quotes:
            if not _quote_in_doc(str(qt), doc_n):
                errs.append(f"HALLUCINATION: trích dẫn không có trong tài liệu: “{str(qt)[:60]}”")

    req_ids = set()
    for r in out["requirements"]:
        if not isinstance(r, dict) or not r.get("id") or not r.get("text"):
            errs.append("SCHEMA: requirement thiếu id/text")
            continue
        req_ids.add(r["id"])
        sq = r.get("source_quote", "")
        if not sq or not _quote_in_doc(str(sq), doc_n):
            errs.append(f"HALLUCINATION: source_quote của {r['id']} không có trong tài liệu")
        bad = _nums(r["text"]) - doc_nums - {"0", "1"}
        if bad:
            errs.append(f"HALLUCINATION: số liệu không có trong tài liệu ở {r['id']}: {sorted(bad)}")

    ac_req_ids = set()
    for a in out["acceptance_criteria"]:
        if not isinstance(a, dict) or a.get("type") not in AC_TYPES or \
                not all(a.get(k) for k in ("id", "req_id", "given", "when", "then")):
            errs.append(f"SCHEMA: acceptance criterion sai định dạng: {str(a)[:60]}")
            continue
        ac_req_ids.add(a["req_id"])
        if a["req_id"] not in req_ids:
            errs.append(f"SCHEMA: {a['id']} trỏ tới req_id '{a['req_id']}' không tồn tại")
        allowed = doc_nums | {"0", "1"}
        if boundary_tolerance and a["type"] in ("boundary", "negative"):
            # phân tích giá trị biên: ví dụ ngưỡng 8 -> thử 7 và 9 là hợp lệ, không phải bịa
            allowed |= {str(int(n) + d) for n in doc_nums for d in (-1, 1) if int(n) + d >= 0}
        bad = _nums(" ".join(str(a[k]) for k in ("given", "when", "then"))) - allowed
        if bad:
            errs.append(f"HALLUCINATION: số liệu không có trong tài liệu ở {a['id']}: {sorted(bad)}")

    st = out["status"]
    if st == "REFUSED":
        if not out["refusal_reason"]:
            errs.append("CONSISTENCY: REFUSED nhưng thiếu refusal_reason")
        if out["requirements"] or out["acceptance_criteria"] or out["questions"]:
            errs.append("CONSISTENCY: REFUSED nhưng vẫn có requirements/questions/acceptance_criteria")
    elif st == "NEEDS_CLARIFICATION":
        if not out["questions"]:
            errs.append("CONSISTENCY: NEEDS_CLARIFICATION nhưng không có câu hỏi nào")
        if out["acceptance_criteria"]:
            errs.append("CONSISTENCY: NEEDS_CLARIFICATION nhưng vẫn sinh acceptance_criteria")
    elif st == "OK":
        if out["questions"]:
            errs.append("CONSISTENCY: status OK nhưng còn câu hỏi chưa giải quyết")
        if not out["acceptance_criteria"]:
            errs.append("CONSISTENCY: status OK nhưng không có acceptance_criteria")
        missing = req_ids - ac_req_ids
        if missing:
            errs.append(f"COVERAGE: yêu cầu chưa có tiêu chí nghiệm thu: {sorted(missing)}")
    return errs
