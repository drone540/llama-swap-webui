# llama-swap WebUI

A lightweight, self-contained web interface for llama-swap, providing a single UI for interacting with text, vision, image, audio, embedding, and reranking models.

The UI is contained entirely in a single `index.html` file. No frontend build system or Node.js installation is required.

A small optional Python server, `serve.py`, is included to work around CORS limitations of llama-swap's native API endpoints. It serves the WebUI and proxies llama-swap through the same origin, allowing the System, Profiles, Metrics, Logs, and other native endpoints to work correctly from a browser.

## Features

### Chat

-   OpenAI-compatible chat interface
-   Streaming responses
-   OpenAI Chat API mode
-   OpenAI Responses API mode
-   Anthropic API mode
-   Model selection with searchable model lists
-   Temperature and maximum-token controls
-   Reasoning/thinking controls
-   Vision/image attachments
-   Conversation history
-   Chat search
-   Chat folders
-   Folder-specific system prompts
-   Rename, move, delete, and organize conversations
-   Regenerate/edit responses with branching support
-   Markdown rendering
-   Syntax highlighting
-   Copy buttons for code blocks
-   Export conversations to Markdown
-   Export conversations to standalone HTML

### Completions

Supports traditional text completion and infill-style requests.

-   `/v1/completions`
-   `/infill`
-   Configurable temperature
-   Configurable maximum tokens
-   Prefix/suffix editing for infill

### Image Generation

Provides a convenient UI for image generation and image-to-image editing.

-   Text-to-image
-   Image-to-image / image editing
-   Multiple resolution presets
-   Custom image dimensions
-   Seed control
-   Randomize/recycle seeds
-   Steps
-   CFG
-   LoRA selection
-   LoRA refresh
-   Image preview

### Speech

Text-to-speech support through llama-swap.

-   Select TTS model
-   Reload available voices
-   MP3, WAV, Opus, and FLAC output
-   Adjustable speech speed
-   Voice selection
-   Weighted voice mixing for supported models

### Transcription

Speech-to-text functionality with:

-   Model selection
-   Optional language selection
-   Audio file upload
-   Transcription output

### Embeddings

Generate embeddings using an embedding-capable model through the llama-swap API.

### Reranking

Run document reranking against a query.

-   Select a reranker model
-   Enter a query
-   Provide multiple documents
-   View ranked results

### System Management

The System tab provides visibility into the llama-swap server itself.

-   Health status
-   Running models
-   Unload all models
-   Profiles
-   Activate profiles
-   Metrics
-   Live logs
-   General logs
-   Proxy logs
-   Upstream logs
-   Per-model log streams

### ComfyUI

The WebUI can embed a ComfyUI instance exposed through llama-swap's `/comfyui/` endpoint.

This requires llama-swap to be configured with an appropriate `comfyui_auto` model.

### MCP Tool Support

The chat interface includes optional client-side MCP-style tool handling.

The current UI includes mock `web_search` and `web_fetch` tools which can be supplied to compatible models. Tool calls are executed client-side and results can be fed back to the model for multiple rounds.

## How It Works

There are two ways to use the WebUI.

### Option 1 — Open `index.html` directly

The frontend is completely self-contained, so you can simply open:

    index.html
    

in a browser.

The UI communicates directly with the llama-swap API using the API Base URL configured in Settings.

The OpenAI-compatible `/v1/*` endpoints generally work cross-origin, but llama-swap's native management endpoints do not currently provide the CORS headers required by browsers.

This means some functionality may be unavailable when the page is opened directly or hosted on a different origin.

In particular, native endpoints such as:

    /health
    /running
    /profiles
    /metrics
    /logs
    

can be blocked by the browser's CORS policy.

The WebUI detects this situation and displays a CORS warning.

### Option 2 — Use `serve.py` (recommended)

`serve.py` solves the CORS problem by doing two jobs:

1.  Serving the WebUI files.
2.  Proxying llama-swap API requests through the same origin.

Instead of:

    Browser
       │
       ├── WebUI ───────────────► localhost:8000
       │
       └── API ─────────────────► 192.168.x.x:8080
                                    ↑
                                 CORS
    

the browser communicates with the Python server:

    Browser
       │
       ▼
    serve.py :8000
       │
       ├── index.html
       │
       └── API proxy
              │
              ▼
          llama-swap :8080
    

Because the browser sees everything as coming from the same origin, the native llama-swap endpoints can be accessed without CORS restrictions.

`serve.py` also preserves streaming responses, including Server-Sent Events used by live logs and streaming generation.

## Requirements

### Required

-   A modern web browser
-   A running llama-swap instance

### For `serve.py`

-   Python 3.x

No Python packages need to be installed.

`serve.py` uses only Python's standard library.

## Installation

Clone the repository:

    git clone https://github.com/drone540/llama-swap-webui.git
    cd llama-swap-webui
    

The repository contains:

    llama-swap-webui/
    ├── index.html
    ├── serve.py
    └── README.md
    

## Configuration

The WebUI stores its settings in the browser's `localStorage`.

The API Base URL can be configured from the Settings interface.

For example, if llama-swap is running directly on:

    http://127.0.0.1:8080
    

the WebUI can use:

    http://127.0.0.1:8080
    

If using `serve.py` with port `8000`, use:

    http://127.0.0.1:8000
    

## Running with `serve.py`

Assuming llama-swap is running on:

    http://127.0.0.1:8080
    

start the WebUI server with:

    python serve.py --upstream http://127.0.0.1:8080 --port 8000
    

Then open:

    http://127.0.0.1:8000
    

Set the WebUI's API Base URL to:

    http://127.0.0.1:8000
    

The Python server will serve `index.html` and proxy supported API paths to llama-swap.

For example:

    Browser
      │
      │ GET /v1/models
      ▼
    serve.py
      │
      │ GET http://127.0.0.1:8080/v1/models
      ▼
    llama-swap
    

## Using a Remote llama-swap Server

`serve.py` can proxy to a llama-swap instance on another machine.

For example:

    python serve.py \
      --upstream http://192.168.1.22:8080 \
      --port 8000
    

Then open:

    http://localhost:8000
    

and configure the WebUI API Base URL as:

    http://localhost:8000
    

This allows the browser to communicate only with the local WebUI server while `serve.py` handles communication with the remote llama-swap instance.

## Proxied Endpoints

`serve.py` proxies llama-swap endpoints including:

    /v1/*
    /infill
    /running
    /health
    /metrics
    /logs
    /api/*
    /sdapi/*
    /comfyui/*
    /audioapi/*
    /profiles
    

The `/v1/models` endpoint is also explicitly handled.

Other paths are served as normal static files by Python's built-in HTTP server.

## Streaming

Streaming is an important part of the server implementation.

`serve.py` uses HTTP/1.1 and forwards streaming responses incrementally instead of buffering the entire response.

This is particularly important for:

-   Chat streaming
-   Server-Sent Events
-   Live logs
-   `/logs/stream`
-   Long-running model generation

The server detects `text/event-stream`, chunked responses, and responses without a known content length and forwards them progressively.

## Browser Storage

Chat history, folders, prompt templates, and WebUI settings are stored locally in the browser using `localStorage`.

This means your conversations are not stored by this repository or by `serve.py`.

Clearing the browser's site data/local storage will remove locally stored conversations and settings.

The llama-swap server itself remains responsible for model execution and API requests.

## External Frontend Dependencies

The application does not require a frontend build step, but `index.html` loads several JavaScript libraries from public CDNs, including:

-   Tailwind CSS
-   Lucide
-   Marked
-   Highlight.js

Therefore, an internet connection may be required for the full UI experience when loading the page for the first time, unless these dependencies are changed to local copies.

## API Compatibility

The WebUI is designed around llama-swap's APIs and OpenAI-compatible interfaces.

It dynamically retrieves the available models from:

    /v1/models
    

and examines model metadata/capabilities to determine which models should be offered for features such as:

-   Chat
-   Completion
-   Vision
-   Image generation
-   Image editing
-   Text-to-speech
-   Speech-to-text
-   Embeddings
-   Reranking
-   Tool/function calling

This allows the model selectors to automatically adapt to the models exposed by the llama-swap server.

## Troubleshooting

### The Chat tab works, but System shows CORS errors

This is the primary reason `serve.py` exists.

If the WebUI is running on a different origin from llama-swap, browsers may block llama-swap's native endpoints because they do not return the required CORS headers.

Run:

    python serve.py --upstream http://YOUR_LLAMA_SWAP_HOST:8080 --port 8000
    

Then open:

    http://localhost:8000
    

and set the API Base URL to:

    http://localhost:8000
    

### I opened `index.html` directly

Opening the HTML file using:

    file:///
    

is supported for basic functionality, but browser security restrictions mean that some llama-swap native endpoints may not work.

For the complete experience, use `serve.py`.

### Models are not appearing

Check that llama-swap is running and that:

    /v1/models
    

is accessible.

You can test it with:

    curl http://127.0.0.1:8080/v1/models
    

If using `serve.py`:

    curl http://127.0.0.1:8000/v1/models
    

### ComfyUI tab is empty

The ComfyUI tab depends on llama-swap exposing:

    /comfyui/
    

This requires the corresponding llama-swap configuration.

Image generation through the Image tab does not require the embedded ComfyUI panel.

## Project Structure

    llama-swap-webui/
    │
    ├── index.html    # Complete WebUI
    ├── serve.py      # Optional static server + CORS proxy
    └── README.md     # Documentation
    

### `index.html`

The entire frontend is contained in a single HTML file.

It includes:

-   HTML markup
-   CSS
-   JavaScript
-   Application state management
-   API communication
-   Chat storage
-   Rendering
-   Model capability detection
-   Feature-specific interfaces

There is no npm project or frontend compilation step.

### `serve.py`

A small Python companion server based entirely on the Python standard library.

It:

-   Serves the WebUI
-   Proxies llama-swap API requests
-   Avoids browser CORS restrictions
-   Supports GET/HEAD/POST/PUT/PATCH/DELETE
-   Handles streaming responses
-   Supports long-running log streams
-   Requires no third-party Python dependencies

## Security Considerations

This project is intended primarily for local or trusted-network use.

`serve.py` is a lightweight HTTP server and reverse proxy. It should **not** be assumed to provide authentication or authorization.

If you expose the WebUI or proxy to an untrusted network, consider placing it behind an appropriate authenticated reverse proxy and using HTTPS.

In particular, be careful when:

-   Binding the server to a publicly accessible interface
-   Proxying a llama-swap instance on a private network
-   Exposing model management endpoints
-   Allowing other users to access the WebUI

## Credits

This project is a WebUI designed to work with llama-swap.

The WebUI is intentionally kept simple to deploy: one HTML file for the frontend and one optional Python file for serving/proxying.

## License

See the repository for the applicable license information.
