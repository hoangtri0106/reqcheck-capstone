"""Điều phối workflow: precheck (code) -> model -> hậu xử lý/validate (code) -> người duyệt.
Dùng:
  python src/pipeline.py --version v2 --provider anthropic --model claude-sonnet-5-5 \
         --input demo/sample-inputs/tc01_happy_path.txt --format md
"""
import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from precheck import precheck, build_user_message          # noqa: E402
from validate import parse_output, validate_output          # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INSTRUCTION = "Phân tích tài liệu yêu cầu này và tạo Acceptance Criteria."


def load_prompt(version: str) -> str:
    return (ROOT / "instructions" / f"system-prompt-{version}.md").read_text(encoding="utf-8")


def make_user_message(version: str, instruction: str, document: str):
    """Trả về (user_message | None, PreCheck | None). None nghĩa là bị chặn bởi code (không gọi model)."""
    if version == "v1":
        return build_user_message(instruction, document), None
    pc = precheck(document)
    if pc.refuse:
        return None, pc
    return build_user_message(instruction, pc.clean_text, pc.flags), pc


def postprocess_v2(raw: str, document: str) -> str:
    """Chạy lại precheck để: (a) lấy đầu ra do code sinh nếu bị chặn, (b) gắn cảnh báo injection bằng code."""
    pc = precheck(document)
    if pc.refuse:
        return json.dumps(pc.refusal_output(), ensure_ascii=False)
    out, err = parse_output(raw)
    if err:
        return raw
    existing = {w.get("code") for w in out.get("warnings", []) if isinstance(w, dict)}
    for f in pc.flags:
        if f["code"] in existing:
            continue
        out.setdefault("warnings", []).append(f)
    return json.dumps(out, ensure_ascii=False)


def audit_log(version, model, doc, status, errs):
    """Lớp 6 - Audit logging: chỉ lưu dấu vết (hash, số từ, trạng thái), KHÔNG lưu nội dung tài liệu."""
    d = ROOT / "logs"
    d.mkdir(exist_ok=True)
    rec = {"time": datetime.datetime.now().isoformat(timespec="seconds"), "version": version, "model": model,
           "doc_sha256": hashlib.sha256(doc.encode("utf-8")).hexdigest()[:16], "doc_words": len(doc.split()),
           "status": status, "validation_errors": errs}
    with open(d / "runs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def render_markdown(out: dict) -> str:
    L = [f"# Kết quả ReqCheck — trạng thái: **{out.get('status')}**", ""]
    if out.get("refusal_reason"):
        L += [f"**Lý do từ chối:** {out['refusal_reason']}", ""]
    if out.get("questions"):
        L += ["## Câu hỏi cần người dùng làm rõ", ""]
        for q in out["questions"]:
            L.append(f"- **[{q['type']}] {q['id']}**: {q['question']}")
            for qt in q.get("quotes", []):
                L.append(f"  - trích: “{qt}”")
        L.append("")
    if out.get("requirements"):
        L += ["## Yêu cầu đã tách", ""] + [f"- **{r['id']}**: {r['text']}" for r in out["requirements"]] + [""]
    if out.get("acceptance_criteria"):
        L += ["## Acceptance Criteria (cần người duyệt trước khi đưa vào Jira/Trello)", ""]
        for a in out["acceptance_criteria"]:
            L.append(f"- [ ] **{a['id']}** ({a['req_id']}, {a['type']}) — Given {a['given']}; "
                     f"When {a['when']}; Then {a['then']}")
        L.append("")
    if out.get("warnings"):
        L += ["## Cảnh báo", ""] + [f"- `{w.get('code')}`: {w.get('message')}" for w in out["warnings"]]
    return "\n".join(L)


def main():
    from llm_adapter import call_llm
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", choices=["v1", "v2"], default="v2")
    ap.add_argument("--provider", choices=["anthropic", "openai"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url")
    ap.add_argument("--input", required=True, help="file .txt chứa tài liệu yêu cầu")
    ap.add_argument("--instruction", default=DEFAULT_INSTRUCTION)
    ap.add_argument("--format", choices=["json", "md"], default="md")
    a = ap.parse_args()

    doc = Path(a.input).read_text(encoding="utf-8")
    msg, pc = make_user_message(a.version, a.instruction, doc)
    if msg is None:
        raw = json.dumps(pc.refusal_output(), ensure_ascii=False)
    else:
        raw = call_llm(load_prompt(a.version), msg, a.provider, a.model, a.base_url)
        if a.version == "v2":
            raw = postprocess_v2(raw, doc)
    out, err = parse_output(raw)
    if err:
        print("KHÔNG PARSE ĐƯỢC ĐẦU RA — chuyển người xử lý.\n", err, "\n", raw)
        sys.exit(2)
    errs = validate_output(out, doc)
    audit_log(a.version, a.model, doc, out.get("status"), errs)
    print(json.dumps(out, ensure_ascii=False, indent=2) if a.format == "json" else render_markdown(out))
    if errs:
        print("\n⚠️ VALIDATION FAILED — cần người duyệt kiểm tra thủ công:\n- " + "\n- ".join(errs))
        sys.exit(1)


if __name__ == "__main__":
    main()
