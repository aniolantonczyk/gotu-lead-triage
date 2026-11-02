#!/usr/bin/env python3
"""One-time setup: create the custom contact properties triage.py writes to.

Needs HUBSPOT_TOKEN (a Private App token with crm.schemas.contacts.write and
crm.objects.contacts.write scopes). Use a free HubSpot developer or test account,
never a production portal.
"""
import os

from triage import hs_request

PROPS = [
    ("gotu_audience", "AI audience", "string", "text"),
    ("gotu_ai_confidence", "AI confidence", "number", "number"),
    ("gotu_ai_reason", "AI reason", "string", "textarea"),
    ("gotu_needs_review", "AI needs review", "string", "text"),
    ("gotu_prompt_version", "AI prompt version", "string", "text"),
]


def main():
    token = os.environ.get("HUBSPOT_TOKEN")
    if not token:
        raise SystemExit("Set HUBSPOT_TOKEN first.")
    for name, label, ptype, field in PROPS:
        body = {"name": name, "label": label, "type": ptype, "fieldType": field, "groupName": "contactinformation"}
        status, resp = hs_request("POST", "/crm/v3/properties/contacts", token, body)
        if status in (200, 201):
            print(f"created  {name}")
        elif status == 409:
            print(f"exists   {name}")
        else:
            print(f"error {status} on {name}: {resp.get('message', '')[:150]}")


if __name__ == "__main__":
    main()
