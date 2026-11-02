#!/usr/bin/env python3
"""Lead triage for a two-sided dental staffing marketplace.

Classifies each inbound lead (dental professional / dental office / other), recommends a
HubSpot lifecycle stage, logs every decision to a JSONL file, and can optionally push the
result to a HubSpot contact. All leads in data/ are synthetic.

Modes:
  --mode rules    keyword baseline, no API key needed (also the benchmark Claude must beat)
  --mode claude   Claude via the Anthropic API (needs ANTHROPIC_API_KEY)
"""
import argparse
import csv
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
PROMPT_VERSION = "triage_v1"
AUDIENCES = {"dental_professional", "dental_office", "other"}
STAGES = {"subscriber", "lead", "marketingqualifiedlead"}
REVIEW_THRESHOLD = float(os.environ.get("REVIEW_THRESHOLD", "0.6"))
DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")


# ---------------------------------------------------------------- classifiers
OFFICE_WORDS = (
    "our practice", "we are a", "we have", "our office", "locations", "our team",
    "office manager", "practice administrator", "operations director",
    "pricing works for offices",
)
NEED_WORDS = ("need", "urgent", "opening", "coverage", "starting")
PRO_WORDS = ("hygienist", "dentist", "dds", "dmd", "rdh", "dental assistant", "student")


def classify_rules(lead):
    """Keyword baseline. Deliberately simple so Claude has something real to beat."""
    text = f"{lead['job_title']} {lead['company']} {lead['form_text']}".lower()
    has_license = bool(lead["license_number"].strip())
    if any(w in text for w in OFFICE_WORDS):
        need = any(w in text for w in NEED_WORDS)
        return {
            "audience": "dental_office",
            "recommended_stage": "marketingqualifiedlead" if need else "lead",
            "confidence": 0.8 if need else 0.65,
            "reason": "Office wording matched" + (" with a stated staffing need." if need else " with no stated need."),
            "next_action": "route to office sales" if need else "send office nurture",
        }
    if any(w in text for w in PRO_WORDS):
        return {
            "audience": "dental_professional",
            "recommended_stage": "marketingqualifiedlead" if has_license else "lead",
            "confidence": 0.85 if has_license else 0.7,
            "reason": "Clinical role keyword matched" + (" and a license number was provided." if has_license else "."),
            "next_action": "verify license and start onboarding" if has_license else "request license number",
        }
    return {
        "audience": "other",
        "recommended_stage": "subscriber",
        "confidence": 0.3,
        "reason": "No office or clinical signal found.",
        "next_action": "human review",
    }


def parse_decision(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in response")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON: {e}")
    for key in ("audience", "recommended_stage", "confidence", "reason", "next_action"):
        if key not in data:
            raise ValueError(f"missing key: {key}")
    if data["audience"] not in AUDIENCES:
        raise ValueError(f"bad audience: {data['audience']}")
    if data["recommended_stage"] not in STAGES:
        raise ValueError(f"bad stage: {data['recommended_stage']}")
    data["confidence"] = max(0.0, min(1.0, float(data["confidence"])))
    return data


def classify_claude(lead, client, model):
    system = (ROOT / "prompts" / f"{PROMPT_VERSION}.md").read_text()
    payload = {k: lead[k] for k in ("source", "job_title", "company", "form_text", "license_number")}
    last_error = None
    for _ in range(2):  # one retry on a malformed response
        msg = client.messages.create(
            model=model,
            max_tokens=400,
            system=system,
            messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        try:
            return parse_decision(text), "ok"
        except ValueError as e:
            last_error = str(e)
    return {
        "audience": "unknown",
        "recommended_stage": "lead",
        "confidence": 0.0,
        "reason": f"parse_failure: {last_error}",
        "next_action": "human review",
    }, "parse_failure"


# ------------------------------------------------------------------- HubSpot
HS_BASE = "https://api.hubapi.com"


def hs_request(method, path, token, body=None):
    req = urllib.request.Request(
        HS_BASE + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"message": raw.decode(errors="replace")[:200]}


def push_to_hubspot(lead, decision, needs_review, token):
    """Create a contact. Existing contacts (409) are skipped, never overwritten."""
    props = {
        "email": lead["email"],
        "jobtitle": lead["job_title"],
        "company": lead["company"],
        "lifecyclestage": decision["recommended_stage"],
        "gotu_audience": decision["audience"],
        "gotu_ai_confidence": decision["confidence"],
        "gotu_ai_reason": decision["reason"],
        "gotu_needs_review": "true" if needs_review else "false",
        "gotu_prompt_version": PROMPT_VERSION,
    }
    props = {k: v for k, v in props.items() if v not in ("", None)}
    status, body = hs_request("POST", "/crm/v3/objects/contacts", token, {"properties": props})
    if status in (200, 201):
        return "created"
    if status == 409:
        return "exists_skipped"
    return f"error_{status}: {body.get('message', '')[:120]}"


# ---------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default=str(ROOT / "data" / "synthetic_leads.csv"))
    ap.add_argument("--mode", choices=["rules", "claude"], default="rules")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--out", help="decision log path (JSONL). Default: runs/<mode>_<timestamp>.jsonl")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--push-hubspot", action="store_true", help="create contacts in HubSpot (needs HUBSPOT_TOKEN)")
    args = ap.parse_args()

    client = None
    if args.mode == "claude":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit("Set ANTHROPIC_API_KEY to use --mode claude (or run --mode rules).")
        import anthropic
        client = anthropic.Anthropic()
    token = os.environ.get("HUBSPOT_TOKEN")
    if args.push_hubspot and not token:
        raise SystemExit("Set HUBSPOT_TOKEN to use --push-hubspot.")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = Path(args.out) if args.out else ROOT / "runs" / f"{args.mode}_{stamp}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(args.input, newline="", encoding="utf-8") as f:
        leads = list(csv.DictReader(f))
    if args.limit:
        leads = leads[: args.limit]

    with open(out_path, "w", encoding="utf-8") as log:
        for lead in leads:
            t0 = time.time()
            if args.mode == "rules":
                decision, status = classify_rules(lead), "ok"
            else:
                decision, status = classify_claude(lead, client, args.model)
            needs_review = status != "ok" or decision["confidence"] < REVIEW_THRESHOLD
            hubspot = push_to_hubspot(lead, decision, needs_review, token) if args.push_hubspot else "not_pushed"
            record = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "lead_id": lead["id"],
                "mode": args.mode,
                "model": args.model if args.mode == "claude" else None,
                "prompt_version": PROMPT_VERSION if args.mode == "claude" else "rules_v1",
                "status": status,
                "needs_review": needs_review,
                "latency_s": round(time.time() - t0, 3),
                "hubspot": hubspot,
                "input": {k: lead[k] for k in ("source", "job_title", "company", "license_number", "form_text")},
                "decision": decision,
            }
            log.write(json.dumps(record, ensure_ascii=False) + "\n")
            flag = "REVIEW" if needs_review else "ok"
            print(f"lead {lead['id']:>2}  {decision['audience']:<20} {decision['recommended_stage']:<24} {decision['confidence']:.2f}  {flag}")
    print(f"\nDecision log: {out_path}")


if __name__ == "__main__":
    main()
