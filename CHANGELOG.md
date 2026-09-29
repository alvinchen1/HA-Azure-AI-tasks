# Changelog

All notable changes to Azure AI Tasks are recorded here. Versions follow
[semantic versioning](https://semver.org/).

## 2.5.1

### Fixed

- Fixed setup and configuration forms failing to load in Home Assistant. The
  custom GPT-image-2 dimension validator could not be serialized for the
  frontend; dimensions are now validated after submission while the form schema
  remains frontend-compatible.

## 2.5.0

### Added

- GPT-image-2 supports configurable custom image dimensions, validated against
  the model's divisibility, aspect-ratio, and maximum-dimension requirements.

## 2.4.0

### Changed

- **A failed update of your saved configuration now tells you what to do about
  it.** Previously the update step always reported success, so a genuinely
  broken entry looked fine and simply failed later. Now:
  - a temporary problem (for example a storage error) is retried by Home
    Assistant on its own - nothing for you to do;
  - a real problem raises a **Repair** in Settings → System → Repairs. Fix the
    entry (usually by reconfiguring the endpoint and API key) and click **Fix**
    to retry the update, without restarting Home Assistant.
- Downgrading Azure AI Tasks to an older version than the one that wrote your
  configuration now says so clearly instead of failing obscurely.
- Running on a Home Assistant older than 2025.10.0 now stops setup with a clear
  message. It previously only logged a warning and carried on, which meant the
  integration failed later for no visible reason.

On Home Assistant versions that cannot retry a migration in place, the Repair
tells you to reconfigure and restart instead of offering a Fix button that
would not work.

Existing working setups are unaffected: a healthy entry migrates exactly as it
did before.

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
