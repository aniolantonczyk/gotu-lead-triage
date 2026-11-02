# SOP: Inbound Lead Triage (AI-assisted)

Owner: [name]   Version: 1.0   Prompt version: triage_v1   Status: prototype, synthetic data only

## Purpose
Classify each inbound lead as dental professional, dental office, or other, recommend a HubSpot lifecycle stage, and route uncertain cases to a person.

## Trigger
A new lead arrives from a form, ad, job board, or direct mail response. In the prototype this is a row in a CSV. In production it would be a HubSpot form submission or contact-created workflow.

## Inputs
`source`, `job_title`, `company`, `license_number`, `form_text`. Any field may be blank.

## Outputs
Per lead: `audience`, `recommended_stage`, `confidence` (0 to 1), `reason`, `next_action`, plus `needs_review`. Written to the decision log, and optionally to HubSpot custom properties (`gotu_audience`, `gotu_ai_confidence`, `gotu_ai_reason`, `gotu_needs_review`, `gotu_prompt_version`).

## Procedure
1. Run triage on the new leads (`triage.py --mode claude`).
2. Review every lead with `needs_review = true` before it enters a nurture sequence or reaches sales.
3. Verify any license number against the state board before treating a provider as qualified. The model never verifies licenses.
4. Spot check 10 percent of non-flagged decisions each week against the source text.
5. Log corrections (lead id, what the model said, what is right). Use them as new test cases in `data/hard_leads.csv`.

## Monitoring
Run `eval.py` on the labeled set after every prompt or model change, and review these weekly:
- Audience and stage accuracy on the labeled set.
- Share of leads flagged for review. A sudden drop can mean over-confidence, a sudden rise can mean an input format change.
- Average confidence on correct versus incorrect decisions. If they match, confidence is not a usable signal.
- Parse failures. Any non-zero count needs a look at the raw response.

## Failure handling
| Symptom | Likely cause | Action |
|---|---|---|
| Parse failure | Model returned text outside the JSON format | Retry runs once automatically. If it persists, inspect the raw response and tighten the prompt. |
| Audience accuracy drops | New lead source or wording, prompt drift, model change | Add examples to the hard set, compare against the previous prompt version. |
| HubSpot error 409 | Contact already exists | Skipped by design. Update the existing record manually or through a reviewed workflow. |
| HubSpot rejects lifecycle stage | HubSpot generally will not move a contact to an earlier stage through the API | Clear the property first, or review manually. Confirm behavior in your portal. |
| API errors or rate limits | Provider or network issue | Re-run the batch. Decisions are logged per lead, so completed rows are not lost. |

## Change control
- Edit the prompt only by creating a new file (`triage_v2.md`) and bumping `PROMPT_VERSION`.
- Run the full labeled set on the old and new versions and compare before switching.
- Record the reason for the change and the before and after numbers in this document.

## Assumptions to confirm with the business
- Lifecycle stage definitions and the qualification rule for providers and offices.
- Whether non-clinical job seekers are in scope.
- Where a license number in free text should count as provided.
