"""EGXpilot MCP integration used as a secondary analysis provider only.

Important: EGXpilot prices are NOT treated as the canonical/live quote source.
The module is fail-open so scanner execution never depends on EGXpilot uptime.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests

MCP_URL = "https://egxpilot.com/api/mcp"
PROTOCOL_VERSION = "2025-03-26"
TIMEOUT_SECONDS = 12


def _parse_response(resp: requests.Response) -> Dict[str, Any]:
    """Parse either JSON or Streamable-HTTP SSE MCP responses."""
    text = (resp.text or "").strip()
    if not text:
        return {}
    ctype = (resp.headers.get("content-type") or "").lower()
    if "application/json" in ctype:
        return resp.json()

    # Streamable HTTP commonly returns `event: message\ndata: {...}` blocks.
    payloads = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            raw = line[5:].strip()
            if raw and raw != "[DONE]":
                try:
                    payloads.append(json.loads(raw))
                except json.JSONDecodeError:
                    pass
    return payloads[-1] if payloads else {}


class EGXpilotMCP:
    def __init__(self, url: str = MCP_URL, timeout: int = TIMEOUT_SECONDS):
        self.url = url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "EGX-Smart-Scanner/1.0",
        })
        self.session_id: Optional[str] = None
        self._rpc_id = 0

    def _next_id(self) -> int:
        self._rpc_id += 1
        return self._rpc_id

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = {}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        resp = self.session.post(self.url, json=payload, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        sid = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
        if sid:
            self.session_id = sid
        return _parse_response(resp)

    def connect(self) -> None:
        if self.session_id:
            return
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "EGX Smart Scanner", "version": "1.0.0"},
            },
        }
        reply = self._post(payload)
        if reply.get("error"):
            raise RuntimeError(f"EGXpilot initialize failed: {reply['error']}")

        # MCP initialized notification. Some servers return 202/no body.
        try:
            self._post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        except Exception:
            # Do not fail a compatible server that does not require the notification.
            pass

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.connect()
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }
        reply = self._post(payload)
        if reply.get("error"):
            raise RuntimeError(f"EGXpilot tool {name} failed: {reply['error']}")
        result = reply.get("result") or {}

        # EGXpilot currently returns the tool payload as JSON inside text content.
        for item in result.get("content") or []:
            if item.get("type") == "text":
                raw = item.get("text") or ""
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    return {"text": raw}
        return result if isinstance(result, dict) else {"value": result}

    def stock_analysis(self, symbol: str) -> Dict[str, Any]:
        return self.call_tool("get_stock_analysis", {"symbol": symbol.upper()})

    def stock_snapshot(self, symbol: str) -> Dict[str, Any]:
        return self.call_tool("get_stock_snapshot", {"symbol": symbol.upper()})


def safe_stock_analysis(symbol: str) -> Dict[str, Any]:
    """One-shot fail-open helper for scanner jobs."""
    at = datetime.now(timezone.utc).isoformat()
    try:
        data = EGXpilotMCP().stock_analysis(symbol)
        return {
            "ok": True,
            "provider": "EGXpilot",
            "role": "SECONDARY_ANALYSIS_ONLY",
            "canonical_price": False,
            "fetched_at": at,
            "data": data,
        }
    except Exception as exc:
        return {
            "ok": False,
            "provider": "EGXpilot",
            "role": "SECONDARY_ANALYSIS_ONLY",
            "canonical_price": False,
            "fetched_at": at,
            "error": f"{type(exc).__name__}: {exc}",
        }
