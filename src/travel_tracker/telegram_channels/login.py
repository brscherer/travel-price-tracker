"""One-time interactive login to create a Telethon session file.

Run manually, not from cron/CI (it needs your phone and the login code
Telegram sends you):

    python -m travel_tracker.telegram_channels.login

Needs TELEGRAM_API_ID and TELEGRAM_API_HASH in .env, from my.telegram.org
("API development tools" -> create an app). On success this writes a
<session_name>.session file in the current directory -- keep it private,
it's equivalent to being logged into your Telegram account. Add
`*.session` to .gitignore (already there) and never commit it.
"""

from __future__ import annotations

import sys

from ..config import load_secrets


def main() -> None:
    try:
        from telethon.sync import TelegramClient
    except ImportError:
        print("telethon not installed. Run: pip install -e '.[telegram]'")
        sys.exit(1)

    secrets = load_secrets()
    if not secrets.telegram_api_id or not secrets.telegram_api_hash:
        print("Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env first (from my.telegram.org).")
        sys.exit(1)

    session_name = "travel_tracker"
    with TelegramClient(session_name, int(secrets.telegram_api_id), secrets.telegram_api_hash) as client:
        me = client.get_me()
        print(f"Logged in as {me.first_name} ({me.phone}). Session saved as {session_name}.session")
        print("Set promos.telegram_channels.enabled: true and list channels in config.yaml to use it.")


if __name__ == "__main__":
    main()
