# 📋 Lead Capture Agent

A conversational application built with **[Google ADK (Agent Development Kit)](https://google.github.io/adk-docs/)** and **[Streamlit](https://streamlit.io/)** to collect and validate prospect (lead) contact information through an interactive chat interface.

## ✨ Features

- **Guided conversational capture**: The agent naturally and politely collects the 4 required lead fields without re-asking for details already provided:
  1. **Full Name** (`full_name`)
  2. **Date of Birth** (`birth_date`)
  3. **Email Address** (`email`), with format validation
  4. **Reason for Contact** (`contact_reason`)
- **Real-time progress tracking**: Sidebar showing capture progress (`0/4` to `4/4`), a per-field checklist, and a button to start capturing a new lead.
- **Captured leads table**: Live interactive table displaying every completed lead once all 4 required fields are collected.
- **ADK tools & session state**: Uses `save_lead_info` and `get_lead_info` with `ToolContext` and `InMemorySessionService` to persist lead details in session state (`user:lead_info`) powered by `gemini-3.5-flash-lite`.

## 📁 Project Structure

```text
lead-capture-agent/
├── lead_capture_agent/
│   ├── __init__.py      # Exports the agent module for Google ADK
│   ├── agent.py         # root_agent definition and tools (save_lead_info, get_lead_info)
│   └── .env             # Environment variables (not tracked by git)
├── streamlit_app.py     # Streamlit chat UI, progress sidebar, and leads table
├── pyproject.toml       # Project metadata and dependencies
└── README.md
```

## 📋 Prerequisites

- **Python 3.14** or higher (see `.python-version`).
- **[uv](https://docs.astral.sh/uv/)** for managing the virtual environment and dependencies.
- A Google Gemini API key (`GOOGLE_API_KEY`).

## 🚀 Installation & Setup

1. **Install `uv`** (if you don't already have it):

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Sync dependencies**:

   ```bash
   uv sync
   ```

3. **Configure your API key**:

   Create a `.env` file at the project root or inside `lead_capture_agent/.env` with your Gemini API key:

   ```env
   GOOGLE_API_KEY=your_api_key_here
   ```

## ▶️ Running the Application

### Streamlit Web UI

```bash
uv run streamlit run streamlit_app.py
```

The app will be available at `http://localhost:8501`.

### Testing with Google ADK CLI (optional)

You can also interact with the agent directly using the Google ADK CLI:

```bash
# ADK developer web UI
uv run adk web

# Interactive CLI session
uv run adk run lead_capture_agent
```

## 📄 License

This project is licensed under the [Apache 2.0 License](LICENSE).
