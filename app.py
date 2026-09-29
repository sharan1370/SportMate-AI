"""
SportMate AI — Sports Facility Booking Assistant
Streamlit front-end for the LangGraph booking agent.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import inspect
import json
import logging
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("sportmate.ui")


# ============================================================
# CONSTANTS
# ============================================================

APP_NAME = "SportMate AI"
APP_TAGLINE = "Sports facility booking assistant"
MAX_TURNS_KEPT = 200  # guards against unbounded session growth

QUICK_ACTIONS: List[Tuple[str, str]] = [
    (
        "Check availability",
        "Is badminton court BC1 available on 2026-09-20 at 7 PM for 1 hour?",
    ),
    (
        "Book a court",
        "Book badminton court BC2 on 2026-09-20 at 7 PM for 1 hour",
    ),
    (
        "See pricing",
        "How much is a badminton court for 1 hour?",
    ),
]

EXAMPLE_LIBRARY: Dict[str, List[str]] = {
    "Availability": [
        "Is BC1 available on 2026-09-20 at 7 PM for 1 hour?",
        "Which football turfs are free tomorrow evening?",
    ],
    "Booking": [
        "Book badminton court BC2 on 2026-09-20 at 7 PM for 1 hour",
        "Reserve the multipurpose room on 2026-09-21 at 10 AM for 2 hours",
    ],
    "Manage a booking": [
        "Cancel booking BKG1013",
        "Reschedule booking BKG1013",
    ],
    "Pricing & equipment": [
        "How much is a badminton court for 1 hour?",
        "How much is a badminton racket?",
    ],
}


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"about": f"{APP_NAME} — {APP_TAGLINE}"},
)


# ============================================================
# STREAMLIT VERSION COMPATIBILITY
# ============================================================

def _full_width_kwargs() -> Dict[str, Any]:
    """
    Newer Streamlit releases replace `use_container_width` with `width`.
    Detect which one this runtime accepts so the app never emits
    deprecation warnings or raises TypeError.
    """
    try:
        params = inspect.signature(st.button).parameters
        if "width" in params:
            return {"width": "stretch"}
        if "use_container_width" in params:
            return {"use_container_width": True}
    except (TypeError, ValueError):  # pragma: no cover - defensive
        pass
    return {}


FULL_WIDTH = _full_width_kwargs()


def safe_rerun() -> None:
    """Rerun the script across Streamlit versions."""
    rerun = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if callable(rerun):
        rerun()


# ============================================================
# STYLES
# ============================================================

st.markdown(
    """
    <style>
        :root {
            --sm-line: color-mix(in srgb, currentColor 18%, transparent);
            --sm-soft: color-mix(in srgb, currentColor 6%, transparent);
        }

        .block-container {
            max-width: 1040px;
            padding-top: 2.2rem;
            padding-bottom: 6rem;
        }

        .sm-header {
            display: flex;
            align-items: baseline;
            gap: 0.75rem;
            padding-bottom: 0.35rem;
            border-bottom: 1px solid var(--sm-line);
            margin-bottom: 1.25rem;
        }

        .sm-title {
            font-size: 1.9rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            line-height: 1.1;
        }

        .sm-tagline {
            font-size: 0.95rem;
            opacity: 0.65;
        }

        .sm-note {
            padding: 0.9rem 1.1rem;
            border: 1px solid var(--sm-line);
            border-left-width: 3px;
            border-radius: 8px;
            background: var(--sm-soft);
            font-size: 0.92rem;
            line-height: 1.55;
            margin-bottom: 1.1rem;
        }

        .sm-meta {
            font-size: 0.75rem;
            opacity: 0.55;
            margin-top: 0.35rem;
        }

        .stChatMessage { border-radius: 12px; }

        div[data-testid="stSidebar"] .stButton button {
            text-align: left;
            font-size: 0.86rem;
        }

        @media (prefers-reduced-motion: reduce) {
            * { animation: none !important; transition: none !important; }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# AGENT STATE
# ============================================================

def new_agent_state() -> Dict[str, Any]:
    """A fresh, fully-populated agent state. Single source of truth."""
    return {
        "messages": [],
        "user_message": "",
        "intent": "",
        "entities": {},
        "tool_name": "",
        "tool_input": {},
        "tool_result": None,
        "last_tool_name": "",
        "last_tool_call_id": "",
        "retrieved_context": [],
        "confirmation_required": False,
        "confirmation_pending": False,
        "confirmed": False,
        "pending_booking": None,
        "pending_booking_price": None,
        "pending_rescheduling": None,
        "pending_cancellation": None,
        "awaiting_membership": False,
        "pending_is_member": None,
        "final_answer": "",
        "error": None,
    }


TRANSIENT_FIELDS = (
    "tool_name",
    "tool_input",
    "tool_result",
    "last_tool_name",
    "last_tool_call_id",
    "error",
    "final_answer",
)


def reset_turn_fields(state: Dict[str, Any]) -> None:
    """
    Clear only per-turn scratch fields. Pending booking, cancellation and
    rescheduling data must survive so multi-turn flows keep working.
    """
    blank = new_agent_state()
    for field in TRANSIENT_FIELDS:
        state[field] = blank[field]


# ============================================================
# AGENT LOADING
# ============================================================

@st.cache_resource(show_spinner="Starting the booking agent…")
def load_agent() -> Tuple[Optional[Any], Optional[str]]:
    """
    Build the LangGraph agent once per server process.
    Returns (agent, error_message). Never raises, so the UI can always render.
    """
    try:
        from src.agent.graph import build_graph

        return build_graph(), None
    except Exception:
        logger.exception("Agent failed to build")
        return None, traceback.format_exc()


agent, agent_error = load_agent()


# ============================================================
# SESSION STATE
# ============================================================

DEFAULTS: Dict[str, Any] = {
    "messages": [],
    "agent_state": None,          # filled below
    "pending_prompt": None,
    "developer_mode": False,
    "turn_count": 0,
    "started_at": datetime.now().strftime("%d %b %Y, %H:%M"),
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

if st.session_state.agent_state is None:
    st.session_state.agent_state = new_agent_state()


def reset_conversation() -> None:
    """Clear the transcript and start a brand-new agent state."""
    st.session_state.messages = []
    st.session_state.agent_state = new_agent_state()
    st.session_state.pending_prompt = None
    st.session_state.turn_count = 0
    st.session_state.started_at = datetime.now().strftime("%d %b %Y, %H:%M")
    logger.info("Conversation reset")


# ============================================================
# AGENT INVOCATION
# ============================================================

def extract_answer(result: Dict[str, Any]) -> str:
    """Pull a user-facing string out of whatever the graph returned."""
    answer = result.get("final_answer")
    if isinstance(answer, str) and answer.strip():
        return answer.strip()
    if answer:
        return str(answer)

    tool_result = result.get("tool_result")
    if isinstance(tool_result, dict):
        for field in ("message", "answer", "reason", "summary", "text"):
            value = tool_result.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return f"```json\n{json.dumps(tool_result, indent=2, default=str)}\n```"
    if tool_result:
        return str(tool_result)

    error = result.get("error")
    if error:
        return f"The agent stopped before answering: {error}"

    return "No answer came back for that request. Try rephrasing it."


def run_agent(user_message: str) -> Dict[str, Any]:
    """
    Send one message through the graph, reusing the same agent state so
    multi-turn flows (details → availability → price → confirm → book,
    and the cancel / reschedule equivalents) stay intact.

    Returns a dict: {"content", "latency", "failed", "trace"}.
    """
    started = time.perf_counter()

    if agent is None:
        return {
            "content": (
                "The booking agent isn't running, so requests can't be processed. "
                "Check the server logs, then reload this page."
            ),
            "latency": 0.0,
            "failed": True,
            "trace": agent_error,
        }

    state = st.session_state.agent_state
    state["user_message"] = user_message
    reset_turn_fields(state)

    try:
        result = agent.invoke(state)

        if isinstance(result, dict):
            st.session_state.agent_state = result
        else:  # graph returned something unexpected but usable
            logger.warning("Agent returned %s, keeping previous state", type(result))
            result = {"final_answer": str(result)}

        return {
            "content": extract_answer(result),
            "latency": time.perf_counter() - started,
            "failed": bool(result.get("error")),
            "trace": None,
        }

    except Exception as exc:
        logger.exception("Agent invocation failed")
        st.session_state.agent_state["error"] = str(exc)
        return {
            "content": (
                "That request couldn't be completed. The details are in the server "
                "logs — try again, or start a new conversation."
            ),
            "latency": time.perf_counter() - started,
            "failed": True,
            "trace": traceback.format_exc(),
        }


def queue_prompt(prompt: str) -> None:
    """Queue a prompt from a button; it runs on the next script run."""
    st.session_state.pending_prompt = prompt
    safe_rerun()


def append_message(role: str, content: str, **meta: Any) -> None:
    st.session_state.messages.append({"role": role, "content": content, **meta})
    if len(st.session_state.messages) > MAX_TURNS_KEPT:
        st.session_state.messages = st.session_state.messages[-MAX_TURNS_KEPT:]


def transcript_text() -> str:
    lines = [f"{APP_NAME} transcript — {st.session_state.started_at}", ""]
    for message in st.session_state.messages:
        speaker = "You" if message["role"] == "user" else APP_NAME
        lines.append(f"{speaker}: {message['content']}\n")
    return "\n".join(lines)


def state_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    """The fields worth watching while debugging a flow."""
    keys = (
        "intent",
        "entities",
        "tool_name",
        "confirmation_required",
        "confirmation_pending",
        "confirmed",
        "awaiting_membership",
        "pending_is_member",
        "pending_booking",
        "pending_booking_price",
        "pending_cancellation",
        "pending_rescheduling",
        "error",
    )
    return {key: state.get(key) for key in keys}


def active_flow(state: Dict[str, Any]) -> Optional[str]:
    if state.get("pending_booking"):
        return "Booking in progress"
    if state.get("pending_cancellation"):
        return "Cancellation in progress"
    if state.get("pending_rescheduling"):
        return "Reschedule in progress"
    if state.get("awaiting_membership"):
        return "Waiting for membership status"
    return None


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown(f"### 🏆 {APP_NAME}")
    st.caption(APP_TAGLINE)

    if agent is None:
        st.error("Agent offline — check `src/agent/graph.py`.")
    else:
        flow = active_flow(st.session_state.agent_state)
        if flow:
            st.info(flow)
        else:
            st.success("Agent ready")

    st.divider()

    st.markdown("**Try one of these**")
    for group, prompts in EXAMPLE_LIBRARY.items():
        with st.expander(group, expanded=False):
            for index, prompt in enumerate(prompts):
                if st.button(prompt, key=f"ex_{group}_{index}", **FULL_WIDTH):
                    queue_prompt(prompt)

    st.divider()

    st.markdown("**Booking codes**")
    st.caption(
        "Courts use a prefix and number (BC1, BC2 for badminton). "
        "Bookings look like BKG1013. Dates are YYYY-MM-DD."
    )

    st.divider()

    if st.button("Start a new conversation", **FULL_WIDTH):
        reset_conversation()
        safe_rerun()

    if st.session_state.messages:
        st.download_button(
            "Download transcript",
            data=transcript_text(),
            file_name=f"sportmate-{datetime.now():%Y%m%d-%H%M}.txt",
            mime="text/plain",
            **FULL_WIDTH,
        )

    st.session_state.developer_mode = st.toggle(
        "Developer mode",
        value=st.session_state.developer_mode,
        help="Show the agent's internal state and full error traces.",
    )

    st.divider()
    st.caption(f"Session started {st.session_state.started_at}")


# ============================================================
# HEADER
# ============================================================

st.markdown(
    f"""
    <div class="sm-header">
        <span class="sm-title">🏆 {APP_NAME}</span>
        <span class="sm-tagline">{APP_TAGLINE}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if agent is None:
    st.error(
        "The booking agent didn't start, so nothing can be booked or checked right now. "
        "Fix the import error below and reload the page."
    )
    if st.session_state.developer_mode and agent_error:
        st.code(agent_error, language="text")


# ============================================================
# EMPTY STATE
# ============================================================

if not st.session_state.messages:
    st.markdown(
        """
        <div class="sm-note">
            Ask about courts, turfs and rooms — check what's free, book it, price it,
            add equipment, or change a booking you already have.
            Start with a request below or type your own.
        </div>
        """,
        unsafe_allow_html=True,
    )

    columns = st.columns(len(QUICK_ACTIONS))
    for column, (label, prompt) in zip(columns, QUICK_ACTIONS):
        with column:
            if st.button(label, key=f"quick_{label}", disabled=agent is None, **FULL_WIDTH):
                queue_prompt(prompt)


# ============================================================
# TRANSCRIPT
# ============================================================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if (
            message["role"] == "assistant"
            and st.session_state.developer_mode
            and message.get("latency") is not None
        ):
            st.markdown(
                f'<div class="sm-meta">{message["latency"]:.2f}s</div>',
                unsafe_allow_html=True,
            )


# ============================================================
# INPUT AND TURN HANDLING
# ============================================================

typed = st.chat_input(
    "Ask about availability, bookings, pricing or equipment…",
    disabled=agent is None,
)

prompt = typed or st.session_state.pending_prompt
st.session_state.pending_prompt = None

if prompt:
    prompt = prompt.strip()

if prompt:
    append_message("user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Checking the booking system…"):
            response = run_agent(prompt)

        st.markdown(response["content"])

        if st.session_state.developer_mode:
            st.markdown(
                f'<div class="sm-meta">{response["latency"]:.2f}s</div>',
                unsafe_allow_html=True,
            )
            if response["trace"]:
                with st.expander("Error trace"):
                    st.code(response["trace"], language="text")

    append_message(
        "assistant",
        response["content"],
        latency=response["latency"],
        failed=response["failed"],
    )
    st.session_state.turn_count += 1

    # Refresh the sidebar flow badge and state panel with the new state.
    safe_rerun()


# ============================================================
# DEVELOPER PANEL
# ============================================================

if st.session_state.developer_mode:
    with st.expander("Agent state", expanded=False):
        left, right = st.columns(2)
        left.metric("Turns", st.session_state.turn_count)
        right.metric("Messages", len(st.session_state.messages))
        st.json(state_summary(st.session_state.agent_state))