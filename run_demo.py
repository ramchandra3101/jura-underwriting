#!/usr/bin/env python3
"""Demo launcher — starts Jura and shows available intake endpoints."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import webbrowser

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

BASE_URL = "http://localhost:8003"
JURA_PORT = 8003
console = Console()


# ---------------------------------------------------------------------------
# Health check / server management
# ---------------------------------------------------------------------------

def _is_running() -> bool:
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _wait_for_server(timeout: int = 15) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _is_running():
            return True
        time.sleep(0.5)
    return False


def _start_server() -> subprocess.Popen | None:
    env = os.environ.copy()
    env["HITL_MODE"] = "browser"
    python = sys.executable
    proc = subprocess.Popen(
        [python, "-m", "uvicorn", "jura.server:app", "--port", str(JURA_PORT), "--log-level", "warning"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def _print_endpoints() -> None:
    console.print()

    intake = Table(title="Intake Pipeline", show_lines=True)
    intake.add_column("Step", style="bold", width=5)
    intake.add_column("Method", width=8)
    intake.add_column("Endpoint", style="cyan", min_width=30)
    intake.add_column("Description", min_width=40)
    rows = [
        ("1", "POST", f"{BASE_URL}/intake/upload",              "Upload PDF or DOCX — Gemini extracts fields"),
        ("2", "GET",  f"{BASE_URL}/intake/drafts",              "List extracted drafts pending review"),
        ("3", "PATCH",f"{BASE_URL}/intake/drafts/{{draft_id}}", "Human edits extracted fields"),
        ("4", "POST", f"{BASE_URL}/intake/confirm/{{draft_id}}","Confirm draft → runs jurisdiction check"),
    ]
    for step, method, url, desc in rows:
        intake.add_row(step, method, url, desc)
    console.print(intake)
    console.print()

    api = Table(title="Jurisdiction & Results", show_lines=True)
    api.add_column("Method", width=8)
    api.add_column("Endpoint", style="cyan", min_width=30)
    api.add_column("Description", min_width=40)
    api_rows = [
        ("POST", f"{BASE_URL}/evaluate",                    "Evaluate a submission directly"),
        ("GET",  f"{BASE_URL}/results",                     "All session results"),
        ("GET",  f"{BASE_URL}/results/{{submission_id}}",   "Single result"),
        ("GET",  f"{BASE_URL}/audit/{{submission_id}}",     "Audit trail for a submission"),
        ("GET",  f"{BASE_URL}/submissions",                 "Submission store"),
        ("GET",  f"{BASE_URL}/demo/reset",                  "Clear all in-memory state"),
        ("GET",  f"{BASE_URL}/compliance",                  "Compliance review queue (HTML)"),
        ("GET",  f"{BASE_URL}/health",                      "Health + LLM status"),
        ("GET",  f"{BASE_URL}/docs",                        "Swagger UI"),
    ]
    for method, url, desc in api_rows:
        api.add_row(method, url, desc)
    console.print(api)
    console.print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Jura demo launcher")
    parser.add_argument("--demo", action="store_true", help="Open browser at /docs after start")
    args = parser.parse_args()

    managed_proc: subprocess.Popen | None = None

    if _is_running():
        console.print(f"[green]✓[/green] Jura already running on port {JURA_PORT}")
    else:
        console.print(f"[yellow]⟳[/yellow] Starting Jura on port {JURA_PORT} …")
        managed_proc = _start_server()
        if not _wait_for_server(timeout=20):
            console.print("[red]✗ Server failed to start within 20s. Run manually:[/red]")
            console.print(f"  [dim]uvicorn jura.server:app --port {JURA_PORT}[/dim]")
            sys.exit(1)
        console.print(f"[green]✓[/green] Server started (pid {managed_proc.pid})")

    _print_endpoints()

    if args.demo:
        url = f"{BASE_URL}/docs"
        console.print(f"[cyan]Opening browser → {url}[/cyan]")
        webbrowser.open(url)
        console.print()
        console.print(Panel(
            f"[bold]Jura running[/bold]\n\n"
            f"  Swagger UI:  {BASE_URL}/docs\n"
            f"  Intake:      {BASE_URL}/intake/upload\n"
            f"  Compliance:  {BASE_URL}/compliance\n"
            f"  Health:      {BASE_URL}/health\n\n"
            "[dim]Upload a PDF/DOCX to /intake/upload to begin.\nPress Ctrl-C to stop.[/dim]",
            title="Jura",
            border_style="cyan",
        ))
        try:
            if managed_proc:
                managed_proc.wait()
            else:
                while True:
                    time.sleep(60)
        except KeyboardInterrupt:
            console.print("\n[dim]Shutting down.[/dim]")
            if managed_proc:
                managed_proc.terminate()


if __name__ == "__main__":
    main()
