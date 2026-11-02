# Triage eval report

Synthetic leads, hand-labeled. Small sample: treat as a smoke test, not a benchmark.

| Run | Leads | Audience acc. | Stage acc. | Flagged for review | Parse failures | Avg conf. (right) | Avg conf. (wrong) |
|---|---|---|---|---|---|---|---|
| local_rules.jsonl | 20 | 100% | 100% | 30% | 0 | 0.64 | nan |
| local_rules_hard.jsonl | 12 | 33% | 25% | 17% | 0 | 0.72 | 0.61 |
| claude_easy.jsonl | 20 | 100% | 100% | 10% | 0 | 0.84 | nan |
| claude_hard.jsonl | 12 | 100% | 92% | 0% | 0 | 0.88 | 0.70 |

## Misses: local_rules.jsonl

- none

## Misses: local_rules_hard.jsonl

- lead 21: predicted dental_professional/lead (conf 0.70), expected dental_office/marketingqualifiedlead. Text: "I need someone to cover my Saturdays."
- lead 22: predicted dental_professional/lead (conf 0.70), expected other/subscriber. Text: "We place hygienists nationwide and want to list our candidates."
- lead 23: predicted dental_professional/lead (conf 0.70), expected other/subscriber. Text: "MBA student researching dental staffing for a class project."
- lead 24: predicted other/subscriber (conf 0.30), expected dental_professional/marketingqualifiedlead. Text: "Soy higienista dental con licencia en Florida. Busco turnos."
- lead 25: predicted dental_professional/lead (conf 0.70), expected other/subscriber. Text: "We make ergonomic loupes for hygienists. Can we sponsor you?"
- lead 26: predicted other/subscriber (conf 0.30), expected dental_office/lead. Text: "Looking to learn how you could help staff our clinics."
- lead 28: predicted dental_professional/lead (conf 0.70), expected dental_office/marketingqualifiedlead. Text: "Need a hygienist next Tuesday. Can you help?"
- lead 29: predicted dental_professional/lead (conf 0.70), expected dental_professional/marketingqualifiedlead. Text: "Active FL license DDS 30211. Looking for shifts in Dade."
- lead 31: predicted dental_professional/lead (conf 0.70), expected other/subscriber. Text: "I need a dentist for a toothache. Can you book me?"

## Misses: claude_easy.jsonl

- none

## Misses: claude_hard.jsonl

- lead 32: predicted dental_office/marketingqualifiedlead (conf 0.70), expected dental_office/lead. Text: "We are hiring hygienists for our office."
