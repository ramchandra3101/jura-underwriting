from __future__ import annotations

import asyncio
import io
import json
import os
from typing import Any

from google import genai
from google.genai import types

_SEM = asyncio.Semaphore(5)

_PROMPT = """\
You are extracting structured fields from a commercial insurance submission document \
(typically an ACORD form packet: ACORD 125 general application + ACORD 140 property section).

Return ONLY a valid JSON object with exactly these keys — no markdown, no extra text:

{
  "insured_name": string,
  "state": string,
  "zip_code": string,
  "sic_code": string,
  "tiv": number,
  "credit_score_used": boolean,
  "new_business": boolean
}

Extraction rules:
- insured_name: Named insured / applicant name on the form
- state: 2-letter writing/premises state abbreviation (e.g. "NY", "FL", "CA")
- zip_code: 5-digit premises ZIP code as a string, preserve leading zeros
- sic_code: 4-digit SIC code as a string
- tiv: Total Insured Value in dollars — sum building + BPP + business income limits if \
itemized; use the TIV field directly if present
- credit_score_used: true only if document explicitly states credit score was used in \
pricing; default false
- new_business: true if "New Business" or "New" checkbox is marked; false if "Renewal"

Use null for any string field not found. Use 0.0 for tiv if not found.
"""


def _client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")
    return genai.Client(api_key=key)


def _parse(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    return json.loads(text.strip())


async def extract_from_pdf(pdf_bytes: bytes, filename: str) -> dict[str, Any]:
    async with _SEM:
        client = _client()
        file_ref = await client.aio.files.upload(
            file=io.BytesIO(pdf_bytes),
            config=types.UploadFileConfig(
                mime_type="application/pdf",
                display_name=filename,
            ),
        )
        try:
            response = await client.aio.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    types.Part.from_uri(file_uri=file_ref.uri, mime_type="application/pdf"),
                    _PROMPT,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            return _parse(response.text)
        finally:
            await client.aio.files.delete(name=file_ref.name)


async def extract_from_text(text: str, filename: str) -> dict[str, Any]:
    # Guard 4: scan DOCX text for injection before sending to Gemini
    from intake.guards import scan_for_injection
    injection = scan_for_injection(text)
    if not injection.passed:
        raise ValueError(f"Injection detected in {filename!r}: {'; '.join(injection.errors)}")

    async with _SEM:
        client = _client()
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"{_PROMPT}\n\nDocument content:\n{text}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return _parse(response.text)
