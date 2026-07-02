"""
xero_client.py — Axiom Commercial Appraisal
Standalone Xero API client using a Custom Connection (client_credentials
grant -- no browser login, no refresh tokens, locked to one organisation).

STATUS: built 2026-07-01, NOT yet live-tested (no credentials existed at
build time). Token auth + the /Invoices and /Organisation endpoints are
well-documented, stable Xero Accounting API shapes and should work as-is.
The deeper report endpoints (BalanceSheet, ProfitAndLoss) have deeply
nested Rows/Cells JSON that's easy to get wrong without live data to check
against -- get_report() below returns the raw JSON rather than guessing at
a parsed shape; we'll build proper parsing once there's real data to test
against.

Setup
-----
1. developer.xero.com -> My Apps -> New app -> Custom connection.
2. Connect it to your organisation (confirms the $5/mo charge), grant
   read-only scopes for Contacts / Accounting / Transactions.
3. Copy xero_config.json.example to xero_config.json, fill in the
   Client ID and Client Secret it gives you.

Usage
-----
  python xero_client.py test                      # confirms auth works
  python xero_client.py receivables                # who owes what
    python xero_client.py receivables "Northstar"   # filter by contact name
  python xero_client.py org                        # organisation info
"""

import sys
import json
import time
import base64
from pathlib import Path

try:
    import requests
except ImportError:
    print("This module needs the 'requests' package: pip install requests")
    raise

BASE_DIR    = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "xero_config.json"

TOKEN_URL = "https://identity.xero.com/connect/token"
API_BASE  = "https://api.xero.com/api.xro/2.0"


# ─── Config helpers ────────────────────────────────────────────────────────

def _load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"{CONFIG_PATH} not found. Copy xero_config.json.example to "
            f"xero_config.json and fill in client_id/client_secret."
        )
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ─── Auth ───────────────────────────────────────────────────────────────────

def _get_access_token():
    """
    Custom Connections use client_credentials -- no user login, no refresh
    token to manage. Just trade client_id/secret for a short-lived access
    token whenever the cached one has expired.
    """
    cfg = _load_config()
    if cfg.get("access_token") and time.time() < cfg.get("access_token_exp", 0):
        return cfg["access_token"]

    creds = base64.b64encode(
        f"{cfg['client_id']}:{cfg['client_secret']}".encode()
    ).decode()

    resp = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials"},
    )
    resp.raise_for_status()
    data = resp.json()

    cfg["access_token"]     = data["access_token"]
    cfg["access_token_exp"] = time.time() + data.get("expires_in", 1800) - 60
    _save_config(cfg)
    return cfg["access_token"]


def _headers():
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "Accept":        "application/json",
        # Note: no Xero-tenant-id header -- Custom Connections are locked
        # to a single organisation, so it's implicit in the token.
    }


# ─── Organisation info (good connectivity smoke test) ──────────────────────

def get_organisation():
    resp = requests.get(f"{API_BASE}/Organisation", headers=_headers())
    resp.raise_for_status()
    return resp.json()["Organisations"][0]


# ─── Accounts receivable ────────────────────────────────────────────────────

def get_contacts_and_receivables(name_filter=None):
    """
    Outstanding (sent, unpaid) customer invoices -- i.e. who owes what.
    Built on the /Invoices endpoint (Type=ACCREC, Status=AUTHORISED is
    Xero's standard definition of "sent, awaiting payment").

    Returns a list of dicts: contact, invoice_number, invoice_date,
    due_date, amount_due, total, status.
    """
    params = {
        "where": 'Type=="ACCREC" AND Status=="AUTHORISED"',
        "order": "DueDate ASC",
    }
    resp = requests.get(f"{API_BASE}/Invoices", headers=_headers(), params=params)
    resp.raise_for_status()
    invoices = resp.json().get("Invoices", [])

    out = []
    for inv in invoices:
        contact_name = inv.get("Contact", {}).get("Name", "")
        if name_filter and name_filter.lower() not in contact_name.lower():
            continue
        out.append({
            "contact":        contact_name,
            "invoice_number": inv.get("InvoiceNumber"),
            "invoice_date":   inv.get("DateString", inv.get("Date")),
            "due_date":       inv.get("DueDateString", inv.get("DueDate")),
            "amount_due":     inv.get("AmountDue"),
            "total":          inv.get("Total"),
            "status":         inv.get("Status"),
        })
    return out


# ─── Raw report access (parsing deferred until we have live data) ─────────

def get_report(report_name, **params):
    """
    Raw passthrough to Xero's Reports endpoint (e.g. 'ProfitAndLoss',
    'BalanceSheet', 'BankSummary'). Returns the raw nested JSON --
    Xero's report format (Rows -> Cells) is intricate enough that we
    should build real parsing against actual data rather than guess.
    """
    resp = requests.get(f"{API_BASE}/Reports/{report_name}", headers=_headers(), params=params)
    resp.raise_for_status()
    return resp.json()


# ─── CLI ────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "test":
        org = get_organisation()
        print(f"\nConnected OK -- organisation: {org.get('Name')} "
              f"({org.get('LegalName', '')})")

    elif cmd == "org":
        print(json.dumps(get_organisation(), indent=2))

    elif cmd == "receivables":
        name_filter = sys.argv[2] if len(sys.argv) > 2 else None
        rows = get_contacts_and_receivables(name_filter)
        if not rows:
            print("\nNo outstanding receivables found" +
                  (f" matching '{name_filter}'" if name_filter else "") + ".")
            return
        print(f"\n{'Contact':<30} {'Invoice#':<12} {'Due':<12} {'Amount Due':>12}")
        print("-" * 68)
        for r in rows:
            print(f"{r['contact']:<30.30} {r['invoice_number'] or '':<12} "
                  f"{r['due_date'] or '':<12} {r['amount_due']:>12,.2f}")

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
