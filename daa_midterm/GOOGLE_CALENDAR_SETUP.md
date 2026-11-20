# DAA Midterm — Google Calendar setup

Google requires an OAuth client created by the app owner, so a one-time setup is needed. The `.ics` export works without it.

## 1. Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

## 2. Create OAuth credentials

1. Open <https://console.cloud.google.com/> and create or select a project.
2. Go to **APIs & Services → Library**, find **Google Calendar API** and enable it.
3. Configure the **OAuth consent screen**. While the app is in testing, add your Google account as a **test user**.
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
5. Choose **Web application**.
6. Under **Authorized redirect URIs**, add exactly `http://localhost:8501`.
7. Copy the **Client ID** and **Client secret**.

## 3. Add the credentials

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill it in:

```toml
[google_calendar]
client_id = "PASTE_YOUR_CLIENT_ID"
client_secret = "PASTE_YOUR_CLIENT_SECRET"
redirect_uri = "http://localhost:8501"
```

Never upload `secrets.toml` to GitHub or share it.

## 4. Restart and connect

```bash
python3 -m streamlit run app.py
```

Open the **Google Calendar** tab, click **Connect Google Calendar**, sign in with the test-user account and approve access.

## Notes

- Events are created in the connected account's **primary** calendar on the date chosen in DAA Midterm.
- Syncing is safe to repeat: each meeting has a fixed event ID per date, so it is never duplicated.
- Attendees are **not** emailed unless you tick **Email invitations to attendees** before syncing.
- DAA Midterm only requests permission to manage calendar events — not Gmail or Drive.
- The sign-in token lives in the Streamlit session, so you reconnect after restarting the app.
- The sign-in must be started and finished while the app is running at the registered redirect URI (within 10 minutes).
- A deployed public version needs HTTPS and its own registered redirect URI.
- Google may show an "unverified app" warning in testing mode; this is expected for personal projects.
