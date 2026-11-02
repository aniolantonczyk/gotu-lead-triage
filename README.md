# Provider and Office Lead Triage (Claude + HubSpot prototype)

A small working prototype of an AI lead triage step for a two-sided dental staffing marketplace. It reads an inbound lead, decides whether it is a dental professional, a dental office, or neither, recommends a HubSpot lifecycle stage, flags low-confidence cases for a human, and logs every decision so performance can be measured.

All data is synthetic. Nothing here uses real company data.

## Results

Run on 2026-11-02 against 32 hand-labeled synthetic leads.

| Run | Audience acc. | Stage acc. | Flagged for review | Parse failures |
|---|---|---|---|---|
| Keyword baseline, easy set (20) | 100% | 100% | 30% | 0 |
| Keyword baseline, hard set (12) | 33% | 25% | 17% | 0 |
| Claude, easy set (20) | 100% | 100% | 10% | 0 |
| Claude, hard set (12) | 100% | 92% | 0% | 0 |

The baseline is what makes these numbers mean something. The keyword rules were tuned on the easy set, which is why they score 100% there and collapse on the hard set.

The single Claude miss is the most useful finding. On "We are hiring hygienists for our office" it returned marketing qualified lead where my label said lead. Reading the prompt back, an office "that states a concrete staffing need (a role, a date, coverage, a new opening)" qualifies, and that lead names a role. The model followed the rubric and my label contradicted it. Its confidence there was 0.70, the lowest in the run, so its uncertainty landed on the genuinely ambiguous case. An accuracy number means nothing until someone audits the label set.

Built with Claude Code as an exercise in AI-assisted marketing operations.

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
