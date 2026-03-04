"""FastAPI server exposing the Compass AI agent via a chat API."""

from __future__ import annotations

import logging
import os
import warnings

# Suppress noisy dependency warnings (must run before langchain imports)
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
warnings.filterwarnings("ignore", module="requests")
warnings.filterwarnings("ignore", message=".*supported version.*")
warnings.filterwarnings("ignore", message=".*PyTorch.*TensorFlow.*Flax.*")
logging.getLogger("transformers").setLevel(logging.ERROR)

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from compass_cli.agent import build_agent


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    messages: list[ChatMessage]


def _to_api_messages(lc_messages) -> list[ChatMessage]:
    """Convert LangChain message objects to API format.

    The LangChain agent may emit intermediate AI messages that only contain
    tool-call metadata or other non-user-facing content. Those should not be
    exposed to the frontend as visible assistant messages, otherwise they
    render as empty bubbles in the UI.
    """

    def _extract_text_content(msg) -> str:
        """Best-effort extraction of displayable text from a LangChain message."""
        content = getattr(msg, "content", "")
        # Common case: simple string content
        if isinstance(content, str):
            return content

        # Newer LangChain messages may use a list of content blocks
        parts: list[str] = []
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str):
                        parts.append(text)
                elif isinstance(part, str):
                    parts.append(part)
        elif content is not None:
            # Fallback: stringify unknown structures
            parts.append(str(content))

        return "\n".join(parts)

    out: list[ChatMessage] = []
    for msg in lc_messages:
        msg_type = getattr(msg, "type", None) or type(msg).__name__
        if msg_type in ("human", "HumanMessage"):
            text = _extract_text_content(msg)
            out.append(ChatMessage(role="user", content=text))
        elif msg_type in ("ai", "AIMessage"):
            text = _extract_text_content(msg)
            # Skip AI messages that have no displayable text (e.g. tool calls)
            if not text or not text.strip():
                continue
            out.append(ChatMessage(role="assistant", content=text))
    return out


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build agent once at startup."""
    app.state.agent = build_agent()
    yield
    app.state.agent = None


app = FastAPI(
    title="Compass AI API",
    description="Chat API for the Compass AI professor recommendation agent.",
    lifespan=lifespan,
)

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Process a chat message and return the assistant's response."""
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    # Ensure last message is from user
    last = request.messages[-1]
    if last.role != "user":
        raise HTTPException(
            status_code=400,
            detail="last message must be from user",
        )

    # Convert to format agent expects
    lc_input = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        agent = app.state.agent
        handler = getattr(agent, "_compass_tool_logging_handler", None)
        attached = bool(getattr(agent, "_compass_tool_logging_attached", False))
        if handler is not None and not attached:
            result = agent.invoke({"messages": lc_input}, config={"callbacks": [handler]})
        else:
            result = agent.invoke({"messages": lc_input})
    except Exception as e:
        err_msg = str(e).split("\n")[0] if str(e) else type(e).__name__
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {err_msg}",
        ) from e

    messages = result.get("messages") if isinstance(result, dict) else None
    if not messages:
        raise HTTPException(
            status_code=500,
            detail="Agent returned no messages",
        )

    api_messages = _to_api_messages(messages)
    return ChatResponse(messages=api_messages)
