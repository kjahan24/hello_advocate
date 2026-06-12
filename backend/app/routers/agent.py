"""Agent router — Claude tool_use agentic loop.

POST /api/agent/chat
"""
from __future__ import annotations

import json
from typing import Any

import structlog
from anthropic import AsyncAnthropic
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.agent_tools import dispatch_tool

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])

_client = AsyncAnthropic()

# ──────────────────────────────────────────────────────────────────────────────
# System prompts
# ──────────────────────────────────────────────────────────────────────────────

_SYSTEM_BN = """আপনি বাংলাদেশের একজন বিশেষজ্ঞ AI আইনি সহকারী। আপনার কাছে বিভিন্ন tools আছে \
যা দিয়ে আপনি বাংলাদেশের আইন অনুসন্ধান, আদালতের তথ্য, সময়সীমা গণনা এবং \
আইনি যোগ্যতা যাচাই করতে পারেন।

জটিল প্রশ্নের জন্য প্রয়োজনীয় tools ব্যবহার করুন। প্রতিটি উত্তরে:
১. সরাসরি উত্তর দিন
২. প্রাসঙ্গিক আইন ও ধারার উল্লেখ করুন
৩. ব্যবহারিক পরবর্তী পদক্ষেপ বলুন
৪. বাংলায় স্পষ্ট ও সহজ ভাষায় উত্তর দিন

⚠️ সর্বদা শেষে এই disclaimer যোগ করুন:
"এটি AI-সহায়তা, আইনি পরামর্শ নয়। গুরুত্বপূর্ণ বিষয়ে যোগ্য আইনজীবীর সাথে পরামর্শ করুন।"
"""

_SYSTEM_EN = """You are an expert AI legal assistant specializing in Bangladesh law. \
You have access to tools that let you search Bangladesh laws, get court information, \
calculate legal deadlines, and check legal eligibility.

Use the appropriate tools for complex questions. For each answer:
1. Give a direct answer
2. Cite the relevant Act and Section
3. Suggest practical next steps
4. Use clear, plain language

⚠️ Always end with: "This is AI assistance, not legal advice. \
For important matters, consult a qualified lawyer."
"""

# ──────────────────────────────────────────────────────────────────────────────
# Tool definitions (Anthropic format)
# ──────────────────────────────────────────────────────────────────────────────

TOOLS: list[dict[str, Any]] = [
    {
        "name":        "search_laws",
        "description": "Search Bangladesh laws and sections by keyword. Use when the user asks about a specific legal topic or wants to know which law covers their situation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type":        "string",
                    "description": "The legal topic or keyword to search for",
                },
                "limit": {
                    "type":        "integer",
                    "description": "Maximum number of results to return (default 5)",
                    "default":     5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name":        "get_law_details",
        "description": "Get full details of a specific Bangladesh law by name, including year, category, and total sections.",
        "input_schema": {
            "type": "object",
            "properties": {
                "law_name": {
                    "type":        "string",
                    "description": "Name or partial name of the Bangladesh law",
                },
            },
            "required": ["law_name"],
        },
    },
    {
        "name":        "search_legal_templates",
        "description": "Find legal document templates relevant to a query. Use when the user needs a legal document or form.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type":        "string",
                    "description": "Type of legal document needed",
                },
                "category": {
                    "type":        "string",
                    "description": "Category filter: land, family, business, labor, consumer, or all",
                    "default":     "all",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name":        "calculate_legal_deadline",
        "description": "Calculate legal deadlines and important dates under Bangladesh law. Use when the user asks about time limits for filing cases or appeals.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_type": {
                    "type":        "string",
                    "description": "Type of legal event: appeal, limitation_contract, limitation_tort, cheque_dishonor, labor_complaint, consumer_complaint, land_dispute",
                },
                "start_date": {
                    "type":        "string",
                    "description": "Start date in YYYY-MM-DD format",
                },
                "jurisdiction": {
                    "type":        "string",
                    "description": "Jurisdiction (default: bangladesh)",
                    "default":     "bangladesh",
                },
            },
            "required": ["event_type", "start_date"],
        },
    },
    {
        "name":        "get_court_info",
        "description": "Get information about Bangladesh courts, their jurisdiction, location, and filing fees.",
        "input_schema": {
            "type": "object",
            "properties": {
                "court_type": {
                    "type":        "string",
                    "description": "Type of court: supreme, high_court, district, sessions, magistrate, labour, family, administrative",
                },
                "district": {
                    "type":        "string",
                    "description": "District name (default: dhaka)",
                    "default":     "dhaka",
                },
            },
            "required": ["court_type"],
        },
    },
    {
        "name":        "check_legal_eligibility",
        "description": "Check eligibility for legal actions like bail, appeal, or legal aid under Bangladesh law.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action_type": {
                    "type":        "string",
                    "description": "Type of legal action: bail, appeal, legal_aid",
                },
                "case_details": {
                    "type":        "object",
                    "description": "Details relevant to the eligibility check (offense, days_since_judgment, monthly_income, etc.)",
                },
            },
            "required": ["action_type", "case_details"],
        },
    },
]

# ──────────────────────────────────────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────────────────────────────────────

class ConversationMessage(BaseModel):
    role:    str
    content: str


class AgentChatRequest(BaseModel):
    message:              str
    language:             str = Field(default="bn", pattern="^(bn|en)$")
    conversation_history: list[ConversationMessage] = []


class ToolUsed(BaseModel):
    name:   str
    input:  dict[str, Any]
    result: dict[str, Any]


class AgentChatResponse(BaseModel):
    response:   str
    tools_used: list[ToolUsed]
    language:   str


# ──────────────────────────────────────────────────────────────────────────────
# Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    request: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
) -> AgentChatResponse:
    """Agentic loop: Claude selects tools, we execute them, Claude writes final answer."""
    system_prompt = _SYSTEM_BN if request.language == "bn" else _SYSTEM_EN

    # Build message history
    messages: list[dict[str, Any]] = []
    for msg in request.conversation_history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})

    tools_used: list[ToolUsed] = []
    max_iterations = 5  # prevent infinite loops

    for _ in range(max_iterations):
        response = await _client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2048,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        # Check stop reason
        if response.stop_reason == "end_turn":
            # Extract text from response
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text
            return AgentChatResponse(
                response=final_text,
                tools_used=tools_used,
                language=request.language,
            )

        if response.stop_reason != "tool_use":
            # Unexpected stop — return whatever text we have
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text
            return AgentChatResponse(
                response=final_text or "দুঃখিত, উত্তর তৈরি করতে সমস্যা হয়েছে।",
                tools_used=tools_used,
                language=request.language,
            )

        # Process tool_use blocks
        tool_results: list[dict[str, Any]] = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            tool_input  = block.input if isinstance(block.input, dict) else {}
            tool_result = await dispatch_tool(block.name, tool_input, db=db)
            tools_used.append(ToolUsed(
                name=block.name,
                input=tool_input,
                result=tool_result,
            ))
            tool_results.append({
                "type":        "tool_result",
                "tool_use_id": block.id,
                "content":     json.dumps(tool_result, ensure_ascii=False),
            })
            logger.info("tool_executed", tool=block.name, input_keys=list(tool_input.keys()))

        # Append assistant turn + tool results to message history
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    # Fallback after max iterations
    return AgentChatResponse(
        response="দুঃখিত, উত্তর তৈরিতে সমস্যা হয়েছে। আবার চেষ্টা করুন।",
        tools_used=tools_used,
        language=request.language,
    )
