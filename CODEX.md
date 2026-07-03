# CODEX.md

## Repository intent

Build and maintain a consent-first Japanese outbound voice agent. Never add features whose
primary purpose is unsolicited bulk calling, caller-ID spoofing, evading opt-outs, or bypassing
carrier/legal controls.

## Engineering rules

- Keep `DRY_RUN=true` as the safe default.
- Every real call must carry a documented consent basis.
- Preserve suppression-list, business-hour, daily-limit, and cooldown checks.
- Never persist full phone numbers in SQLite; store a salted hash and masked value only.
- Add tests for policy changes and run `ruff check . && pytest` before merging.
- Secrets belong in environment variables or GitHub Actions secrets, never in commits.
- Update `docs/research.md` with dated primary sources when changing vendors or models.

## Production definition of done

A production deployment requires a configured SIP carrier/trunk, LiveKit credentials, OpenAI or
another voice-model credential, a verified caller ID, monitoring, human escalation, privacy notice,
retention policy, and legal review for the intended campaign.
