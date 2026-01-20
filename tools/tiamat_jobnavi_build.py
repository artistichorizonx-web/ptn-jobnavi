import json, re, urllib.request
from datetime import datetime, timezone
import os

def stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent":"PTN-TIAMAT/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8","replace"))

def norm(s):
    return re.sub(r"\s+"," ", s or "").strip()

def main():
    stp = stamp()
    errors = []
    jobs = []

    try:
        rem = fetch("https://remotive.com/api/remote-jobs")
        for j in (rem.get("jobs", []) or [])[:200]:
            jobs.append({
                "id": f"remotive:{j.get('id')}",
                "source": "remotive",
                "title": j.get("title","") or "",
                "company": j.get("company_name","") or "",
                "location": j.get("candidate_required_location","") or "Remote",
                "remote": True,
                "url": j.get("url","") or "",
                "posted_at": j.get("publication_date","") or "",
                "salary": j.get("salary","") or "",
                "tags": (j.get("tags", []) or [])[:12],
                "snippet": norm(j.get("description",""))[:260],
            })
    except Exception as e:
        errors.append(f"remotive_fetch_failed:{e}")

    try:
        arb = fetch("https://www.arbeitnow.com/api/job-board-api")
        for j in (arb.get("data", []) or [])[:200]:
            jobs.append({
                "id": f"arbeitnow:{j.get('slug','')}",
                "source": "arbeitnow",
                "title": j.get("title","") or "",
                "company": j.get("company_name","") or "",
                "location": j.get("location","") or "",
                "remote": bool(j.get("remote", False)),
                "url": j.get("url","") or "",
                "posted_at": j.get("created_at","") or "",
                "salary": "",
                "tags": ((j.get("tags", []) or []) + (j.get("job_types", []) or []))[:12],
                "snippet": norm(j.get("description",""))[:260],
            })
    except Exception as e:
        errors.append(f"arbeitnow_fetch_failed:{e}")

    seen = set()
    out = []
    for j in jobs:
        key = (j.get("title",""), j.get("company",""), j.get("url",""))
        if key in seen:
            continue
        seen.add(key)
        out.append(j)

    def size_ok(items):
        blob = json.dumps({"jobs": items}, ensure_ascii=False).encode("utf-8")
        return len(blob) <= 900_000

    while out and not size_ok(out):
        out = out[: max(20, int(len(out) * 0.8))]

    os.makedirs("docs", exist_ok=True)
    with open("docs/jobs_latest.json","w",encoding="utf-8") as f:
        json.dump({"generated_at": stp, "count": len(out), "errors": errors, "jobs": out}, f, ensure_ascii=False, indent=2)
    with open("docs/health.json","w",encoding="utf-8") as f:
        json.dump({"ok": True, "generated_at": stp, "job_errors": errors}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
