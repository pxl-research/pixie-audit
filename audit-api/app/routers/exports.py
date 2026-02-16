from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO
from typing import cast
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from openpyxl import Workbook

from app.auth import require_read_auth

router = APIRouter(dependencies=[Depends(require_read_auth)])

EXPORT_WORKSHEET_NAME = "Conversaties"
EXPORT_HEADERS = (
    "Conversatie ID",
    "Profiel",
    "Locatie",
    "Gestart op",
    "Beeindigd op",
    "Aantal berichten",
    "Samenvatting",
    "Volledig gesprek",
)
DISPLAY_TIMEZONE = ZoneInfo("Europe/Brussels")
SAFE_DIALOGUE_ROLES = {"user", "assistant", "system"}
FORMULA_PREFIXES = ("=", "+", "-", "@")


def _format_timestamp(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    localized = value.astimezone(DISPLAY_TIMEZONE)
    return localized.strftime("%Y-%m-%d %H:%M:%S")


def _escape_excel_text(value: str) -> str:
    stripped = value.lstrip()
    if stripped and stripped[0] in FORMULA_PREFIXES:
        return "'" + value
    return value


def _safe_cell_text(value: object | None) -> str:
    if value is None:
        return ""
    return _escape_excel_text(str(value))


def _conversation_location(metadata: object) -> str:
    if not isinstance(metadata, dict):
        return ""
    metadata_dict = cast(dict[str, object], metadata)
    raw_location = metadata_dict.get("location")
    if not isinstance(raw_location, str):
        return ""
    return raw_location.strip()


@router.get("/exports/logs.xlsx")
async def export_logs(request: Request) -> Response:
    pool = request.app.state.db
    async with pool.acquire() as conn:
        conversation_rows = await conn.fetch(
            "select id, profile, started_at, ended_at, metadata "
            "from audit.conversations "
            "order by started_at desc, id desc"
        )
        conversations = [dict(row) for row in conversation_rows]

        conversation_ids = [str(row["id"]) for row in conversations]
        messages: list[dict[str, object]] = []
        if conversation_ids:
            message_rows = await conn.fetch(
                "select id::text as id, conversation_id, role, content, created_at "
                "from audit.messages "
                "where conversation_id = any($1::text[]) "
                "order by conversation_id asc, created_at asc, id asc",
                conversation_ids,
            )
            messages = [dict(row) for row in message_rows]

    latest_summary_by_conversation: dict[str, str] = {}
    dialogue_lines_by_conversation: defaultdict[str, list[str]] = defaultdict(list)
    dialogue_count_by_conversation: defaultdict[str, int] = defaultdict(int)
    for message in messages:
        conversation_id = str(message["conversation_id"])
        role = str(message["role"])
        content = str(message["content"])
        created_at = message["created_at"]
        created_at_text = _format_timestamp(
            created_at if isinstance(created_at, datetime) else None
        )

        if role == "summary":
            latest_summary_by_conversation[conversation_id] = content
            continue

        if role not in SAFE_DIALOGUE_ROLES:
            continue

        dialogue_count_by_conversation[conversation_id] += 1
        dialogue_lines_by_conversation[conversation_id].append(
            f"[{created_at_text}] {role}: {content}"
        )

    workbook = Workbook(write_only=True)
    worksheet = workbook.create_sheet(title=EXPORT_WORKSHEET_NAME)
    worksheet.append(EXPORT_HEADERS)

    for conversation in conversations:
        conversation_id = str(conversation["id"])
        profile = _safe_cell_text(conversation["profile"])
        location = _safe_cell_text(_conversation_location(conversation["metadata"]))
        started_at_value = conversation.get("started_at")
        ended_at_value = conversation.get("ended_at")
        started_at = _safe_cell_text(
            _format_timestamp(
                started_at_value if isinstance(started_at_value, datetime) else None
            )
        )
        ended_at = _safe_cell_text(
            _format_timestamp(
                ended_at_value if isinstance(ended_at_value, datetime) else None
            )
        )
        message_count = dialogue_count_by_conversation.get(conversation_id, 0)
        summary = _safe_cell_text(
            latest_summary_by_conversation.get(conversation_id, "")
        )
        transcript = _safe_cell_text(
            "\n".join(dialogue_lines_by_conversation.get(conversation_id, []))
        )

        worksheet.append(
            (
                _safe_cell_text(conversation_id),
                profile,
                location,
                started_at,
                ended_at,
                message_count,
                summary,
                transcript,
            )
        )

    payload = BytesIO()
    workbook.save(payload)
    workbook.close()
    payload.seek(0)

    generated_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"pixie-audit-export-{generated_at}.xlsx"

    return Response(
        content=payload.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
