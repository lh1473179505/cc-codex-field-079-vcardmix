from __future__ import annotations
import json
from pathlib import Path
def rows(path):
    p=Path(path)
    if not p.is_file(): return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
def run_verify(args) -> int:
    exp=json.loads(Path(args.expect).read_text())
    out=Path(args.out)
    got=rows(out/"contacts.jsonl")
    quar=rows(out/"quarantine.jsonl")
    errors=[]
    blob="".join(p.read_text() for p in out.glob("*.jsonl")) + ((out/"report.json").read_text() if (out/"report.json").is_file() else "")
    if "VCARD_SECRET" in blob or "VCARD_SECRET_TOKEN" in blob:
        errors.append("secret leaked into outputs")
    by={r.get("email","").lower():r for r in got}
    if len(by)!=len(got):
        errors.append("duplicate emails")
    if "bob@example.com" in by:
        errors.append("truncated bob must not be ingested")
    exp_by={r["email"]:r for r in exp["contacts"]}
    if set(by)!=set(exp_by):
        errors.append(f"emails extra={sorted(set(by)-set(exp_by))} missing={sorted(set(exp_by)-set(by))}")
    for em,e in exp_by.items():
        g=by.get(em)
        if not g: continue
        for k,v in e.items():
            if g.get(k)!=v:
                errors.append(f"{em}.{k} {g.get(k)!r} != {v!r}")
    if not any(q.get("reason")=="truncated" for q in quar):
        errors.append(f"truncated not quarantined {quar}")
    if errors:
        print("verify failed:")
        for e in errors: print(" -", e)
        return 1
    print("verify ok"); return 0
