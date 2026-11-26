import asyncio
import threading
from pathlib import Path
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from lead_capture_agent.agent import REQUIRED_LEAD_FIELDS, root_agent

# Load environment variables from .env at the project root or inside lead_capture_agent/
load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(__file__).parent / "lead_capture_agent" / ".env")

APP_NAME = "lead_capture_app"

FIELD_LABELS = {
    "full_name": "Full Name",
    "birth_date": "Date of Birth",
    "email": "Email Address",
    "contact_reason": "Reason for Contact",
}

WELCOME_MESSAGE = (
    "Hello! To help you and follow up on your request, "
    "I need to collect a few details: your **full name**, **date of birth**, "
    "**email address**, and a **brief reason for contact**. "
    "Which details would you like to start with?"
)


@st.cache_resource
def _get_event_loop() -> asyncio.AbstractEventLoop:
    """Maintains a single persistent event loop on a background thread.

    Prevents `asyncio.run()` from closing the loop at the end of each turn while
    the async HTTP client in `google-genai` / `httpx` still holds connections
    bound to that loop.
    """
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    return loop


def _run_async(coro):
    """Runs a coroutine on the persistent event loop from Streamlit."""
    loop = _get_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()


async def _ensure_session(
    session_service: InMemorySessionService,
    user_id: str,
    session_id: str,
):
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    if session is None:
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
    return session


async def _send_to_agent(
    runner: Runner,
    session_service: InMemorySessionService,
    user_id: str,
    session_id: str,
    message_text: str,
) -> tuple[str, dict]:
    await _ensure_session(session_service, user_id, session_id)

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=message_text)],
    )

    final_chunks: list[str] = []
    fallback_chunks: list[str] = []

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
    ):
        if event.content and event.content.parts:
            text_parts = [p.text for p in event.content.parts if getattr(p, "text", None)]
            if text_parts:
                joined = "".join(text_parts)
                if event.is_final_response():
                    final_chunks.append(joined)
                else:
                    fallback_chunks.append(joined)

    reply = "\n".join(final_chunks).strip() or "\n".join(fallback_chunks).strip()
    if not reply:
        reply = "Sorry, I didn't receive a response from the agent. Could you please try again?"

    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    raw_lead = session.state.get("user:lead_info", {}) if session else {}
    lead_info = dict(raw_lead) if isinstance(raw_lead, dict) else {}

    return reply, lead_info


def _is_lead_complete(lead: dict) -> bool:
    return all(bool(lead.get(field)) for field in REQUIRED_LEAD_FIELDS)


def _start_new_conversation() -> None:
    st.session_state.user_id = f"user-{uuid4().hex[:8]}"
    st.session_state.session_id = f"session-{uuid4().hex[:8]}"
    st.session_state.messages = [{"role": "assistant", "content": WELCOME_MESSAGE}]
    st.session_state.current_lead = {}


def _init_state() -> None:
    if "session_service" not in st.session_state:
        st.session_state.session_service = InMemorySessionService()
    if "runner" not in st.session_state:
        st.session_state.runner = Runner(
            agent=root_agent,
            app_name=APP_NAME,
            session_service=st.session_state.session_service,
        )
    if "captured_leads" not in st.session_state:
        st.session_state.captured_leads = {}
    if "session_id" not in st.session_state:
        _start_new_conversation()


def main() -> None:
    st.set_page_config(
        page_title="Lead Capture Agent",
        page_icon="📋",
        layout="wide",
    )

    _init_state()

    st.title("📋 Lead Capture Agent")
    st.caption(
        "Chat with the assistant to record full name, date of birth, "
        "email address, and a brief reason for contact."
    )

    with st.sidebar:
        st.subheader("Options")
        if st.button("➕ Capture new lead", width="stretch"):
            _start_new_conversation()
            st.rerun()

        st.divider()
        current_lead: dict = st.session_state.current_lead
        captured_count = sum(1 for f in REQUIRED_LEAD_FIELDS if current_lead.get(f))
        st.markdown(f"**Current progress:** {captured_count} / {len(REQUIRED_LEAD_FIELDS)}")
        st.progress(captured_count / len(REQUIRED_LEAD_FIELDS))
        for field in REQUIRED_LEAD_FIELDS:
            icon = "✅" if current_lead.get(field) else "⬜"
            st.write(f"{icon} {FIELD_LABELS[field]}")

    col_chat, col_table = st.columns([3, 2], gap="large")

    with col_chat:
        st.subheader("💬 Chat")
        chat_container = st.container(height=500)
        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

    with col_table:
        st.subheader("📊 Captured Lead Data")
        captured_rows = [
            {
                FIELD_LABELS[field]: lead.get(field, "")
                for field in REQUIRED_LEAD_FIELDS
            }
            for lead in st.session_state.captured_leads.values()
        ]

        if captured_rows:
            st.success(f"Captured leads: {len(captured_rows)}")
            st.dataframe(
                captured_rows,
                width="stretch",
                hide_index=True,
            )
        else:
            st.info(
                "No complete lead yet. The data will appear in this table "
                "once all 4 required fields have been captured."
            )

    if prompt := st.chat_input("Type your message here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with col_chat:
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)
                with st.chat_message("assistant"):
                    with st.spinner("Processing..."):
                        try:
                            reply, lead_info = _run_async(
                                _send_to_agent(
                                    runner=st.session_state.runner,
                                    session_service=st.session_state.session_service,
                                    user_id=st.session_state.user_id,
                                    session_id=st.session_state.session_id,
                                    message_text=prompt,
                                )
                            )
                        except Exception as exc:
                            reply = (
                                "An error occurred while communicating with the agent. "
                                f"Please check your API configuration (`GOOGLE_API_KEY`).\n\n`{exc}`"
                            )
                            lead_info = st.session_state.current_lead

                    st.markdown(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.session_state.current_lead = lead_info

        if _is_lead_complete(lead_info):
            st.session_state.captured_leads[st.session_state.session_id] = dict(lead_info)

        st.rerun()


if __name__ == "__main__":
    main()
