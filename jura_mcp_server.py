#!/usr/bin/env python3
"""Jura MCP server — exposes Jura jurisdiction tools to Cursor (and any MCP client).

Run via stdio (Cursor will start this automatically):
    python jura_mcp_server.py

Jura must be running on port 8003:
    uvicorn jura.server:app --port 8003
"""
from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

JURA_BASE = "http://localhost:8003"

app = Server("jura")


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="check_jurisdiction",
            description=(
                "Run a full jurisdiction check on a commercial insurance submission. "
                "Returns routing decision (admitted / E&S / blocked), all triggered DOI flags, "
                "and plain-language rationale. This is the main Jura entry point."
            ),
            inputSchema={
                "type": "object",
                "required": ["submission_id", "insured_name", "state", "zip_code", "sic_code", "tiv", "credit_score_used", "new_business"],
                "properties": {
                    "submission_id":    {"type": "string", "description": "Unique submission identifier (e.g. SUB-ABC123)"},
                    "insured_name":     {"type": "string", "description": "Legal name of the insured business"},
                    "state":            {"type": "string", "description": "2-letter writing state code (e.g. CA, TX, FL)"},
                    "zip_code":         {"type": "string", "description": "5-digit premises ZIP code"},
                    "sic_code":         {"type": "string", "description": "4-digit SIC code"},
                    "tiv":              {"type": "number", "description": "Total Insured Value in dollars"},
                    "credit_score_used":{"type": "boolean", "description": "Was credit score used in pricing?"},
                    "new_business":     {"type": "boolean", "description": "True = new business, False = renewal"},
                },
            },
        ),
        Tool(
            name="get_submission",
            description="Retrieve a stored submission and its current status from Jura.",
            inputSchema={
                "type": "object",
                "required": ["submission_id"],
                "properties": {
                    "submission_id": {"type": "string", "description": "Submission ID to look up"},
                },
            },
        ),
        Tool(
            name="list_submissions",
            description="List all submissions in Jura, optionally filtered by status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status: jura_pending, forwarded_to_aria, admitted_disclose_pending, surplus_pending, jurisdiction_blocked",
                    },
                    "limit": {"type": "integer", "description": "Max results (default 20, max 200)"},
                },
            },
        ),
        Tool(
            name="get_audit_trail",
            description="Get the full tamper-evident audit trail for a submission (all events: EVALUATED, BLOCKED, FORWARDED, etc.)",
            inputSchema={
                "type": "object",
                "required": ["submission_id"],
                "properties": {
                    "submission_id": {"type": "string", "description": "Submission ID"},
                },
            },
        ),
        Tool(
            name="get_jurisdiction_result",
            description="Get the stored JurisdictionResult for a submission (requires /evaluate to have been called first).",
            inputSchema={
                "type": "object",
                "required": ["submission_id"],
                "properties": {
                    "submission_id": {"type": "string", "description": "Submission ID"},
                },
            },
        ),
        Tool(
            name="reset_demo",
            description="Clear all in-memory state (submissions, audit log, session results). Useful for a clean demo run.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="health_check",
            description="Check Jura server health: version, LLM provider status, HITL mode, Aria endpoint.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    async with httpx.AsyncClient(base_url=JURA_BASE, timeout=15.0) as client:
        try:
            if name == "check_jurisdiction":
                r = await client.post("/evaluate", json=arguments)
                return [TextContent(type="text", text=_fmt(r))]

            elif name == "get_submission":
                sid = arguments["submission_id"]
                r = await client.get(f"/submissions/{sid}")
                return [TextContent(type="text", text=_fmt(r))]

            elif name == "list_submissions":
                params: dict[str, Any] = {}
                if "status" in arguments:
                    params["status"] = arguments["status"]
                if "limit" in arguments:
                    params["limit"] = arguments["limit"]
                r = await client.get("/submissions", params=params)
                return [TextContent(type="text", text=_fmt(r))]

            elif name == "get_audit_trail":
                sid = arguments["submission_id"]
                r = await client.get(f"/audit/{sid}")
                return [TextContent(type="text", text=_fmt(r))]

            elif name == "get_jurisdiction_result":
                sid = arguments["submission_id"]
                r = await client.get(f"/results/{sid}")
                return [TextContent(type="text", text=_fmt(r))]

            elif name == "reset_demo":
                r = await client.get("/demo/reset")
                return [TextContent(type="text", text=_fmt(r))]

            elif name == "health_check":
                r = await client.get("/health")
                return [TextContent(type="text", text=_fmt(r))]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except httpx.ConnectError:
            return [TextContent(
                type="text",
                text=f"Cannot connect to Jura at {JURA_BASE}. Start the server first:\n"
                     f"  uvicorn jura.server:app --port 8003",
            )]
        except Exception as exc:
            return [TextContent(type="text", text=f"Error calling {name}: {exc}")]


def _fmt(response: httpx.Response) -> str:
    try:
        return json.dumps(response.json(), indent=2)
    except Exception:
        return response.text


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
