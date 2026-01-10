#!/usr/bin/env python3
"""
Send a real WhatsApp test message via Twilio using .env credentials.
Requires: requests, python-dotenv
"""

import os
import json
from datetime import datetime

import requests
from dotenv import load_dotenv


def main():
    # Explicitly load .env from current directory
    from pathlib import Path
    env_path = Path('.') / '.env'
    loaded = load_dotenv(dotenv_path=str(env_path), override=True)
    print(f".env loaded: {loaded} from {env_path.resolve()}")

    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_number = os.getenv('TWILIO_WHATSAPP_FROM')
    to_numbers = os.getenv('TWILIO_WHATSAPP_TO', '').split(',')
    content_sid = os.getenv('TWILIO_CONTENT_SID')

    # Fallback: parse .env directly if env vars look like placeholders
    def looks_placeholder(v: str) -> bool:
        return (not v) or ('xxxx' in v.lower()) or ('seu_numero' in v.lower())

    if looks_placeholder(account_sid) or looks_placeholder(auth_token) or looks_placeholder(content_sid):
        print("Using direct .env file parsing fallback...")
        env = {}
        try:
            with open('.env', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        k, v = line.split('=', 1)
                        env[k.strip()] = v.strip()
            account_sid = env.get('TWILIO_ACCOUNT_SID', account_sid)
            auth_token = env.get('TWILIO_AUTH_TOKEN', auth_token)
            from_number = env.get('TWILIO_WHATSAPP_FROM', from_number)
            to_numbers = env.get('TWILIO_WHATSAPP_TO', os.getenv('TWILIO_WHATSAPP_TO', '')).split(',')
            content_sid = env.get('TWILIO_CONTENT_SID', content_sid)
        except Exception as e:
            print(f"Failed to parse .env directly: {e}")

    # Basic validations
    missing = []
    for key, val in {
        'TWILIO_ACCOUNT_SID': account_sid,
        'TWILIO_AUTH_TOKEN': auth_token,
        'TWILIO_WHATSAPP_FROM': from_number,
        'TWILIO_WHATSAPP_TO': os.getenv('TWILIO_WHATSAPP_TO'),
        'TWILIO_CONTENT_SID': content_sid,
    }.items():
        if looks_placeholder(str(val)):
            missing.append(key)

    if missing:
        print(f"❌ Missing or placeholder env vars: {', '.join(missing)}")
        # Debug dump of loaded values (masked)
        def mask(v):
            if not v:
                return 'None'
            return v[:4] + '...' + v[-4:]
        print("Debug env:")
        print(f"  SID={mask(account_sid)}")
        print(f"  TOKEN={mask(auth_token)}")
        print(f"  FROM={from_number}")
        print(f"  TO={os.getenv('TWILIO_WHATSAPP_TO')}")
        print(f"  CONTENT_SID={mask(content_sid)}")
        return 1

    # Build ContentVariables test payload
    now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    content_vars = {
        "1": "TESTE-OS",
        "2": now,
        "3": "Sistema",
        "4": "TI",
        "5": "Servidor",
        "6": "Alta",
        "7": "Mensagem de teste de notificação via Twilio",
        "8": "Envio automatizado"
    }

    errors = 0
    for raw_to in to_numbers:
        to = raw_to.strip()
        if not to:
            continue

        data = {
            'To': to,
            'From': from_number,
            'ContentSid': content_sid,
            'ContentVariables': json.dumps(content_vars, ensure_ascii=False),
        }

        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        print(f"→ Sending to {to} ...")
        try:
            resp = requests.post(url, data=data, auth=(account_sid, auth_token), timeout=15)
            print(f"  Status: {resp.status_code}")
            if resp.status_code in (200, 201):
                body = resp.json()
                print(f"  ✓ Sent. SID: {body.get('sid')}, Status: {body.get('status')}")
            else:
                print(f"  ✗ Error: {resp.text[:200]}")
                errors += 1
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            errors += 1

    if errors:
        print(f"❌ Completed with {errors} error(s)")
        return 1

    print("✅ All messages queued successfully")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
