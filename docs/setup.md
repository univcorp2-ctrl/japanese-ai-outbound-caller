# Initial setup

## Local dry run — no external account required

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
ruff check .
pytest
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs`. Keep `DRY_RUN=true`; requests are validated and recorded but no
phone call is made.

```bash
curl -X POST http://localhost:8000/v1/calls \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: replace-with-a-long-random-value' \
  -d '{"phone_number":"+819012345678","recipient_name":"山田太郎", \
       "purpose":"依頼されたデモの日程確認","consent_basis":"requested_callback"}'
```

## Real outbound calling

Production requires LiveKit, a SIP carrier, verified caller ID, outbound trunk, model credentials,
strong application secrets, a human transfer route, monitoring, privacy notice, retention rules,
and legal/carrier review. Fill `.env`, install voice extras, and start both processes:

```bash
pip install -e ".[voice]"
DRY_RUN=false uvicorn app.main:app --host 0.0.0.0 --port 8000
python -m agent.worker dev
```

Alternatively run `docker compose up --build`.

## Notion publishing

Create a Notion internal integration, grant access to the destination parent page, and add GitHub
Actions secrets `NOTION_TOKEN` and `NOTION_PARENT_PAGE_ID`. Run **Actions → Publish research to
Notion → Run workflow**. It publishes `notion/AI音声電話サービス調査.md` with Notion API version
`2026-03-11`.

## Production validation

Test noisy phone audio, numbers/dates/names, interruptions, silence, voicemail, transfer, opt-out
phrases, API failures, carrier rate limits, monitoring and incident rollback before enabling traffic.
