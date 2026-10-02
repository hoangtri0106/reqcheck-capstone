"""Chấm lại TOÀN BỘ đầu ra đã lưu (không gọi API) bằng bộ chấm đã sửa, và so với kết quả chấm lần đầu.
  python evals/regrade.py
Ghi: evals/results/regrade.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "evals"))
from run_evals import load_cases, read_doc, EVALS       # noqa: E402
from pipeline import postprocess_v2, make_user_message   # noqa: E402
from validate import parse_output, is_clean_json         # noqa: E402
from checks import grade                                 # noqa: E402

RUNS = [("v1", "models-gemini-flash-lite-latest"), ("v2", "models-gemini-flash-lite-latest"),
        ("v2", "models-gemma-4-26b-a4b-it")]
summary = {}
for ver, model in RUNS:
    rid = f"{ver}__{model}"
    first = {c["id"]: c for c in json.loads((EVALS / "results" / f"{rid}.json").read_text(encoding="utf-8"))["cases"]}
    rows = []
    for c in load_cases():
        tid, doc = c["test_id"], read_doc(c)
        f = EVALS / "outputs" / rid / f"{tid}.txt"
        gated = ver == "v2" and make_user_message("v2", "", doc)[0] is None
        raw = f.read_text(encoding="utf-8") if f.exists() else None
        if ver == "v2":
            raw = postprocess_v2(raw or "", doc) if (raw is not None or gated) else None
        out, err = parse_output(raw) if raw is not None else (None, "NO_OUTPUT")
        if err:
            passed, fails = False, [err]
        else:
            passed, fails = grade(tid, out, doc, raw, tolerant=True)
        clean = True if gated else (is_clean_json(f.read_text(encoding="utf-8")) if f.exists() else False)
        rows.append({"id": tid, "name": c["name"], "gated_by_code": gated, "first_pass": first[tid]["passed"],
                     "first_failures": first[tid]["failures"], "fixed_pass": passed, "fixed_failures": fails,
                     "status": (out or {}).get("status"), "clean_json": clean})
    summary[rid] = {"first": sum(r["first_pass"] for r in rows), "fixed": sum(r["fixed_pass"] for r in rows),
                    "clean_json_model_calls": sum(r["clean_json"] for r in rows if not r["gated_by_code"]),
                    "model_calls": sum(1 for r in rows if not r["gated_by_code"]), "cases": rows}
(EVALS / "results" / "regrade.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
for rid, s in summary.items():
    print(f"\n{rid}: chấm lần đầu {s['first']}/10 -> bộ chấm đã sửa {s['fixed']}/10 | JSON thuần {s['clean_json_model_calls']}/{s['model_calls']} lượt gọi model")
    for r in s["cases"]:
        flag = "" if r["first_pass"] == r["fixed_pass"] else "   <-- đổi sau khi sửa bộ chấm"
        print(f"  {r['id']} lần đầu={'P' if r['first_pass'] else 'F'} đã sửa={'P' if r['fixed_pass'] else 'F'} status={r['status']}{flag}"
              + ("" if r["fixed_pass"] else f"  | {'; '.join(r['fixed_failures'])[:140]}"))
