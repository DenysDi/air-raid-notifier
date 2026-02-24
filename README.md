# Air Raid Notifier

Monitors [alerts.in.ua](https://alerts.in.ua) for air-raid alerts in a configured Ukrainian region and automatically changes your work-messenger status.

When an alert starts → status switches to **Air Raid 🚀**
When the alert ends  → status reverts to whatever it was before.

Supported messengers:
- **Slack** – changes user status text & emoji
- **Microsoft Teams** – changes user presence (Available → DoNotDisturb)

Designed to run as a background service on a home Ubuntu server.

---

## Requirements

| Requirement | Version |
|---|---|
| Python | 3.9 or newer |
| Ubuntu / Debian | Any recent release |

---

## Quick start

```bash
# 1. Clone your repo
git clone https://github.com/<you>/air-raid-notifier.git
cd air-raid-notifier

# 2. Run the installer
chmod +x install.sh
./install.sh

# 3. Edit config
nano config.yaml

# 4. Start
systemctl --user start air-raid-notifier

# 5. Enable on boot
systemctl --user enable air-raid-notifier
```

---

## Configuration

`config.yaml` (created from the example on first install):

```yaml
log_level: INFO          # DEBUG | INFO | WARNING | ERROR

alerts:
  token: "YOUR_TOKEN"   # from https://devs.alerts.in.ua/
  region_uid: 31        # 31 = Kyiv city; see full list below
  poll_interval_seconds: 30
  alert_on_partial: true

messengers:
  slack:
    enabled: true
    token: "xoxp-..."
    alert_text:  "Air Raid 🚀"
    alert_emoji: ":rotating_light:"

  teams:
    enabled: false
    tenant_id:     "..."
    client_id:     "..."
    client_secret: "..."
    user_id:       "..."
    alert_presence: "DoNotDisturb"
    alert_text:    "Air Raid 🚀"
```

### Region UIDs

| UID | Region |
|-----|--------|
| 4  | Вінницька область |
| 5  | Волинська область |
| 6  | Дніпропетровська область |
| 7  | Донецька область |
| 8  | Житомирська область |
| 9  | Закарпатська область |
| 10 | Запорізька область |
| 11 | Івано-Франківська область |
| 12 | Київська область |
| 13 | Кіровоградська область |
| 14 | Луганська область |
| 15 | Львівська область |
| 16 | Миколаївська область |
| 17 | Одеська область |
| 18 | Полтавська область |
| 19 | Рівненська область |
| 20 | Сумська область |
| 21 | Тернопільська область |
| 22 | Харківська область |
| 23 | Херсонська область |
| 24 | Хмельницька область |
| 25 | Черкаська область |
| 26 | Чернівецька область |
| 27 | Чернігівська область |
| 31 | м. Київ |

---

## Messenger setup

### Slack

1. Go to <https://api.slack.com/apps> → **Create New App** → **From scratch**.
2. Name it (e.g. "Air Raid Notifier"), pick your workspace.
3. Go to **OAuth & Permissions** → scroll to **User Token Scopes** → add:
   - `users.profile:read`
   - `users.profile:write`
4. Click **Install to Workspace** and authorise.
5. Copy the **User OAuth Token** (starts with `xoxp-`).
6. Paste it into `config.yaml` under `messengers.slack.token`.

### Microsoft Teams

Teams uses the Microsoft Graph API with application permissions (no interactive login needed after setup).

**Step 1 – Register an Azure AD app**

1. Sign in to <https://portal.azure.com>.
2. Go to **Azure Active Directory** → **App registrations** → **New registration**.
   - Name: `Air Raid Notifier`
   - Supported account types: *Accounts in this organizational directory only*
   - Redirect URI: leave empty
3. After creation note the **Application (client) ID** and **Directory (tenant) ID**.

**Step 2 – Add a client secret**

1. Go to **Certificates & secrets** → **New client secret**.
2. Set a description and expiry, click **Add**.
3. **Copy the VALUE immediately** – it is only shown once.

**Step 3 – Add API permissions**

1. Go to **API permissions** → **Add a permission** → **Microsoft Graph** → **Application permissions**.
2. Search for and add: `Presence.ReadWrite.All`
3. Click **Grant admin consent for \<tenant\>** (requires Global Admin).

**Step 4 – Find your user Object ID**

1. **Azure Active Directory** → **Users** → find your account.
2. Copy the **Object ID** (a GUID).

**Step 5 – Fill in config.yaml**

```yaml
teams:
  enabled: true
  tenant_id:     "<Directory (tenant) ID>"
  client_id:     "<Application (client) ID>"
  client_secret: "<secret value>"
  user_id:       "<your Object ID>"
  alert_presence: "DoNotDisturb"
```

---

## Service management

```bash
# Start / stop / restart
systemctl --user start   air-raid-notifier
systemctl --user stop    air-raid-notifier
systemctl --user restart air-raid-notifier

# Enable / disable auto-start on boot
systemctl --user enable  air-raid-notifier
systemctl --user disable air-raid-notifier

# Live logs
journalctl --user -u air-raid-notifier -f

# Status
systemctl --user status air-raid-notifier
```

---

## Adding a new messenger

1. Create `src/messengers/yourapp.py` that inherits from `BaseMessenger` and implements `get_status()` and `set_status()`.
2. Register it in `src/messengers/__init__.py`:
   ```python
   from .yourapp import YourAppMessenger
   _REGISTRY = {
       ...
       "yourapp": YourAppMessenger,
   }
   ```
3. Add the corresponding block to `config.yaml.example`.

---

## Uninstall

```bash
chmod +x uninstall.sh
./uninstall.sh
```

This removes the systemd service but leaves `config.yaml` and `venv/` intact.

---

## Alerts API token

Request a token at <https://alerts.in.ua> (fill the developer form on that page).
The API is free for personal / non-commercial use.

---

## License

MIT
