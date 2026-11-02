# Provider and Office Lead Triage (Claude + HubSpot prototype)

A small working prototype of an AI lead triage step for a two-sided dental staffing marketplace. It reads an inbound lead, decides whether it is a dental professional, a dental office, or neither, recommends a HubSpot lifecycle stage, flags low-confidence cases for a human, and logs every decision so performance can be measured.

All data is synthetic. Nothing here uses real company data.

## What is real and what is not

| Piece | Status |
|---|---|
| Rules baseline classifier | Built and run. Scores 100% on the 20 easy leads (tuned on them) and 33% audience / 25% stage on 12 hard leads. |
| Claude classifier (`--mode claude`) | Written, not yet run. It needs an API key. Run it and record the real numbers before claiming any result. |
| Decision log (JSONL) | Built and run. |
| Eval script and report | Built and run. |
| HubSpot push and property setup | Written against HubSpot's CRM v3 API, not yet run. Needs a free HubSpot account and a Private App token. |
| Lifecycle stage rubric | My assumption, not GoTu's. Confirm the real stages and rules before relying on it. |

## Setup

```bash
pip install anthropic
export ANTHROPIC_API_KEY=...        # for --mode claude
export HUBSPOT_TOKEN=...            # only for HubSpot steps; use a free test account
```

## Run

```bash
# 1. Baseline, no API key needed
python3 triage.py --mode rules --out runs/rules_baseline.jsonl
python3 triage.py --mode rules --input data/hard_leads.csv --out runs/rules_hard.jsonl

# 2. Claude on both sets
python3 triage.py --mode claude --out runs/claude_easy.jsonl
python3 triage.py --mode claude --input data/hard_leads.csv --out runs/claude_hard.jsonl

# 3. Compare
python3 eval.py runs/rules_baseline.jsonl runs/rules_hard.jsonl runs/claude_easy.jsonl runs/claude_hard.jsonl

# 4. HubSpot (test account only)
python3 setup_hubspot.py                       # once, creates custom properties
python3 triage.py --mode claude --push-hubspot # creates contacts, never overwrites existing ones
```

The model defaults to `claude-sonnet-5-5`. Override with `ANTHROPIC_MODEL`.

## Design choices worth explaining

- **Baseline first.** The rules classifier is the benchmark Claude has to beat. Its misses on the hard set show where an LLM adds value: wording without keywords, vendors and recruiters who mention hygienists, non-English leads, and a first-person owner asking for coverage.
- **Rules are confidently wrong.** On the hard set the rules were wrong at 0.61 average confidence, so a simple confidence threshold would not catch them. Calibration is worth checking for Claude too.
- **Human review queue.** Anything under the confidence threshold (default 0.6, set `REVIEW_THRESHOLD`) or with a parse failure is flagged `needs_review`.
- **License numbers are claims.** The prompt forbids calling a license verified and requires the next action to include verifying it.
- **Prompt versioning.** Every decision records the prompt version, so a change can be traced to a change in results.
- **No overwrites.** An existing HubSpot contact is skipped, not modified.

## Open questions for the business (good to ask in an interview)

- What are GoTu's real lifecycle stages for providers and for offices?
- Are front-desk and other non-clinical job seekers in scope? I labeled them `other`.
- What counts as qualified for a provider: license on file, verified license, or first booked shift?
- If a lead's license number is in the free text but not the field, should it count?
