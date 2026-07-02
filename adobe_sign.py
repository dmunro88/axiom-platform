"""
adobe_sign.py — Axiom Commercial Appraisal
Adobe Acrobat Sign integration: send the engagement letter for signature,
check status, and pull the signed copy back down.

STATUS: built 2026-07-01, NOT yet live-tested against a real Acrobat Sign
account (no credentials existed at build time). The OAuth token/API host
values below are Adobe's documented defaults for the NA1 shard -- CONFIRM
these against your actual account during first live run; Acrobat Sign
accounts are sharded (na1/na2/eu1/etc.) and the exact host can differ.
Everything else (request shapes, flow order) follows Acrobat Sign's
documented REST API v6.

Setup
-----
1. In your Acrobat Sign account: Account > Acrobat Sign API > API
   Applications > create an application > Configure OAuth (redirect URI +
   scopes) > note the Client ID and Client Secret.
2. Copy adobe_sign_config.json.example to adobe_sign_config.json and fill
   in client_id / client_secret / redirect_uri.
3. Run:  python adobe_sign.py authorize
   -> open the printed URL in a browser, log in, approve. Adobe redirects
      you to your redirect_uri with ?code=... in the address bar -- copy
      that code value.
4. Run:  python adobe_sign.py exchange <code>
   -> stores a long-lived refresh_token + your account's real API host in
      adobe_sign_config.json. One-time step; access tokens after this
      refresh automatically.

Usage (once configured)
------------------------
  python adobe_sign.py send <pdf_path> <signer_email> <signer_name> <agreement_name>
  python adobe_sign.py status <agreement_id>
  python adobe_sign.py download <agreement_id> <output_path>
"""

import sys
import json
import time
import urllib.parse
from pathlib import Path

try:
    import requests
except ImportError:
    print("This module needs the 'requests' package: pip install requests")
    raise

BASE_DIR    = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "adobe_sign_config.json"

# Adobe's documented default auth/token hosts for accounts that haven't yet
# resolved to a specific shard. CONFIRM against your account -- if these
# don't work, check helpx.adobe.com/sign/developer/integration-key.html or
# your account's "API Information" page for your actual host.
DEFAULT_AUTHORIZE_HOST = "secure.na1.adobesign.com"
DEFAULT_TOKEN_HOST     = "api.na1.adobesign.com"

# Scopes requested during the one-time authorization. Must match (or be a
# subset of) what you enabled when configuring OAuth on the Application.
SCOPES = [
    "agreement_send:account",
    "agreement_read:account",
    "agreement_write:account",
    "webhook_read:account",
    "webhook_write:account",
]


# ─── Config helpers ────────────────────────────────────────────────────────

def _load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"{CONFIG_PATH} not found. Copy adobe_sign_config.json.example "
            f"to adobe_sign_config.json and fill in client_id/client_secret/redirect_uri."
        )
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ─── One-time authorization (run manually, once) ───────────────────────────

def build_authorization_url():
    cfg = _load_config()
    host = cfg.get("authorize_host", DEFAULT_AUTHORIZE_HOST)
    params = {
        "redirect_uri":  cfg["redirect_uri"],
        "response_type": "code",
        "client_id":     cfg["client_id"],
        "scope":         " ".join(SCOPES),
    }
    return f"https://{host}/public/oauth/v2?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(auth_code):
    """
    One-time: trade the authorization code (copied from the browser URL
    bar after approving access) for an access_token + refresh_token.
    Stores both in adobe_sign_config.json, along with the account's real
    api_access_point (Adobe returns this so future calls hit the right
    shard instead of guessing).
    """
    cfg = _load_config()
    host = cfg.get("token_host", DEFAULT_TOKEN_HOST)
    resp = requests.post(
        f"https://{host}/oauth/v2/token",
        data={
            "grant_type":    "authorization_code",
            "code":          auth_code,
            "client_id":     cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uri":  cfg["redirect_uri"],
        },
    )
    resp.raise_for_status()
    data = resp.json()

    cfg["refresh_token"]    = data["refresh_token"]
    cfg["access_token"]     = data.get("access_token")
    cfg["access_token_exp"] = time.time() + data.get("expires_in", 3600) - 60
    if "api_access_point" in data:
        cfg["api_access_point"] = data["api_access_point"].rstrip("/")
    _save_config(cfg)
    return data


# ─── Access token refresh (automatic, called internally) ──────────────────

def _get_access_token():
    cfg = _load_config()
    if cfg.get("access_token") and time.time() < cfg.get("access_token_exp", 0):
        return cfg["access_token"], cfg.get("api_access_point")

    if not cfg.get("refresh_token"):
        raise RuntimeError(
            "No refresh_token stored yet. Run:\n"
            "  python adobe_sign.py authorize\n"
            "then\n"
            "  python adobe_sign.py exchange <code>"
        )

    host = cfg.get("token_host", DEFAULT_TOKEN_HOST)
    resp = requests.post(
        f"https://{host}/oauth/v2/token",
        data={
            "grant_type":    "refresh_token",
            "refresh_token": cfg["refresh_token"],
            "client_id":     cfg["client_id"],
            "client_secret": cfg["client_secret"],
        },
    )
    resp.raise_for_status()
    data = resp.json()

    cfg["access_token"]     = data["access_token"]
    cfg["access_token_exp"] = time.time() + data.get("expires_in", 3600) - 60
    _save_config(cfg)
    return cfg["access_token"], cfg.get("api_access_point")


def _api_base():
    cfg = _load_config()
    point = cfg.get("api_access_point")
    if not point:
        raise RuntimeError(
            "No api_access_point stored yet -- run the authorize/exchange "
            "steps first (it's returned as part of the token exchange)."
        )
    return f"{point}/api/rest/v6"


def _auth_headers():
    token, _ = _get_access_token()
    return {"Authorization": f"Bearer {token}"}


# ─── Sending an agreement ───────────────────────────────────────────────────

def send_agreement_for_signature(pdf_path, signer_email, signer_name, agreement_name):
    """
    Upload a PDF (e.g. the engagement letter, already tagged with
    {{Sig_es_...}} fields) and send it to one signer.
    Returns the new agreement's ID (store this on the assignment record
    so status checks / dashboard tracking know what to poll).
    """
    pdf_path = Path(pdf_path)
    base = _api_base()
    headers = _auth_headers()

    # Step 1: upload as a transient document
    with open(pdf_path, "rb") as f:
        upload_resp = requests.post(
            f"{base}/transientDocuments",
            headers=headers,
            files={"File": (pdf_path.name, f, "application/pdf")},
            data={"File-Name": pdf_path.name, "Mime-Type": "application/pdf"},
        )
    upload_resp.raise_for_status()
    transient_id = upload_resp.json()["transientDocumentId"]

    # Step 2: create the agreement from that document
    payload = {
        "fileInfos": [{"transientDocumentId": transient_id}],
        "name": agreement_name,
        "participantSetsInfo": [
            {
                "role": "SIGNER",
                "order": 1,
                "memberInfos": [{"email": signer_email, "name": signer_name}],
            }
        ],
        "signatureType": "ESIGN",
        "state": "IN_PROCESS",
    }
    create_resp = requests.post(
        f"{base}/agreements",
        headers={**headers, "Content-Type": "application/json"},
        json=payload,
    )
    create_resp.raise_for_status()
    return create_resp.json()["id"]


def get_agreement_status(agreement_id):
    """
    Returns Adobe's status string, e.g. OUT_FOR_SIGNATURE, SIGNED,
    CANCELLED, EXPIRED. 'SIGNED' means fully countersigned and complete.
    """
    base = _api_base()
    resp = requests.get(f"{base}/agreements/{agreement_id}", headers=_auth_headers())
    resp.raise_for_status()
    return resp.json()


def download_signed_document(agreement_id, output_path):
    """Download the final (signed, if complete) combined PDF."""
    base = _api_base()
    resp = requests.get(
        f"{base}/agreements/{agreement_id}/combinedDocument",
        headers=_auth_headers(),
    )
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(resp.content)
    return Path(output_path)


# ─── CLI ────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "authorize":
        print("\nOpen this URL in a browser, log in, and approve access:\n")
        print(build_authorization_url())
        print("\nAdobe will redirect you to your redirect_uri with a "
              "?code=... value in the address bar. Copy just that code, then run:")
        print("  python adobe_sign.py exchange <code>\n")

    elif cmd == "exchange" and len(sys.argv) >= 3:
        data = exchange_code_for_tokens(sys.argv[2])
        print("\nSuccess -- refresh_token and api_access_point saved to "
              f"{CONFIG_PATH.name}.")
        print(f"api_access_point: {data.get('api_access_point', '(not returned -- check config)')}")

    elif cmd == "send" and len(sys.argv) >= 6:
        agreement_id = send_agreement_for_signature(
            sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
        )
        print(f"\nSent. Agreement ID: {agreement_id}")
        print("Save this ID on the assignment record to track status.")

    elif cmd == "status" and len(sys.argv) >= 3:
        info = get_agreement_status(sys.argv[2])
        print(f"\nStatus: {info.get('status')}")
        print(json.dumps(info, indent=2))

    elif cmd == "download" and len(sys.argv) >= 4:
        path = download_signed_document(sys.argv[2], sys.argv[3])
        print(f"\nSaved: {path}")

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
