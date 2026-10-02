"""Chạy và chấm bộ Eval Suite 10 kịch bản.

Quy trình (chi tiết trong README):
  A) Tự động (có API key):   python evals/run_evals.py run --version v1 --provider anthropic --model <tên-model>
  B) Thủ công (chat miễn phí): python evals/run_evals.py prepare --version v1 --model <nhãn>
       -> dán system prompt + từng file TCxx.input.txt vào chatbot, lưu câu trả lời vào TCxx.txt
       -> python evals/run_evals.py score --version v1 --model <nhãn>
  C) So sánh:                python evals/run_evals.py compare --v1 v1__<nhãn> --v2 v2__<nhãn>
"""
import argparse
import csv
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "evals"))
from pipeline import make_user_message, load_prompt, postprocess_v2   # noqa: E402
from validate import parse_output                                     # noqa: E402
from checks import grade, extra_metrics                               # noqa: E402

EVALS = ROOT / "evals"


def slug(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", s).strip("-")


def run_id(version, model):
    return f"{version}__{slug(model)}"


def load_cases():
    with open(EVALS / "test-cases.csv", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def read_doc(case):
    return (ROOT / case["input_file"]).read_text(encoding="utf-8")


def outdir(rid):
    d = EVALS / "outputs" / rid
    d.mkdir(parents=True, exist_ok=True)
    return d


def cmd_prepare(a):
    rid = run_id(a.version, a.model)
    d = outdir(rid)
    print(f"System prompt cần dán: instructions/system-prompt-{a.version}.md")
    print(f"Thư mục làm việc: {d.relative_to(ROOT)}\n")
    for c in load_cases():
        msg, pc = make_user_message(a.version, c["user_instruction"], read_doc(c))
        if msg is None:
            print(f"{c['test_id']}: bị chặn bởi precheck ({pc.code}) -> KHÔNG cần chạy model, code tự sinh kết quả.")
            continue
        (d / f"{c['test_id']}.input.txt").write_text(msg, encoding="utf-8")
        print(f"{c['test_id']}: dán {c['test_id']}.input.txt vào chatbot, lưu câu trả lời vào {c['test_id']}.txt")


def cmd_run(a):
    from llm_adapter import call_llm
    rid = run_id(a.version, a.model)
    d = outdir(rid)
    system = load_prompt(a.version)
    for c in load_cases():
        msg, pc = make_user_message(a.version, c["user_instruction"], read_doc(c))
        if msg is None:
            print(f"{c['test_id']}: chặn bởi precheck, bỏ qua gọi model")
            continue
        out_file = d / f"{c['test_id']}.txt"
        if out_file.exists():
            print(f"{c['test_id']}: đã có kết quả, bỏ qua")
            continue
        raw = call_llm(system, msg, a.provider, a.model, a.base_url, max_tokens=a.max_tokens)
        out_file.write_text(raw, encoding="utf-8")
        print(f"{c['test_id']}: đã lưu")
    cmd_score(a)


def score_run(version, model):
    rid = run_id(version, model)
    d = EVALS / "outputs" / rid
    results = []
    for c in load_cases():
        tid, doc = c["test_id"], read_doc(c)
        f = d / f"{tid}.txt"
        raw = f.read_text(encoding="utf-8") if f.exists() else None
        if version == "v2":
            raw = postprocess_v2(raw or "", doc) if (raw or not make_user_message("v2", "", doc)[0]) else None
        if raw is None:
            results.append({"id": tid, "name": c["name"], "expected": c["expected_behavior"], "ran": False,
                            "passed": False, "status": "-", "failures": ["CHƯA CÓ ĐẦU RA (chưa chạy)"], "extra": {}})
            continue
        out, err = parse_output(raw)
        if err:
            results.append({"id": tid, "name": c["name"], "expected": c["expected_behavior"], "ran": True,
                            "passed": False, "status": "-", "failures": [err], "extra": {}})
            continue
        ok, fails = grade(tid, out, doc, raw)
        results.append({"id": tid, "name": c["name"], "expected": c["expected_behavior"], "ran": True,
                        "passed": ok, "status": out.get("status"), "failures": fails,
                        "extra": extra_metrics(tid, out) if isinstance(out.get("warnings"), list) else {}})
    ran = [r for r in results if r["ran"]]
    summary = {"run_id": rid, "version": version, "model": model,
               "date": datetime.datetime.now().isoformat(timespec="seconds"),
               "cases_run": len(ran), "passed": sum(r["passed"] for r in results), "total": len(results),
               "cases": results}
    (EVALS / "results").mkdir(exist_ok=True)
    (EVALS / "results" / f"{rid}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                                    encoding="utf-8")
    return summary


def write_report(s):
    L = [f"# Bảng ghi nhận kết quả kiểm thử — {s['version'].upper()} — model: {s['model']}", "",
         f"Ngày chạy: {s['date']} · Đạt **{s['passed']}/{s['total']}** kịch bản "
         f"({100 * s['passed'] // s['total']}%) · Số ca đã chạy: {s['cases_run']}/{s['total']}", "",
         "| ID | Kịch bản | Kỳ vọng | Hành vi thực tế (do code chấm) | Kết quả | Nguyên nhân gốc rễ | Hành động sửa |",
         "|---|---|---|---|---|---|---|"]
    for r in s["cases"]:
        actual = f"status=`{r['status']}`" + ("" if r["passed"] else "; " + "; ".join(r["failures"]))
        mark = "✅ PASS" if r["passed"] else "❌ FAIL"
        rc = "—" if r["passed"] else "_(điền theo 5-Whys, xem failure-analysis.md)_"
        L.append(f"| {r['id']} | {r['name']} | {r['expected']} | {actual} | {mark} | {rc} | {rc} |")
    extras = [f"{r['id']}: injection_flagged={r['extra']['injection_flagged']}"
              for r in s["cases"] if r["extra"].get("injection_flagged") is not None]
    if extras:
        L += ["", "Chỉ số phụ: " + "; ".join(extras)]
    p = EVALS / "results" / f"report-{s['run_id']}.md"
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    return p


def cmd_score(a):
    s = score_run(a.version, a.model)
    p = write_report(s)
    print(f"\n{s['run_id']}: đạt {s['passed']}/{s['total']} (đã chạy {s['cases_run']}/{s['total']})")
    for r in s["cases"]:
        print(f"  {r['id']} {'PASS' if r['passed'] else 'FAIL'}  {r['name']}"
              + ("" if r["passed"] else f"  -> {'; '.join(r['failures'])[:150]}"))
    print(f"\nĐã ghi: {p.relative_to(ROOT)}")


def cmd_compare(a):
    v1 = json.loads((EVALS / "results" / f"{a.v1}.json").read_text(encoding="utf-8"))
    v2 = json.loads((EVALS / "results" / f"{a.v2}.json").read_text(encoding="utf-8"))
    m1 = {r["id"]: r for r in v1["cases"]}
    m2 = {r["id"]: r for r in v2["cases"]}
    L = ["# Bảng đối chiếu tiến bộ định lượng V1 ↔ V2", "",
         f"- V1: `{a.v1}` — đạt **{v1['passed']}/{v1['total']}**",
         f"- V2: `{a.v2}` — đạt **{v2['passed']}/{v2['total']}**", "",
         "| ID | Kịch bản | V1 | V2 | Ghi chú |", "|---|---|---|---|---|"]
    regress = []
    for tid in m1:
        p1, p2 = m1[tid]["passed"], m2[tid]["passed"]
        note = ""
        if p1 and not p2:
            note = "⚠️ HỒI QUY (V1 đạt, V2 trượt)"
            regress.append(tid)
        elif not p2:
            note = "; ".join(m2[tid]["failures"])[:120]
        L.append(f"| {tid} | {m1[tid]['name']} | {'✅' if p1 else '❌'} | {'✅' if p2 else '❌'} | {note} |")
    L += ["", f"**Hồi quy (regression):** {', '.join(regress) if regress else 'không có ca nào V1 đạt mà V2 trượt.'}"]
    p = ROOT / "docs" / "comparison-v1-v2.md"
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"\nĐã ghi: {p.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("prepare", "run", "score"):
        p = sub.add_parser(name)
        p.add_argument("--version", choices=["v1", "v2"], required=True)
        p.add_argument("--model", required=True, help="tên model (hoặc nhãn nếu chạy thủ công)")
        if name == "run":
            p.add_argument("--provider", choices=["anthropic", "openai"], required=True)
            p.add_argument("--base-url")
            p.add_argument("--max-tokens", type=int, default=4000, help="tăng lên (vd 8000) nếu model hay bị cắt cụt")
    p = sub.add_parser("compare")
    p.add_argument("--v1", required=True)
    p.add_argument("--v2", required=True)
    a = ap.parse_args()
    {"prepare": cmd_prepare, "run": cmd_run, "score": cmd_score, "compare": cmd_compare}[a.cmd](a)


if __name__ == "__main__":
    main()
