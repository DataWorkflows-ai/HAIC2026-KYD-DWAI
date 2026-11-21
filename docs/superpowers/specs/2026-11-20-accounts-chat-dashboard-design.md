# Accounts, chat workspace and dashboard: design (2026-11-20)

Requested by Mitchell at 15:34. He chose these answers: live tonight as the default UI; login and chat first.
Items marked *(decided while Mitchell was away)* are defaults he has not yet reviewed.

## 1. Accounts and sign-in

- **Sign-in is required** for every page and API call except `/api/health` and `/api/auth/*`.
  - The setting is `KYD_AUTH_REQUIRED`, on by default.
  - Tests turn it off in `conftest.py`, except the auth tests themselves.
- **Self-registration** takes email, name and password, and grants access immediately as `user`.
- **Roles:**
  - `owner` (one): changes anyone's role (user or admin) and can disable or re-enable accounts.
  - `admin`: sees the usage page.
  - `user`: everything else.
- **Who becomes owner:** the account whose email equals `KYD_OWNER_EMAIL`. If that is unset, the first account
  registered becomes owner *(decided while Mitchell was away)*.
- **Storage:** new `app` schema in Supabase (`kyd/db/app.sql`, idempotent, never dropped).
  - `kyd_app` gets SELECT, INSERT and UPDATE on `app.*` only; it still cannot touch `kyd.*` or the audit log.
  - Bundled and CI mode use `backend/var/app.sqlite`, with the same tables.
- **Passwords:**
  - Hashed with scrypt (Python standard library, n=2^14, r=8, p=1, 16-byte salt); minimum 8 characters.
  - Sign-in and registration are limited to 30 attempts a minute per client (a venue's Wi-Fi counts as one).
- **Tokens:**
  - The existing HMAC bearer tokens, valid for 7 days, stored in `localStorage`.
  - Each request re-reads the account (30 s cache), so a role change or a disable takes effect without signing in again.
- **Signing secret:** `KYD_AUTH_SECRET`. If it is unset, the server generates a random one at start-up.
  Sign-ins then end on every redeploy, and `/api/health` reports `auth.secret: "ephemeral"`.
- **Audit:** the actor is the account id (`u:…`), not the email. The usage page maps ids to emails for admins.
- **Not included:** email verification and password reset (no email service), and SSO.

## 2. Chat workspace (Claude desktop style)

- **Three columns:**
  - Left, collapsible: chat history.
  - Middle: the conversation.
  - Right, collapsible: the document panel.
  - On phones the side columns become slide-over panels.
- **History** is saved per account on the server (`app.chats`, `app.messages`).
  - The title is the first question, which can be renamed.
  - Chats can be pinned, archived (with a "Show archived" view) and unarchived, and searched by title and
    message text. There is no delete, as Mitchell chose.
- **Follow-ups:** the last 3 turns go to System 2 as context. System 1 routing is unchanged.
- **Documents:**
  - When the user asks for something long-form (memo, brief, letter, talking points, report…), System 2 replies
    with a short summary plus `<document title="…">markdown</document>`.
  - The server extracts the document and runs the same figure check on it as on the answer.
  - Any answer can also be opened in the panel ("Open as document").
  - Documents are shown as safe Markdown (react-markdown, no raw HTML; only http and https links are clickable).
  - They can be copied, printed or saved as PDF, and downloaded as Markdown.

## 3. Dashboard

- A new **Dashboard** tab, the landing page after sign-in. Overview is unchanged.
- **Widgets** use the Mission Control pattern:
  - Edit-layout mode: drag by the title bar, resize from the corner, hide, add from the catalog.
  - Reset to a preset.
  - The layout is saved per account on the server (`app.dashboards`).
  - On narrow screens widgets stack in one column.
- **Presets:** Constituent services; Budget and finance; Health and human services.
- **Per-widget settings:** district, indicator, chamber.
- **"Pin to dashboard"** on any figure (KPI widget) and on any chat answer (pinned-answer widget).
- **Catalog**, all built on data already in KYD:
  - District snapshot, single figure, where we rank, SNAP gap range and peers, and top programs.
  - Mini map (ranking map).
  - Trends: unemployment 2014–2025, crime (Oʻahu estimate), births and deaths.
  - Schools: meals and test scores; housing: HUD and rent burden.
  - Who represents it.
  - Quick ask, and recent and pinned chats.
  - Holidays: federal and Hawaiʻi.
  - Calendar: month view with holidays and the user's own entries.
  - Notes and to-dos.
  - Usage (admins only).
- **Deferred, needing new data or integrations:**
  - Homeless counts: Partners in Care / Bridging the Gap PIT data is not loaded.
  - Test results by school and grade (only district rollups are loaded).
  - Legislative bills with updates: capitol.hawaii.gov is not integrated.
  - Connecting an external calendar: Google or Outlook OAuth.

## Testing

- **Backend:**
  - Registration, login, wrong password, disabled account, ownership rules, and role-change effects.
  - Chats: CRUD, ownership isolation, search, pin and archive.
  - Dashboard save and load, the auth-required gate, and document extraction plus redaction.
- **Both backends:** the backend tests run against Postgres in CI too (the whole suite already runs there).
- **Browser checks:** sign-in, register, chat with history, documents, dashboard edit, and phone size.
