from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

try:
    # LangChain v0.1+/v0.2+
    from langchain.callbacks.base import BaseCallbackHandler
except Exception:  # pragma: no cover
    # Older import path fallback
    from langchain_core.callbacks.base import BaseCallbackHandler  # type: ignore


_REDACT_KEYS = {
    "api_key",
    "openai_api_key",
    "authorization",
    "auth",
    "token",
    "access_token",
    "refresh_token",
    "supabase_key",
    "service_role_key",
    "password",
    "secret",
}


def _looks_like_secret_key(key: str) -> bool:
    k = key.lower()
    return any(part in k for part in _REDACT_KEYS)


def _truncate_str(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 12] + f"...({len(s)} chars)"


def _sanitize(
    obj: Any,
    *,
    max_str_len: int = 500,
    max_list_len: int = 50,
    max_dict_items: int = 50,
    _depth: int = 0,
    _max_depth: int = 6,
) -> Any:
    """Redact common secrets + truncate large values for readable logs."""
    if _depth > _max_depth:
        return "<truncated: max_depth>"

    if obj is None:
        return None
    if isinstance(obj, (bool, int, float)):
        return obj
    if isinstance(obj, bytes):
        return f"<bytes: {len(obj)}>"
    if isinstance(obj, str):
        return _truncate_str(obj, max_str_len)

    if isinstance(obj, Mapping):
        out: dict[str, Any] = {}
        items = list(obj.items())
        for i, (k, v) in enumerate(items):
            if i >= max_dict_items:
                out["<truncated>"] = f"+{len(items) - max_dict_items} more keys"
                break
            key_str = str(k)
            if _looks_like_secret_key(key_str):
                out[key_str] = "<redacted>"
            else:
                out[key_str] = _sanitize(
                    v,
                    max_str_len=max_str_len,
                    max_list_len=max_list_len,
                    max_dict_items=max_dict_items,
                    _depth=_depth + 1,
                    _max_depth=_max_depth,
                )
        return out

    if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
        seq = list(obj)
        trimmed = seq[:max_list_len]
        out_list = [
            _sanitize(
                v,
                max_str_len=max_str_len,
                max_list_len=max_list_len,
                max_dict_items=max_dict_items,
                _depth=_depth + 1,
                _max_depth=_max_depth,
            )
            for v in trimmed
        ]
        if len(seq) > max_list_len:
            out_list.append(f"<truncated: +{len(seq) - max_list_len} more items>")
        return out_list

    # Fallback for objects (pydantic models, etc.)
    try:
        return _truncate_str(str(obj), max_str_len)
    except Exception:
        return "<unprintable>"


def _to_json_line(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True)
    except Exception:
        return json.dumps({"unserializable": _sanitize(obj)})


class ToolCallPrintHandler(BaseCallbackHandler):
    """Print tool calls + tool results to stdout (sanitized)."""

    def on_tool_start(  # type: ignore[override]
        self,
        serialized: dict[str, Any] | None = None,
        input_str: str | None = None,
        *,
        inputs: dict[str, Any] | None = None,
        name: str | None = None,
        **kwargs: Any,
    ) -> None:
        tool_name = (
            name
            or (serialized or {}).get("name")
            or (serialized or {}).get("id")
            or "unknown_tool"
        )

        params: Any
        if inputs is not None:
            params = inputs
        elif input_str is not None:
            params = input_str
        else:
            params = kwargs.get("input") or kwargs.get("tool_input") or {}

        payload = {"tool": tool_name, "params": _sanitize(params)}
        print(f"TOOL_CALL {tool_name} {_to_json_line(payload['params'])}", flush=True)

    def on_tool_end(  # type: ignore[override]
        self,
        output: Any,
        *,
        name: str | None = None,
        **kwargs: Any,
    ) -> None:
        tool_name = name or kwargs.get("tool") or "unknown_tool"
        payload = {"tool": tool_name, "output": _sanitize(output)}
        print(f"TOOL_RESULT {tool_name} {_to_json_line(payload['output'])}", flush=True)

    def on_tool_error(  # type: ignore[override]
        self,
        error: BaseException,
        *,
        name: str | None = None,
        **kwargs: Any,
    ) -> None:
        tool_name = name or kwargs.get("tool") or "unknown_tool"
        payload = {"tool": tool_name, "error": _sanitize(str(error))}
        print(f"TOOL_ERROR {tool_name} {_to_json_line(payload['error'])}", flush=True)

