# Security Policy

## API And Privacy Rules

API / Token / Secret / Credential are sensitive private information in this repository.

API 是隐私内容，务必不能泄漏。

Never commit any real API key, token, secret, credential, certificate, or private key to this public repository.

Code can be public. Credentials must stay local.

## Local Secret Handling

Use [`.env.example`](.env.example) only as a template.

1. Copy [`.env.example`](.env.example) to `.env`.
2. Fill in your own local values.
3. Export the variables from `.env` into your shell before running live integrations.

Example:

```bash
cp .env.example .env
set -a
source .env
set +a
```

The repository does not commit `.env`, and [`.gitignore`](.gitignore) blocks the most common local secret files:

- `.env`
- `.env.*`
- `!.env.example`
- `secrets/`
- `*.pem`
- `*.key`

These rules reduce the risk of accidentally committing local credentials, certificate material, or ad-hoc secret folders.

## Supported Environment Variables

Sensitive values must be provided through environment variables only. Do not hardcode them in Python, YAML, JSON, prompts, scripts, or test fixtures.

Current and reserved examples include:

- `GITHUB_TOKEN`
- `PRODUCT_HUNT_TOKEN`
- `APO_LLM_RELAY_TOKEN`
- `OPENAI_API_KEY`
- `SCRAPER_API_KEY`

Non-secret live configuration such as `APO_LLM_RELAY_BASE_URL` and `APO_LLM_RELAY_MODEL` may also live in `.env`, but any credential-bearing value must remain local-only.

## Defensive Defaults In Code

The shared config helpers under `src/common/config.py` are the approved place for required environment-variable reads.

- Missing required variables fail with a setup error that points developers to `.env.example` and `.env`.
- Secret-like variables are redacted in helper summaries and must not be logged in full.
- New API integrations must read credentials from environment variables instead of hardcoded strings.

## If Something Is Accidentally Committed

If a local `.env` file is accidentally tracked:

```bash
git rm --cached .env
```

Then rotate the affected secrets if any real values were exposed in a commit, branch, pull request, CI log, screenshot, or pasted terminal output.

## If A Secret Leaks

1. Revoke the exposed key or token immediately.
2. Issue a replacement credential.
3. Update your local `.env`.
4. Check Git history, pull requests, CI logs, and external paste targets for secondary exposure.

Do not treat secret rotation as optional. Once a real key is exposed, assume it is compromised.
