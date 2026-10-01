# Azure AI Tasks - Home Assistant Integration

[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5?style=flat-square)](https://github.com/hacs/integration)
[![Release](https://img.shields.io/github/v/release/alvinchen1/HA-Azure-AI-tasks?style=flat-square)](https://github.com/alvinchen1/HA-Azure-AI-tasks/releases)
[![Release date](https://img.shields.io/github/release-date/alvinchen1/HA-Azure-AI-tasks?style=flat-square)](https://github.com/alvinchen1/HA-Azure-AI-tasks/releases)
[![Downloads](https://img.shields.io/github/downloads/alvinchen1/HA-Azure-AI-tasks/total?style=flat-square)](https://github.com/alvinchen1/HA-Azure-AI-tasks/releases)
[![License](https://img.shields.io/github/license/alvinchen1/HA-Azure-AI-tasks?style=flat-square)](LICENSE)
[![Last commit](https://img.shields.io/github/last-commit/alvinchen1/HA-Azure-AI-tasks?style=flat-square)](https://github.com/alvinchen1/HA-Azure-AI-tasks/commits)
[![Stars](https://img.shields.io/github/stars/alvinchen1/HA-Azure-AI-tasks?style=flat-square)](https://github.com/alvinchen1/HA-Azure-AI-tasks/stargazers)

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=alvinchen1&repository=HA-Azure-AI-tasks&category=integration)

A Home Assistant custom integration that facilitates AI tasks using Azure AI services.

<p align="center"><img width="256" height="256" alt="icon" src="https://github.com/user-attachments/assets/934b88ed-f038-474f-9211-4417717e5e84" /><p>

## Features

- Easy configuration through Home Assistant UI
- Secure API key management  
- **User-configurable AI models for chat responses** (GPT-3.5, GPT-4, GPT-4o, etc.) - type in any model name
- **🎨 Image generation with DALL-E support** - generate images from text prompts using DALL-E 2/3
- **Image and video analysis with attachment support** - analyze camera streams and uploaded images
- **Flexible entity configuration** - create chat-only, image-only, or combined entities
- **Reconfiguration support** - change models without re-entering credentials
- **Multiple entry support** - use different API endpoints and keys for different purposes
- Compatible with Azure OpenAI and other Azure AI services
- HACS ready for easy installation

## Installation

### Via HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the three dots menu and select "Custom repositories"
4. Add `https://github.com/alvinchen1/HA-Azure-AI-Tasks` as repository
5. Set category to "Integration"
6. Click "Add"
7. Find "Azure AI Tasks" in the integration list and install it
8. Restart Home Assistant
9. Go to Configuration > Integrations
10. Click "+ Add Integration" and search for "Azure AI Tasks"
11. Press Submit to complete the installation.

Or replace steps 1-6 with this:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=alvinchen1&repository=HA-Azure-AI-Tasks&category=integration)

### Manual Installation

1. Copy the `custom_components/azure_ai_tasks` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Add the integration through the UI (Settings → Devices & Services → Add Integration)

## Configuration

1. Go to Settings → Devices & Services → Add Integration
2. Search for "Azure AI Tasks"
3. Enter your Azure AI endpoint URL. Both Azure surfaces are supported and the right one is detected automatically:
   - **Azure OpenAI (classic)** - `https://YOUR-RESOURCE.openai.azure.com`
   - **Azure AI Foundry (v1)** - `https://YOUR-RESOURCE.services.ai.azure.com`

   Just the resource URL is enough; if you paste the full `.../openai/v1` base that works too.
4. Enter your API key
5. **Enter your preferred chat model** (gpt-35-turbo, gpt-4, gpt-4o, etc.) - leave empty for image-only entities
6. **Enter your preferred image model** (dall-e-2, dall-e-3, etc.) - leave empty for chat-only entities  
7. Give your integration a name
8. Click Submit

<img width="383" height="478" alt="image" src="https://github.com/user-attachments/assets/8932c51a-8fcb-42bc-9e22-ead143c610d7" />

### Reconfiguration

To change AI models without re-entering credentials:
1. Go to your Azure AI Tasks integration
2. Click "Configure" 
3. Enter different chat/image models as needed (use placeholder text `[None - leave empty to disable chat]` or `[None - leave empty to disable images]` to clear fields)
4. Save changes

**Note**: You can create specialized entities by leaving one model type empty:
- **Chat-only entities**: Configure chat model, leave image model empty
- **Image-only entities**: Configure image model, leave chat model empty  
- **Combined entities**: Configure both models

<img width="1072" height="700" alt="image" src="https://github.com/user-attachments/assets/598b8c28-7663-4507-be63-22413cac4b9d" />

## Usage

Once configured, the integration provides an AI Task entity that can be used in automations and scripts to process AI tasks using your Azure AI service.

### Chat/Text Generation
Example service call for generating text responses:
```yaml
service: ai_task.process
target:
  entity_id: ai_task.azure_ai_tasks
data:
  task: "Summarize the weather forecast for today"
```
![HA Azure AI Task example](https://github.com/user-attachments/assets/592ec039-20ea-436f-a6f0-caf88bef9b56)

### 🎨 Image Generation
Example service calls for generating images:

**Basic Image Generation:**
```yaml
action: ai_task.generate_image
data:
  task_name: smart home image
  instructions: "A futuristic smart home with holographic displays and AI assistants"
  entity_id: ai_task.azure_ai_tasks
```
<img width="1413" height="1164" alt="image" src="https://github.com/user-attachments/assets/b1d7c898-bb54-4398-838f-838f4a5e26fa" />
<img width="1360" height="1246" alt="Generated AI image of a futuristic smart home with holographic displays and AI assistants" src="https://github.com/user-attachments/assets/f748fffd-a379-4745-845f-1fecdff31e44" />

**GPT-image-2** uses Azure's `1024x1024` default. The integration does not
expose an image-size configuration field. The standard Home Assistant
`ai_task.generate_image` action rejects an extra `size` field before the
integration receives the request, so custom dimensions cannot currently be
selected through that action. Do not add `size` to the action data; it will
fail validation in Home Assistant. Calls through the action use the default
`1024x1024`.

GPT-image-2 dimensions must be multiples of 16, have an aspect ratio between
1:3 and 3:1 (inclusive), be no longer than 3840 pixels on either side, and
contain between 655,360 and 8,294,400 total pixels. The smallest allowed total
is 655,360 pixels; `640x1024` is one valid size at that limit. Other valid
examples are `800x832`, `1024x1024`, `1200×1600`, and `3840x1280`. When a size
reaches the entity, its validator accepts ASCII `x` or the Unicode
multiplication sign `×`; this does not make `size` an accepted field of the
standard Home Assistant action.
`800x480` is too small. The integration's validation reports which constraint
an invalid size violates when a size value reaches the entity; it cannot
validate `size` from the standard action because Home Assistant rejects it
first. Other image models retain their existing request sizes.

### Image/Video Analysis with Attachments
Example service calls for analyzing images or camera streams:

**Analyze Camera Stream:**
```yaml
action: ai_task.generate_data
data:
  task_name: camera analysis
  instructions: What's going on in this picture?
  entity_id: ai_task.azure_ai_tasks
  attachments:
    media_content_id: media-source://camera/camera.front_door_fluent
    media_content_type: application/vnd.apple.mpegurl
    metadata:
      title: Front door camera
      media_class: video
```
<img width="1390" height="1247" alt="image" src="https://github.com/user-attachments/assets/c475523b-37af-4e76-9336-bc148c5a1a5d" />
<br><br>

**Analyze Uploaded Image:**
```yaml
action: ai_task.generate_data
data:
  task_name: image analysis
  instructions: Describe what you see in this image
  entity_id: ai_task.azure_ai_tasks
  attachments:
    media_content_id: media-source://media_source/local/my_image.jpeg
    media_content_type: image/jpeg
    metadata:
      title: My uploaded image
      media_class: image
```
<img width="1372" height="1222" alt="image" src="https://github.com/user-attachments/assets/28e81122-463d-4d37-8df9-1a7c0d902f86" />

### Available Models

**Chat Models**: You can enter any chat model name that your Azure AI deployment supports:
- gpt-35-turbo, gpt-4, gpt-4o, gpt-4-turbo, gpt-5, gpt-5-mini, etc.
- **Note**: GPT-5 models (including gpt-5-mini) are fully supported and use the max_completion_tokens parameter automatically

**Image Models**: Supported image generation models:
- **dall-e-2**: Classic DALL-E image generation
- **dall-e-3**: DALL-E image generation
- **gpt-image-2**: GPT image generation using Azure's default `1024x1024` size

## Requirements

- **Home Assistant 2025.10.0 or later** (required for AI Task and AI Image services)
- Azure AI service with API access - either an **Azure OpenAI** resource (`*.openai.azure.com`) or an **Azure AI Foundry** resource (`*.services.ai.azure.com`)
- Valid Azure AI endpoint and API key

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Development Approach
<img width="256" height="256" alt="Vibe Coding with GitHub Copilot 256x256" src="https://github.com/user-attachments/assets/bb41d075-6b3e-4f2b-a88e-94b2022b5d4f" />

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues, please report them on the [GitHub Issues page](https://github.com/alvinchen1/HA-Azure-AI-tasks/issues).
