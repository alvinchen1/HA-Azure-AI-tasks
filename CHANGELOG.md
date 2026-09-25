# Changelog

All notable changes to Azure AI Tasks are recorded here. Versions follow
[semantic versioning](https://semver.org/).

## 2.3.0

### Added

- **Azure AI Foundry (v1) endpoints are now supported.** If your endpoint is an
  Azure AI Foundry resource (`https://YOUR-RESOURCE.services.ai.azure.com`), the
  integration now talks to the newer `/openai/v1/...` API, which no longer needs
  a deployment name in the URL or an `api-version`. Pasting the full
  `.../openai/v1` base works too.
- Existing **Azure OpenAI** endpoints (`https://YOUR-RESOURCE.openai.azure.com`)
  are unchanged and keep working exactly as before - nothing to do if your setup
  works today. The surface is detected from the endpoint you configured; there
  is no new setting.

### Changed

- The endpoint field in setup and reconfigure now says which endpoint styles are
  accepted.

## 2.2.0

- Added a reconfigure flow so the endpoint and API key can be changed in place
  without removing and re-adding the integration.

## 2.1.0

- GPT-5 (reasoning) models now work: a newer API version is used and the
  completion-token budget was given headroom so replies are not empty.

## 2.0.0

- Multiple config entries, separate chat and image models, and image generation
  support. See the GitHub releases for the full history of 1.x and 2.0.x.
