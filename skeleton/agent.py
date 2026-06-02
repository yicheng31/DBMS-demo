<<<<<<< Updated upstream
=======

>>>>>>> Stashed changes
# TASK 6 EXTENSION: added get_user_profile and get_payment_info tools,
# Chinese keyword support, booking confirmation gate, human-friendly prompts,
# stronger fallback logic, greeting protection, Chinese policy query translation,
# pre-classification for tool routing, automatic date extraction, multi-step chaining,
# booking confirmation context recovery, cancel vs policy classification fix,
# pre-login check, ticket type extraction, seat preference detection
"""
TransitFlow — Intelligent Agent (v4 final)
============================================
OPTIMIZATIONS:
  1.  Chinese keyword & station name support (30 mappings)
  2.  Added get_user_profile and get_payment_info tools
  3.  Human-friendly system prompt and error messages
  4.  Booking confirmation with context recovery from history
  5.  Structured, emoji-enhanced response formatting
  6.  Stronger fallback: overrides wrong tool selections
  7.  Greeting protection: skip tool calls for simple greetings
  8.  Chinese policy query translation for vector search
  9.  Pre-classification: categorize query BEFORE LLM (14→2-4 tools)
  10. Automatic date extraction from natural language
  11. Multi-step chaining: booking queries auto-call availability+fare+seats
  12. Cancel vs policy smart classification
  13. Pre-login check: prompt login BEFORE running booking chain
  14. Ticket type extraction (single/return)
  15. Seat preference extraction (window/aisle)
  16. Multi-schedule selection: list options for user to choose
  17. Stronger confirmation message format in SYSTEM_PROMPT
  18. Station ID deduplication (BUG FIX #1)
  19. Booking context recovery uses correct search order (BUG FIX #2)
  20. Fare class extracted from USER messages only (BUG FIX #3)
  21. Continuation dialog detection from history (BUG FIX #4)
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Optional

<<<<<<< Updated upstream
from skeleton.llm_provider import llm
=======
<<<<<<< HEAD
from databases.graph.queries import (
    query_alternative_routes,
    query_cheapest_route,
    query_delay_ripple,
    query_interchange_path,
    query_shortest_route,
    query_station_connections,
)
=======
from skeleton.llm_provider import llm
>>>>>>> 4836b765bf1e177ac0fef698aec75593eac5dcd5
>>>>>>> Stashed changes
from databases.relational.queries import (
    query_national_rail_availability,
    query_national_rail_fare,
    query_metro_schedules,
    query_metro_fare,
    query_available_seats,
    auto_select_adjacent_seats,
    query_user_profile,
    query_user_bookings,
    query_payment_info,
    execute_booking,
    execute_cancellation,
    query_policy_vector_search,
)
from databases.graph.queries import (
    query_shortest_route,
    query_cheapest_route,
    query_alternative_routes,
    query_interchange_path,
    query_delay_ripple,
)


# ── Station name → ID lookup ─────────────────────────────────────────────────

_STATION_INDEX: dict[str, str] = {
    "central square": "MS01", "riverside": "MS02", "northgate": "MS03",
    "elm park": "MS04", "westfield": "MS05", "harbour view": "MS06",
    "old town": "MS07", "university": "MS08", "queensbridge": "MS09",
    "parkside": "MS10", "greenhill": "MS11", "lakeshore": "MS12",
    "clifton": "MS13", "eastwick": "MS14", "ferndale": "MS15",
    "hilltop": "MS16", "broadmoor": "MS17", "sunnyvale": "MS18",
    "redwood": "MS19", "thornton": "MS20",
    "中央廣場": "MS01", "河濱站": "MS02", "北門站": "MS03",
    "榆樹公園站": "MS04", "西田站": "MS05", "海港景站": "MS06",
    "舊城站": "MS07", "大學站": "MS08", "皇后橋站": "MS09",
    "公園側站": "MS10", "綠丘站": "MS11", "湖岸站": "MS12",
    "克利夫頓站": "MS13", "東威克站": "MS14", "芬戴爾站": "MS15",
    "山頂站": "MS16", "寬地站": "MS17", "陽光谷站": "MS18",
    "紅木站": "MS19", "桑頓站": "MS20",
    "central station": "NR01", "maplewood": "NR02",
    "old town junction": "NR03", "ashford": "NR04",
    "stonehaven": "NR05", "bridgeport": "NR06",
    "ferndale halt": "NR07", "coalport": "NR08",
    "dunmore": "NR09", "langford end": "NR10",
    "中央站": "NR01", "楓木站": "NR02",
    "舊城交匯站": "NR03", "阿什福德站": "NR04",
    "石港站": "NR05", "橋港站": "NR06",
    "芬戴爾停靠站": "NR07", "煤港站": "NR08",
    "丹摩站": "NR09", "蘭福德終點站": "NR10",
}

_POLICY_TRANSLATION: dict[str, str] = {
    "退款": "refund cancellation policy", "退票": "refund cancellation policy",
    "取消": "cancellation refund policy", "補償": "delay compensation policy",
    "延誤": "delay compensation policy", "誤點": "delay compensation policy",
    "行李": "luggage baggage policy", "寵物": "pet animal travel policy",
    "腳踏車": "bicycle bike travel policy", "自行車": "bicycle bike travel policy",
    "兒童": "child fare discount policy", "小孩": "child fare discount policy",
    "票種": "ticket types single return day pass", "票價": "fare pricing ticket cost",
    "規定": "rules policy regulations", "政策": "company policy rules",
    "食物": "food drink policy onboard", "飲料": "food drink policy onboard",
    "逃票": "fare evasion penalty", "罰款": "fare evasion penalty",
    "訂票規則": "booking rules policy",
}


def _translate_policy_query(query: str) -> str:
    translations = [en for zh, en in _POLICY_TRANSLATION.items() if zh in query]
    return " ".join(translations) if translations else query


def _inject_station_ids(text: str) -> str:
    result = text
    seen_ids: set[str] = set()
    for name in sorted(_STATION_INDEX, key=len, reverse=True):
        sid = _STATION_INDEX[name]
        if sid in seen_ids:
            continue
        pattern = re.compile(re.escape(name), re.IGNORECASE)
        if pattern.search(result):
            result = pattern.sub(f"{name} ({sid})", result)
            seen_ids.add(sid)
    return result


<<<<<<< Updated upstream
# ── Detection helpers ─────────────────────────────────────────────────────────

_GREETING_PATTERNS = {
    "你好", "您好", "嗨", "哈囉", "早安", "午安", "晚安",
    "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
    "howdy", "greetings", "yo", "sup",
}

_CONFIRM_WORDS = [
    "confirm", "yes", "ok", "sure", "go ahead", "do it",
    "確認", "确认", "好", "好的", "沒問題", "没问题",
    "訂吧", "訂了", "订吧", "订了", "對", "对", "是",
    "可以", "沒錯", "没错", "就這樣", "就这样",
]


def _is_greeting(text: str) -> bool:
    clean = text.strip().lower().rstrip("!！。.~")
    if clean in _GREETING_PATTERNS:
        return True
    if len(clean) < 10:
        for g in _GREETING_PATTERNS:
            if clean.startswith(g):
                return True
    return False


def _is_confirmation(text: str) -> bool:
    """
    Check if message is a booking confirmation.
    Uses RAW user message to avoid encoding issues.
    """
    clean = text.strip().rstrip("!！。.~,，")
    # Exact match
    if clean.lower() in [w.lower() for w in _CONFIRM_WORDS]:
        return True
    if clean in _CONFIRM_WORDS:
        return True
    # Short message containing confirm word
    if len(clean) < 20:
        for w in _CONFIRM_WORDS:
            if w in clean or w in clean.lower():
                return True
    return False


def _extract_date(text: str) -> Optional[str]:
    match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
    if match:
        return match.group(1)
    match = re.search(r'(\d{4})/(\d{2})/(\d{2})', text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return None


# BUG FIX #1: Deduplicate station IDs while preserving order.
# Before: "Bridgeport NR06 到 Central Station NR01" after injection became
# "Bridgeport (NR06) NR06 到 Central Station (NR01) NR01"
# → [NR06, NR06, NR01, NR01] → station_ids[1] = NR06 (WRONG!)
# After: [NR06, NR01] → station_ids[1] = NR01 (CORRECT!)
def _extract_station_ids(text: str) -> list[str]:
    """Extract unique station IDs preserving first-occurrence order."""
=======
<<<<<<< HEAD
def _unique_preserve_order(values: list[str]) -> list[str]:
>>>>>>> Stashed changes
    seen = set()
    result = []
    for sid in re.findall(r'(MS\d{2}|NR\d{2})', text, re.IGNORECASE):
        upper = sid.upper()
        if upper not in seen:
            seen.add(upper)
            result.append(upper)
    return result


<<<<<<< Updated upstream
def _extract_ticket_type(text: str) -> str:
    lower = text.lower()
    if any(kw in lower for kw in ["return", "round trip", "來回", "來回票", "往返"]):
        return "return"
    return "single"

=======
SYSTEM_PROMPT = """You are TransitFlow, a friendly and patient transit assistant for a dual-network system.
=======
# ── Detection helpers ─────────────────────────────────────────────────────────
>>>>>>> 4836b765bf1e177ac0fef698aec75593eac5dcd5

_GREETING_PATTERNS = {
    "你好", "您好", "嗨", "哈囉", "早安", "午安", "晚安",
    "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
    "howdy", "greetings", "yo", "sup",
}

_CONFIRM_WORDS = [
    "confirm", "yes", "ok", "sure", "go ahead", "do it",
    "確認", "确认", "好", "好的", "沒問題", "没问题",
    "訂吧", "訂了", "订吧", "订了", "對", "对", "是",
    "可以", "沒錯", "没错", "就這樣", "就这样",
]


def _is_greeting(text: str) -> bool:
    clean = text.strip().lower().rstrip("!！。.~")
    if clean in _GREETING_PATTERNS:
        return True
    if len(clean) < 10:
        for g in _GREETING_PATTERNS:
            if clean.startswith(g):
                return True
    return False


def _is_confirmation(text: str) -> bool:
    """
    Check if message is a booking confirmation.
    Uses RAW user message to avoid encoding issues.
    """
    clean = text.strip().rstrip("!！。.~,，")
    # Exact match
    if clean.lower() in [w.lower() for w in _CONFIRM_WORDS]:
        return True
    if clean in _CONFIRM_WORDS:
        return True
    # Short message containing confirm word
    if len(clean) < 20:
        for w in _CONFIRM_WORDS:
            if w in clean or w in clean.lower():
                return True
    return False


def _extract_date(text: str) -> Optional[str]:
    match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
    if match:
        return match.group(1)
    match = re.search(r'(\d{4})/(\d{2})/(\d{2})', text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return None


# BUG FIX #1: Deduplicate station IDs while preserving order.
# Before: "Bridgeport NR06 到 Central Station NR01" after injection became
# "Bridgeport (NR06) NR06 到 Central Station (NR01) NR01"
# → [NR06, NR06, NR01, NR01] → station_ids[1] = NR06 (WRONG!)
# After: [NR06, NR01] → station_ids[1] = NR01 (CORRECT!)
def _extract_station_ids(text: str) -> list[str]:
    """Extract unique station IDs preserving first-occurrence order."""
    seen = set()
    result = []
    for sid in re.findall(r'(MS\d{2}|NR\d{2})', text, re.IGNORECASE):
        upper = sid.upper()
        if upper not in seen:
            seen.add(upper)
            result.append(upper)
    return result


def _extract_ticket_type(text: str) -> str:
    lower = text.lower()
    if any(kw in lower for kw in ["return", "round trip", "來回", "來回票", "往返"]):
        return "return"
    return "single"

>>>>>>> Stashed changes

def _extract_seat_preference(text: str) -> Optional[str]:
    lower = text.lower()
    if any(kw in lower for kw in ["window", "靠窗", "窗邊", "窗戶"]):
        return "window"
    if any(kw in lower for kw in ["aisle", "走道", "靠走道"]):
        return "aisle"
    return None


def _extract_fare_class(text: str) -> str:
    lower = text.lower()
    if any(kw in lower for kw in ["first class", "first", "頭等", "商務", "一等"]):
        return "first"
    return "standard"


# ── Pre-classification ────────────────────────────────────────────────────────

def _pre_classify_query(text: str, station_ids: list[str], has_date: bool,
                        current_user_email: Optional[str]) -> str:
    lower = text.lower()
    two_stations = len(station_ids) >= 2
    is_cross = two_stations and station_ids[0][:2] != station_ids[1][:2]

    route_kw = {
        "fastest", "quickest", "shortest", "cheapest", "route", "path",
        "directions", "how to get", "how do i get", "way from",
        "最快", "最短", "最便宜", "怎麼去", "如何前往", "怎麼走",
        "如何去", "如何搭", "怎麼搭", "路線", "轉乘",
    }
    booking_kw = {
        "book", "booking", "ticket", "seat", "buy", "purchase", "reserve",
        "訂票", "訂位", "買票", "座位", "訂", "購買", "靠窗", "first class",
        "standard", "single ticket", "return ticket",
    }
    avail_kw = {
        "train", "trains", "schedule", "timetable", "service", "services",
        "available", "availability", "what runs", "are there",
        "班次", "時刻表", "列車", "有沒有車", "幾點有車", "有哪些",
        "哪些班次", "查車",
    }
    fare_kw = {"fare", "price", "cost", "how much", "票價", "多少錢", "價格", "費用"}
    policy_kw = {
        "refund", "policy", "compensation", "luggage", "bicycle", "pet",
        "conduct", "rules", "regulation",
        "退款", "補償", "政策", "行李", "寵物", "腳踏車", "規定",
        "延誤", "誤點", "逃票", "罰款",
    }
    personal_kw = {
        "my booking", "my ticket", "my trip", "my account", "my profile",
        "show my", "view my", "my history",
        "我的訂票", "我的票", "我的帳號", "我的資料", "訂票紀錄",
    }
    cancel_kw = {"cancel", "cancellation", "取消", "退訂"}
    delay_kw = {"delay", "disruption", "closed", "affected", "ripple",
                "延誤", "關閉", "影響"}
    policy_override_kw = {
        "多少", "政策", "如何", "怎麼", "可以退", "退多少", "規定",
        "how much", "what is", "what's", "policy", "refund amount",
    }

    if is_cross and two_stations:
        return "route"
    if any(kw in lower for kw in route_kw) and two_stations:
        return "route"
    if any(kw in lower for kw in cancel_kw):
        if any(kw in lower for kw in policy_override_kw) or any(kw in lower for kw in policy_kw):
            return "policy"
        return "cancel"
    if any(kw in lower for kw in booking_kw) and two_stations:
        return "booking"
    if any(kw in lower for kw in fare_kw) and two_stations:
        return "fare"
    if any(kw in lower for kw in avail_kw) and two_stations:
        return "availability"
    if two_stations:
        return "availability"
    if any(kw in lower for kw in policy_kw):
        return "policy"
    if any(kw in lower for kw in personal_kw):
        return "personal"
    if any(kw in lower for kw in delay_kw):
        return "delay"
    return "general"


_CATEGORY_TOOLS: dict[str, list[str]] = {
    "route": ["find_route", "find_alternative_routes"],
    "availability": ["check_national_rail_availability", "check_metro_availability"],
    "booking": ["check_national_rail_availability", "get_available_seats",
                "get_national_rail_fare", "make_booking"],
    "fare": ["get_national_rail_fare", "get_metro_fare", "calculate_metro_fare",
             "check_national_rail_availability", "check_metro_availability"],
    "policy": ["search_policy"],
    "personal": ["get_user_bookings", "get_user_profile", "get_payment_info"],
    "cancel": ["cancel_booking", "get_user_bookings"],
    "delay": ["get_delay_ripple"],
    "general": [],
}


def _filter_tools(tools: list[dict], category: str) -> list[dict]:
    allowed = _CATEGORY_TOOLS.get(category)
    if allowed is None:
        return tools
    return [t for t in tools if t["name"] in allowed]


# ── Booking context recovery ─────────────────────────────────────────────────
# BUG FIX #2: Removed `reversed` so schedule_id search finds the FIRST
# (correct) schedule, not a later wrong one.
# BUG FIX #3: Extract fare_class from USER messages only, not from AI
# responses (which may contain "first" in descriptions of other options).

def _recover_booking_context(history: list[dict]) -> Optional[dict]:
    """Recover booking details from conversation history."""
    # Collect USER messages only (for preferences like fare_class)
    user_text = ""
    for msg in history[-10:]:
        if msg.get("role") == "user":
            user_text += " " + msg.get("content", "")

    # Collect ALL messages (for schedule_id, station_ids, dates)
    # BUG FIX #2: forward order, not reversed
    all_text = ""
    for msg in history[-10:]:
        all_text += " " + msg.get("content", "")

    # Schedule ID is required
    schedule_match = re.search(r'(NR_SCH\d+|MS_SCH\d+)', all_text)
    if not schedule_match:
        return None

    # Station IDs (deduplicated)
    station_ids = _extract_station_ids(all_text)
    if len(station_ids) < 2:
        return None

    # Date from all text
    travel_date = _extract_date(all_text)

    # BUG FIX #3: fare_class from USER messages only
    fare_class = _extract_fare_class(user_text)
    ticket_type = _extract_ticket_type(user_text)

    # Seat ID if user mentioned one
    seat_match = re.search(r'\b([AB]\d{2})\b', user_text)
    seat_id = seat_match.group(1) if seat_match else "any"

    return {
        "schedule_id": schedule_match.group(1),
        "origin_station_id": station_ids[0],
        "destination_station_id": station_ids[1],
        "travel_date": travel_date or date.today().isoformat(),
        "fare_class": fare_class,
        "seat_id": seat_id,
        "ticket_type": ticket_type,
    }


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are TransitFlow, a friendly transit assistant.

Networks: City Metro MS01-MS20 (M1-M4) | National Rail NR01-NR10 (NR1-NR2)
Interchanges: Central=MS01/NR01 | Old Town=MS07/NR03 | Ferndale=MS15/NR07
Today: {today}

PERSONALITY: Warm, helpful, patient. Never show raw errors. Always offer to help more.

RESPONSE FORMAT: Use emojis (🚂🚇💰💺🗺️📋). Keep concise but complete.

BOOKING CONFIRMATION (CRITICAL):
When showing booking details, ALWAYS use this format:
  📋 訂票摘要：
  🚂 路線：[origin] ([origin_id]) → [dest] ([dest_id])
  🔢 班次：[schedule_id]
  📅 日期：[date]
  🎫 票種：[ticket_type]
  💺 等級：[fare_class]
  💰 票價：$[fare]
  🪑 座位：[seat_id]
  請回覆「確認」以完成訂票。

MULTI-SCHEDULE: When multiple schedules found, list ALL with numbers for user to choose.

LOGIN RULE: Only make_booking and cancel_booking need login.

Use DATA FROM TRANSITFLOW DATABASE as the only source of truth. Never invent data.
Always reply in the same language as the user.
""".format(today=date.today().isoformat())


# ── Tool definitions ──────────────────────────────────────────────────────────

TOOLS = [
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
    {
        "name": "check_national_rail_availability",
        "description": (
            "Check available national rail trains and services between two stations. "
            "Use for schedules, timetables, or availability."
        ),
        "parameters": {
            "origin_id": {"type": "string", "description": "National rail station ID e.g. NR01"},
            "destination_id": {"type": "string", "description": "National rail station ID e.g. NR05"},
            "travel_date": {"type": "string", "description": "YYYY-MM-DD, optional"},
        },
        "required": ["origin_id", "destination_id"],
    },
    {
        "name": "get_national_rail_fare",
        "description": "Calculate the fare for a national rail journey on a specific schedule.",
        "parameters": {
            "schedule_id": {"type": "string", "description": "e.g. NR_SCH01"},
            "fare_class": {"type": "string", "description": "standard or first"},
            "stops_travelled": {"type": "integer", "description": "Number of stops"},
        },
        "required": ["schedule_id", "fare_class", "stops_travelled"],
    },
    {
        "name": "get_national_rail_schedule_fares",
        "description": (
            "Get all ticket prices for a national rail schedule id when the user asks "
            "for the price of a service such as NR_SCH04."
        ),
        "parameters": {
            "schedule_id": {"type": "string", "description": "e.g. NR_SCH04"},
        },
        "required": ["schedule_id"],
    },
    {
        "name": "get_national_rail_journey_fares",
        "description": (
            "Get national rail fares between two national rail stations. "
            "Use when the user asks the price, cost, or fare from one NR station to another."
        ),
        "parameters": {
            "origin_id": {"type": "string", "description": "National rail station ID e.g. NR01"},
            "destination_id": {"type": "string", "description": "National rail station ID e.g. NR05"},
            "travel_date": {"type": "string", "description": "YYYY-MM-DD, optional"},
            "fare_class": {"type": "string", "description": "standard, first, or all"},
        },
        "required": ["origin_id", "destination_id"],
    },
    {
        "name": "check_metro_availability",
        "description": "Check available metro services between two metro stations.",
        "parameters": {
            "origin_id": {"type": "string", "description": "Metro station ID e.g. MS01"},
            "destination_id": {"type": "string", "description": "Metro station ID e.g. MS09"},
        },
        "required": ["origin_id", "destination_id"],
    },
    {
        "name": "calculate_metro_fare",
        "description": "Calculate the metro single-ticket fare for a journey.",
        "parameters": {
            "schedule_id": {"type": "string", "description": "e.g. MS_SCH01"},
            "stops_travelled": {"type": "integer", "description": "Number of stops"},
        },
        "required": ["schedule_id", "stops_travelled"],
    },
    {
        "name": "get_metro_fare",
        "description": (
            "Get the metro ticket price between two stations. "
            "Use for fare/price/cost questions, not route questions."
        ),
        "parameters": {
            "origin_id": {"type": "string", "description": "Metro station ID e.g. MS01"},
            "destination_id": {"type": "string", "description": "Metro station ID e.g. MS09"},
        },
        "required": ["origin_id", "destination_id"],
    },
    {
        "name": "get_user_bookings",
        "description": "Retrieve the logged-in user's full booking history.",
        "parameters": {},
        "required": [],
    },
    {
        "name": "get_user_profile",
        "description": "Retrieve the logged-in user's profile information.",
        "parameters": {},
        "required": [],
    },
    {
        "name": "get_payment_info",
        "description": "Retrieve payment details for a specific booking or metro trip.",
        "parameters": {
            "booking_id": {"type": "string", "description": "Booking or trip ID e.g. BK-A1B2C3"},
        },
        "required": ["booking_id"],
    },
    {
        "name": "get_available_seats",
        "description": "Show available seats on a national rail service.",
        "parameters": {
            "schedule_id": {"type": "string", "description": "e.g. NR_SCH01"},
            "travel_date": {"type": "string", "description": "YYYY-MM-DD"},
            "fare_class": {"type": "string", "description": "standard or first"},
        },
        "required": ["schedule_id", "travel_date", "fare_class"],
    },
    {
        "name": "booking_preflight",
        "description": (
            "Check national rail availability, fare, and seats before booking. "
            "Use for booking requests before the user explicitly confirms."
        ),
        "parameters": {
            "schedule_id": {"type": "string", "description": "e.g. NR_SCH01, optional"},
            "origin_station_id": {"type": "string", "description": "e.g. NR01"},
            "destination_station_id": {"type": "string", "description": "e.g. NR05"},
            "travel_date": {"type": "string", "description": "YYYY-MM-DD"},
            "fare_class": {"type": "string", "description": "standard or first"},
            "seat_id": {"type": "string", "description": "Seat ID or any, optional"},
            "ticket_type": {"type": "string", "description": "single or return"},
        },
        "required": ["origin_station_id", "destination_station_id", "travel_date", "fare_class"],
    },
    {
        "name": "make_booking",
        "description": "Create a national rail booking for the logged-in user after confirmation.",
        "parameters": {
            "schedule_id": {"type": "string", "description": "e.g. NR_SCH01"},
            "origin_station_id": {"type": "string", "description": "e.g. NR01"},
            "destination_station_id": {"type": "string", "description": "e.g. NR05"},
            "travel_date": {"type": "string", "description": "YYYY-MM-DD"},
            "fare_class": {"type": "string", "description": "standard or first"},
            "seat_id": {"type": "string", "description": "Seat ID or any"},
            "ticket_type": {"type": "string", "description": "single or return"},
        },
        "required": [
            "schedule_id",
            "origin_station_id",
            "destination_station_id",
            "travel_date",
            "fare_class",
            "seat_id",
        ],
    },
    {
        "name": "cancel_booking",
        "description": "Cancel a national rail booking for the logged-in user.",
        "parameters": {
            "booking_id": {"type": "string", "description": "Booking reference e.g. BK-A1B2C3"},
        },
        "required": ["booking_id"],
    },
    {
        "name": "search_policy",
        "description": "Search company policy documents.",
        "parameters": {
            "query": {"type": "string", "description": "Natural language policy question"},
        },
        "required": ["query"],
    },
    {
        "name": "find_route",
        "description": "Find the best route or path between two stations.",
        "parameters": {
            "origin_id": {"type": "string", "description": "Station ID e.g. MS01 or NR01"},
            "destination_id": {"type": "string", "description": "Station ID e.g. MS09 or NR05"},
            "network": {"type": "string", "description": "metro, rail, or auto"},
            "optimise_by": {"type": "string", "description": "time or cost"},
        },
        "required": ["origin_id", "destination_id"],
    },
    {
        "name": "find_alternative_routes",
        "description": "Find routes that avoid a specific delayed or closed station.",
        "parameters": {
            "origin_id": {"type": "string", "description": "e.g. NR01"},
            "destination_id": {"type": "string", "description": "e.g. NR05"},
            "avoid_station_id": {"type": "string", "description": "e.g. NR03"},
            "network": {"type": "string", "description": "metro, rail, or auto"},
        },
        "required": ["origin_id", "destination_id", "avoid_station_id"],
    },
    {
        "name": "get_delay_ripple",
        "description": "Show affected stations and lines from a disruption.",
        "parameters": {
            "station_id": {"type": "string", "description": "Station ID e.g. NR03 or MS07"},
            "hops": {"type": "integer", "description": "Number of hops"},
        },
        "required": ["station_id"],
    },
    {
        "name": "get_station_connections",
        "description": "List direct outbound graph connections from one station.",
        "parameters": {
            "station_id": {"type": "string", "description": "Station ID e.g. MS01 or NR01"},
        },
        "required": ["station_id"],
    },
=======
>>>>>>> Stashed changes
    {"name": "check_national_rail_availability",
     "description": "Check available national rail trains between two NR stations.",
     "parameters": {
         "origin_id": {"type": "string", "description": "NR station ID e.g. NR01"},
         "destination_id": {"type": "string", "description": "NR station ID e.g. NR05"},
         "travel_date": {"type": "string", "description": "YYYY-MM-DD (optional)"},
     }, "required": ["origin_id", "destination_id"]},
    {"name": "get_national_rail_fare",
     "description": "Calculate fare for a national rail journey.",
     "parameters": {
         "schedule_id": {"type": "string", "description": "e.g. NR_SCH01"},
         "fare_class": {"type": "string", "description": "standard or first"},
         "stops_travelled": {"type": "integer", "description": "Number of stops"},
     }, "required": ["schedule_id", "fare_class", "stops_travelled"]},
    {"name": "check_metro_availability",
     "description": "Check available metro services between two MS stations.",
     "parameters": {
         "origin_id": {"type": "string", "description": "MS station ID e.g. MS01"},
         "destination_id": {"type": "string", "description": "MS station ID e.g. MS09"},
     }, "required": ["origin_id", "destination_id"]},
    {"name": "calculate_metro_fare",
     "description": "Calculate metro fare.",
     "parameters": {
         "schedule_id": {"type": "string", "description": "e.g. MS_SCH01"},
         "stops_travelled": {"type": "integer", "description": "Number of stops"},
     }, "required": ["schedule_id", "stops_travelled"]},
    {"name": "get_metro_fare",
     "description": "Get metro ticket price between two stations.",
     "parameters": {
         "origin_id": {"type": "string", "description": "MS station ID"},
         "destination_id": {"type": "string", "description": "MS station ID"},
     }, "required": ["origin_id", "destination_id"]},
    {"name": "get_user_bookings",
     "description": "Get logged-in user's booking history.",
     "parameters": {}, "required": []},
    {"name": "get_user_profile",
     "description": "Get logged-in user's profile info.",
     "parameters": {}, "required": []},
    {"name": "get_payment_info",
     "description": "Get payment details for a booking.",
     "parameters": {
         "booking_id": {"type": "string", "description": "e.g. BK-A1B2C3"},
     }, "required": ["booking_id"]},
    {"name": "get_available_seats",
     "description": "Show available seats for a national rail service.",
     "parameters": {
         "schedule_id": {"type": "string", "description": "e.g. NR_SCH01"},
         "travel_date": {"type": "string", "description": "YYYY-MM-DD"},
         "fare_class": {"type": "string", "description": "standard or first"},
     }, "required": ["schedule_id", "travel_date", "fare_class"]},
    {"name": "make_booking",
     "description": "Create a booking. REQUIRES LOGIN and explicit confirmation.",
     "parameters": {
         "schedule_id": {"type": "string", "description": "e.g. NR_SCH01"},
         "origin_station_id": {"type": "string", "description": "e.g. NR01"},
         "destination_station_id": {"type": "string", "description": "e.g. NR05"},
         "travel_date": {"type": "string", "description": "YYYY-MM-DD"},
         "fare_class": {"type": "string", "description": "standard or first"},
         "seat_id": {"type": "string", "description": "e.g. B05 or 'any'"},
         "ticket_type": {"type": "string", "description": "single or return"},
     }, "required": ["schedule_id", "origin_station_id", "destination_station_id",
                      "travel_date", "fare_class", "seat_id"]},
    {"name": "cancel_booking",
     "description": "Cancel a booking. REQUIRES LOGIN.",
     "parameters": {
         "booking_id": {"type": "string", "description": "e.g. BK-A1B2C3"},
     }, "required": ["booking_id"]},
    {"name": "search_policy",
     "description": "Search policy documents (refunds, compensation, luggage, etc.).",
     "parameters": {
         "query": {"type": "string", "description": "Question about policy"},
     }, "required": ["query"]},
    {"name": "find_route",
     "description": "Find best route between two stations. Works across networks.",
     "parameters": {
         "origin_id": {"type": "string", "description": "e.g. MS01 or NR01"},
         "destination_id": {"type": "string", "description": "e.g. MS09 or NR05"},
         "network": {"type": "string", "description": "metro, rail, or auto"},
         "optimise_by": {"type": "string", "description": "time or cost"},
     }, "required": ["origin_id", "destination_id"]},
    {"name": "find_alternative_routes",
     "description": "Find routes avoiding a specific station.",
     "parameters": {
         "origin_id": {"type": "string", "description": "e.g. NR01"},
         "destination_id": {"type": "string", "description": "e.g. NR05"},
         "avoid_station_id": {"type": "string", "description": "e.g. NR03"},
         "network": {"type": "string", "description": "metro, rail, or auto"},
     }, "required": ["origin_id", "destination_id", "avoid_station_id"]},
    {"name": "get_delay_ripple",
     "description": "Show stations affected by a delay.",
     "parameters": {
         "station_id": {"type": "string", "description": "e.g. NR03"},
         "hops": {"type": "integer", "description": "Connections to check (default 2)"},
     }, "required": ["station_id"]},
<<<<<<< Updated upstream
=======
>>>>>>> 4836b765bf1e177ac0fef698aec75593eac5dcd5
>>>>>>> Stashed changes
]

TOOLS_SCHEMA = """\
find_route(origin_id, destination_id, optimise_by?)
check_national_rail_availability(origin_id, destination_id, travel_date?)
get_national_rail_fare(schedule_id, fare_class, stops_travelled)
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
get_national_rail_schedule_fares(schedule_id)
get_national_rail_journey_fares(origin_id, destination_id, travel_date?, fare_class?)
=======
>>>>>>> 4836b765bf1e177ac0fef698aec75593eac5dcd5
>>>>>>> Stashed changes
check_metro_availability(origin_id, destination_id)
calculate_metro_fare(schedule_id, stops_travelled)
get_available_seats(schedule_id, travel_date, fare_class)
make_booking(schedule_id, origin_station_id, destination_station_id, travel_date, fare_class, seat_id, ticket_type?)
cancel_booking(booking_id)
get_user_bookings()
get_user_profile()
get_payment_info(booking_id)
search_policy(query)
find_alternative_routes(origin_id, destination_id, avoid_station_id, network?)
get_delay_ripple(station_id, hops?)"""


# ── Tool execution ────────────────────────────────────────────────────────────

def _execute_tool(tool_name: str, params: dict,
                  current_user_email: Optional[str] = None) -> str:
    try:
        if tool_name == "check_national_rail_availability":
            result = query_national_rail_availability(**params)
        elif tool_name == "get_national_rail_fare":
            result = query_national_rail_fare(**params)
<<<<<<< Updated upstream
=======
<<<<<<< HEAD

        elif tool_name == "get_national_rail_schedule_fares":
            result = query_national_rail_schedule_fares(params["schedule_id"])
            if not result:
                return json.dumps({"error": f"找不到班次 {params['schedule_id']} 的票價資料。"})

        elif tool_name == "get_national_rail_journey_fares":
            origin_id = params["origin_id"]
            destination_id = params["destination_id"]
            travel_date = params.get("travel_date")
            requested_class = params.get("fare_class", "all")
            classes = ["standard", "first"] if requested_class in ("", "all", None) else [requested_class]
            schedules = query_national_rail_availability(
                origin_id=origin_id,
                destination_id=destination_id,
                travel_date=travel_date,
            )
            if not schedules:
                result = {
                    "error": "很抱歉，找不到這兩個國鐵站之間的服務。請確認站點代碼或方向是否正確。"
                }
            else:
                priced_services = []
                for schedule in schedules:
                    fares = []
                    for fare_class in classes:
                        fare = query_national_rail_fare(
                            schedule_id=schedule["schedule_id"],
                            fare_class=fare_class,
                            stops_travelled=schedule["stops_travelled"],
                        )
                        if fare:
                            fares.append(fare)
                    priced_services.append({
                        **schedule,
                        "fares": fares,
                    })
                result = priced_services

=======
>>>>>>> 4836b765bf1e177ac0fef698aec75593eac5dcd5
>>>>>>> Stashed changes
        elif tool_name == "check_metro_availability":
            result = query_metro_schedules(origin_id=params["origin_id"],
                                           destination_id=params["destination_id"])
        elif tool_name == "calculate_metro_fare":
            result = query_metro_fare(**params)
        elif tool_name == "get_metro_fare":
            schedules = query_metro_schedules(origin_id=params["origin_id"],
                                              destination_id=params["destination_id"])
            if not schedules:
                result = {"error": "找不到這兩站之間的捷運服務。"}
            else:
                sched = schedules[0]
                stops = sched.get("stops_in_order") or []
                if isinstance(stops, str):
                    stops = json.loads(stops)
                try:
                    n_stops = stops.index(params["destination_id"]) - stops.index(params["origin_id"])
                except ValueError:
                    n_stops = 1
                fare = query_metro_fare(sched["schedule_id"], n_stops)
                result = {"origin": sched.get("origin_name", params["origin_id"]),
                          "destination": sched.get("destination_name", params["destination_id"]),
                          "line": sched.get("line"), "schedule_id": sched["schedule_id"],
                          "stops": n_stops, **(fare or {"error": "票價查詢失敗"})}
        elif tool_name == "get_user_bookings":
            if not current_user_email:
                return json.dumps({"error": "您尚未登入。請點右上角的登入按鈕後再試 😊"})
            result = query_user_bookings(current_user_email)
        elif tool_name == "get_user_profile":
            if not current_user_email:
                return json.dumps({"error": "您尚未登入。請點右上角的登入按鈕後再試 😊"})
            result = query_user_profile(current_user_email)
            if result is None:
                return json.dumps({"error": "找不到使用者資料，請重新登入。"})
        elif tool_name == "get_payment_info":
            if not current_user_email:
                return json.dumps({"error": "您尚未登入。請點右上角的登入按鈕後再試 😊"})
            result = query_payment_info(params["booking_id"])
            if result is None:
                return json.dumps({"error": f"找不到訂單 {params['booking_id']} 的付款紀錄。"})
        elif tool_name == "get_available_seats":
            result = query_available_seats(**params)
        elif tool_name == "make_booking":
            if not current_user_email:
                return json.dumps({"error": "您尚未登入。請點右上角的登入按鈕後再試 😊"})
            profile = query_user_profile(current_user_email)
            if not profile:
                return json.dumps({"error": "找不到使用者資料，請重新登入。"})
            ok, data = execute_booking(
                user_id=profile["user_id"], schedule_id=params["schedule_id"],
                origin_station_id=params["origin_station_id"],
                destination_station_id=params["destination_station_id"],
                travel_date=params["travel_date"], fare_class=params["fare_class"],
                seat_id=params["seat_id"], ticket_type=params.get("ticket_type", "single"))
            result = data if ok else {"error": f"訂票失敗：{data}"}
        elif tool_name == "cancel_booking":
            if not current_user_email:
                return json.dumps({"error": "您尚未登入。請點右上角的登入按鈕後再試 😊"})
            profile = query_user_profile(current_user_email)
            if not profile:
                return json.dumps({"error": "找不到使用者資料，請重新登入。"})
            ok, data = execute_cancellation(booking_id=params["booking_id"],
                                            user_id=profile["user_id"])
            result = data if ok else {"error": f"取消失敗：{data}"}
        elif tool_name == "search_policy":
            raw_query = params["query"]
            search_query = _translate_policy_query(raw_query)
            embedding = llm.embed(search_query)
            docs = query_policy_vector_search(embedding)
            if not docs and search_query != raw_query:
                embedding = llm.embed(raw_query)
                docs = query_policy_vector_search(embedding)
            if not docs:
                return json.dumps({"error": "找不到相關政策資訊。請嘗試用不同的關鍵字搜尋。"})
            result = [{"title": d["title"], "category": d["category"],
                       "content": d["content"][:800], "similarity": round(d["similarity"], 3)}
                      for d in docs]
        elif tool_name == "find_route":
            oid, did = params["origin_id"], params["destination_id"]
            network = params.get("network", "auto")
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
            optimise_by = params.get("optimise_by", "time")

            is_cross = (
                origin_id.upper().startswith("MS")
                and destination_id.upper().startswith("NR")
            ) or (
                origin_id.upper().startswith("NR")
                and destination_id.upper().startswith("MS")
            )
            if optimise_by == "cost":
                result = query_cheapest_route(
                    origin_id=origin_id,
                    destination_id=destination_id,
                    network=network,
                )
            elif is_cross:
                result = query_interchange_path(origin_id, destination_id)
=======
>>>>>>> Stashed changes
            opt = params.get("optimise_by", "time")
            is_cross = ((oid.upper().startswith("MS") and did.upper().startswith("NR")) or
                        (oid.upper().startswith("NR") and did.upper().startswith("MS")))
            if is_cross:
                result = query_interchange_path(oid, did)
            elif opt == "cost":
                result = query_cheapest_route(oid, did, network)
<<<<<<< Updated upstream
=======
>>>>>>> 4836b765bf1e177ac0fef698aec75593eac5dcd5
>>>>>>> Stashed changes
            else:
                result = query_shortest_route(oid, did, network)
        elif tool_name == "find_alternative_routes":
            routes = query_alternative_routes(
                origin_id=params["origin_id"], destination_id=params["destination_id"],
                avoid_station_id=params["avoid_station_id"],
                network=params.get("network", "auto"))
            result = [{"route_number": i + 1, "legs": r} for i, r in enumerate(routes)]
        elif tool_name == "get_delay_ripple":
<<<<<<< Updated upstream
            result = query_delay_ripple(delayed_station_id=params["station_id"],
                                        hops=params.get("hops", 2))
=======
<<<<<<< HEAD
            result = query_delay_ripple(
                delayed_station_id=params["station_id"],
                hops=params.get("hops", 2),
            )

        elif tool_name == "get_station_connections":
            result = query_station_connections(params["station_id"])

=======
            result = query_delay_ripple(delayed_station_id=params["station_id"],
                                        hops=params.get("hops", 2))
>>>>>>> 4836b765bf1e177ac0fef698aec75593eac5dcd5
>>>>>>> Stashed changes
        else:
            result = {"error": f"未知工具：{tool_name}"}
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": f"系統發生錯誤：{str(e)}。請稍後再試。"})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _flatten_to_text(obj, depth: int = 0) -> str:
    pad = "  " * depth
    if isinstance(obj, dict):
        if not obj:
            return f"{pad}(empty)"
        lines = []
        for k, v in obj.items():
            if v is None:
                continue
            if isinstance(v, (dict, list)):
                inner = _flatten_to_text(v, depth + 1)
                if inner.strip():
                    lines.append(f"{pad}{k}:\n{inner}")
            else:
                lines.append(f"{pad}{k}: {v}")
        return "\n".join(lines) or f"{pad}(empty)"
    elif isinstance(obj, list):
        if not obj:
            return f"{pad}(no records)"
        parts = []
        for i, item in enumerate(obj, 1):
            if isinstance(item, (dict, list)):
                parts.append(f"{pad}[{i}]")
                parts.append(_flatten_to_text(item, depth + 1))
            else:
                parts.append(f"{pad}- {item}")
        return "\n".join(parts)
    else:
        return f"{pad}{obj}"


def _normalise_result(tool_name: str, result_json: str) -> str:
    try:
        data = json.loads(result_json)
    except json.JSONDecodeError:
        return result_json
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    return _flatten_to_text(data)


def _parse_tool_calls(llm_response: str) -> list[dict] | None:
    text = llm_response.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    decoder = json.JSONDecoder()
    for m in re.finditer(r'\{', text):
        try:
            data, _ = decoder.raw_decode(text, m.start())
            if "tool_calls" in data:
                return data["tool_calls"]
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
        if "tool_calls" in data:
            return data["tool_calls"]
        if "tools" in data:
            return data["tools"]
        if "calls" in data:
            return data["calls"]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(data, list):
        return data
>>>>>>> Stashed changes
    return None


# ── Multi-step booking chain ──────────────────────────────────────────────────

def _chain_booking_query(origin_id, destination_id, travel_date, fare_class,
                         seat_preference, current_user_email, debug_info, debug):
    results = []
    avail_params = {"origin_id": origin_id, "destination_id": destination_id}
    if travel_date:
        avail_params["travel_date"] = travel_date
    if debug:
        debug_info.append(f"**Chain step 1:** check_national_rail_availability({avail_params})")
    avail_json = _execute_tool("check_national_rail_availability", avail_params, current_user_email)
    results.append({"tool": "check_national_rail_availability", "params": avail_params,
                     "result": avail_json, "summary": avail_json})
    try:
        avail_data = json.loads(avail_json)
        if isinstance(avail_data, list) and avail_data:
            for sched in avail_data:
                sid = sched.get("schedule_id")
                stops = sched.get("stops_travelled")
                if sid and stops:
                    fp = {"schedule_id": sid, "fare_class": fare_class, "stops_travelled": stops}
                    if debug:
                        debug_info.append(f"**Chain step 2:** get_national_rail_fare({fp})")
                    fr = _execute_tool("get_national_rail_fare", fp, current_user_email)
                    results.append({"tool": "get_national_rail_fare", "params": fp,
                                     "result": fr, "summary": fr})
                if sid and travel_date and sched == avail_data[0]:
                    sp = {"schedule_id": sid, "travel_date": travel_date, "fare_class": fare_class}
                    if debug:
                        debug_info.append(f"**Chain step 3:** get_available_seats({sp})")
                    sr = _execute_tool("get_available_seats", sp, current_user_email)
                    results.append({"tool": "get_available_seats", "params": sp,
                                     "result": sr, "summary": sr})
    except (json.JSONDecodeError, KeyError, IndexError):
        pass
    if seat_preference:
        results.append({"tool": "seat_preference", "params": {"preference": seat_preference},
                         "result": json.dumps({"user_seat_preference": seat_preference}),
                         "summary": json.dumps({"user_seat_preference": seat_preference})})
    return results


<<<<<<< Updated upstream
=======
def run_agent(
    user_message: str,
    history: list[dict],
    debug: bool = False,
    current_user_email: Optional[str] = None,
) -> tuple:
    """Main agent loop."""
=======
    return None


# ── Multi-step booking chain ──────────────────────────────────────────────────

def _chain_booking_query(origin_id, destination_id, travel_date, fare_class,
                         seat_preference, current_user_email, debug_info, debug):
    results = []
    avail_params = {"origin_id": origin_id, "destination_id": destination_id}
    if travel_date:
        avail_params["travel_date"] = travel_date
    if debug:
        debug_info.append(f"**Chain step 1:** check_national_rail_availability({avail_params})")
    avail_json = _execute_tool("check_national_rail_availability", avail_params, current_user_email)
    results.append({"tool": "check_national_rail_availability", "params": avail_params,
                     "result": avail_json, "summary": avail_json})
    try:
        avail_data = json.loads(avail_json)
        if isinstance(avail_data, list) and avail_data:
            for sched in avail_data:
                sid = sched.get("schedule_id")
                stops = sched.get("stops_travelled")
                if sid and stops:
                    fp = {"schedule_id": sid, "fare_class": fare_class, "stops_travelled": stops}
                    if debug:
                        debug_info.append(f"**Chain step 2:** get_national_rail_fare({fp})")
                    fr = _execute_tool("get_national_rail_fare", fp, current_user_email)
                    results.append({"tool": "get_national_rail_fare", "params": fp,
                                     "result": fr, "summary": fr})
                if sid and travel_date and sched == avail_data[0]:
                    sp = {"schedule_id": sid, "travel_date": travel_date, "fare_class": fare_class}
                    if debug:
                        debug_info.append(f"**Chain step 3:** get_available_seats({sp})")
                    sr = _execute_tool("get_available_seats", sp, current_user_email)
                    results.append({"tool": "get_available_seats", "params": sp,
                                     "result": sr, "summary": sr})
    except (json.JSONDecodeError, KeyError, IndexError):
        pass
    if seat_preference:
        results.append({"tool": "seat_preference", "params": {"preference": seat_preference},
                         "result": json.dumps({"user_seat_preference": seat_preference}),
                         "summary": json.dumps({"user_seat_preference": seat_preference})})
    return results


>>>>>>> Stashed changes
# ── Main agent loop ───────────────────────────────────────────────────────────

def run_agent(user_message: str, history: list[dict], debug: bool = False,
              current_user_email: Optional[str] = None) -> tuple:
<<<<<<< Updated upstream
=======
>>>>>>> 4836b765bf1e177ac0fef698aec75593eac5dcd5
>>>>>>> Stashed changes
    debug_info = []

    # ══════════════════════════════════════════════════════════════════
    # Step 0a: CONFIRMATION CHECK (on RAW user_message, before anything)
    # ══════════════════════════════════════════════════════════════════
    if _is_confirmation(user_message):
        if debug:
            debug_info.append("**Confirmation detected** (early check on raw message)")

        if not current_user_email:
            if debug:
                debug_info.append("**Booking blocked:** not logged in")
            answer = "您尚未登入，無法完成訂票。請點右上角的登入按鈕後再試 😊"
        else:
            booking_ctx = _recover_booking_context(history)
            if booking_ctx:
                if debug:
                    debug_info.append(f"**Recovered booking context:** {booking_ctx}")
                result_json = _execute_tool("make_booking", booking_ctx, current_user_email)
                if debug:
                    debug_info.append(f"**make_booking result:** {result_json[:300]}")
                data_block = f"[make_booking]\n{_normalise_result('make_booking', result_json)}"
                content = (f"DATA FROM TRANSITFLOW DATABASE:\n{data_block}"
                           f"\n\nThe user confirmed a booking. Tell them the result.")
                ctx_prompt = SYSTEM_PROMPT
                profile = query_user_profile(current_user_email)
                if profile:
                    ctx_prompt += f"\n\n目前登入使用者：{profile['full_name']}"
                answer = llm.chat(
                    messages=history + [{"role": "user", "content": content}],
                    system_prompt=ctx_prompt)
            else:
                if debug:
                    debug_info.append("**No booking context found** in history")
                answer = llm.chat(
                    messages=history + [{"role": "user", "content":
                        "The user said '確認' but no booking details were found. "
                        "Ask them to provide: origin, destination, date, fare class."}],
                    system_prompt=SYSTEM_PROMPT)

        updated_history = history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": answer},
        ]
        if debug:
            return answer, updated_history, "\n\n".join(debug_info)
        return answer, updated_history

    # ══════════════════════════════════════════════════════════════════
    # Step 0b: GREETING CHECK
    # ══════════════════════════════════════════════════════════════════
    if _is_greeting(user_message):
        if debug:
            debug_info.append("**Greeting detected** — skipping all tool calls.")
        answer = llm.chat(
            messages=history + [{"role": "user", "content": user_message}],
            system_prompt=SYSTEM_PROMPT)
        updated_history = history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": answer},
        ]
        if debug:
            return answer, updated_history, "\n\n".join(debug_info)
        return answer, updated_history

    # ══════════════════════════════════════════════════════════════════
    # Step 1: Pre-processing
    # ══════════════════════════════════════════════════════════════════
    _augmented = _inject_station_ids(user_message)
    _station_ids = _extract_station_ids(_augmented)
    _travel_date = _extract_date(user_message)
    _fare_class = _extract_fare_class(user_message)
    _ticket_type = _extract_ticket_type(user_message)
    _seat_pref = _extract_seat_preference(user_message)
    _lower = _augmented.lower()

    # ══════════════════════════════════════════════════════════════════
    # Step 2: Pre-classify
    # ══════════════════════════════════════════════════════════════════
    category = _pre_classify_query(_augmented, _station_ids, _travel_date is not None,
                                   current_user_email)

    # ── BUG FIX #4: Continuation dialog detection ────────────────────
    # If category is "general" but message has booking keywords without
    # station IDs, check conversation history for station context.
    if category == "general":
        _booking_cont_kw = {
            "訂", "book", "ticket", "買", "購買", "第一班", "第二班",
            "幫我訂", "我要訂", "standard", "first class",
        }
        if any(kw in user_message.lower() for kw in _booking_cont_kw):
            hist_text = " ".join(m.get("content", "") for m in history[-6:])
            hist_stations = _extract_station_ids(hist_text)
            if len(hist_stations) >= 2:
                category = "booking"
                _station_ids = hist_stations[:2]
                _travel_date = _travel_date or _extract_date(hist_text)
                if debug:
                    debug_info.append(
                        f"**Continuation detected:** booking from history, "
                        f"stations={_station_ids}, date={_travel_date}")

    if debug:
        debug_info.append(f"**Pre-classification:** {category}")

    # ══════════════════════════════════════════════════════════════════
    # Step 3: Context prompt
    # ══════════════════════════════════════════════════════════════════
    if current_user_email:
        profile = query_user_profile(current_user_email)
        user_display = f"{profile['full_name']} ({current_user_email})" if profile else current_user_email
        contextual_prompt = SYSTEM_PROMPT + f"\n\n目前登入使用者：{user_display}。"
    else:
<<<<<<< Updated upstream
        contextual_prompt = SYSTEM_PROMPT + "\n\n目前沒有使用者登入。訂票和取消需要先登入。"
=======
<<<<<<< HEAD
        contextual_prompt = SYSTEM_PROMPT + (
            "\n\n目前沒有使用者登入。"
            "如果使用者詢問個人訂票、歷史紀錄，或想要訂票、取消訂票，"
            "請友善地告知他們需要先登入。"
        )

    recent_history = history[-4:] if len(history) > 4 else history
    augmented_message = _inject_station_ids(user_message)

    # Gemini is stronger than Ollama, but we still ask for a tiny JSON routing
    # decision so database access remains explicit and inspectable in debug mode.
    tool_selection_prompt = f"""Output only this JSON (no other text):
{{"tool_calls": [{{"name": "TOOL", "params": {{"KEY": "VALUE"}}}}]}}
Or if no tool needed: {{"tool_calls": []}}

STATIONS: Metro=MS01-MS20, Rail=NR01-NR10
USER: {current_user_email or "not logged in"}
Use relational tools for schedules, availability, fares, seats, bookings, payments, and policies.
Use graph tools only for route/path/interchange/disruption questions.
get_user_bookings: call when logged-in user asks about their bookings, tickets, or travel history.
get_user_profile: call when logged-in user asks about their account or profile.
get_payment_info: call with booking_id when user asks about payment for a specific booking.
Booking requests before confirmation: do not call make_booking; call booking_preflight.
make_booking: only if user is logged in AND the latest user message explicitly confirms the booking.
cancel_booking: only if user is logged in and the user asks to cancel.
Route/path/journey/怎麼去/如何前往/路線 questions: use find_route.
Metro fare/price/cost/票價/多少錢 between two MS stations: use get_metro_fare.
National rail fare/price/cost/票價/多少錢 between two NR stations: use get_national_rail_journey_fares.
National rail fare/price/cost for a schedule id like NR_SCH04: use get_national_rail_schedule_fares.
Schedule/timetable/班次/時刻表 between two stations: use check_metro_availability or check_national_rail_availability.
Direct neighbours/adjacent stations/相鄰/直接連到: use get_station_connections.
Avoid/避開 route questions: use find_alternative_routes.
Delay/延誤/affected stations/hops: use get_delay_ripple.
Policy/rules/退款/補償/行李/寵物 questions: use search_policy.
Never use "" as a param value. Omit optional params if unknown.

TOOLS:
{TOOLS_SCHEMA}

HISTORY:
{json.dumps(recent_history, indent=None)}

USER: "{augmented_message}"

JSON:"""

    if llm.get_chat_provider() == "ollama":
        try:
            tool_calls = llm.ollama_tool_call(
                recent_history,
                TOOLS,
                augmented_message,
                system_prompt=(
                    "You are a tool router. Call the right tool based on the user message. "
                    f"Logged-in user: {current_user_email or 'none'}. "
                    "My bookings/tickets/travel history/我的訂票 -> get_user_bookings. "
                    "My account/profile/我的帳號 -> get_user_profile. "
                    "Payment info for booking -> get_payment_info. "
                    "Fare/price/cost for a rail schedule id like NR_SCH04 -> get_national_rail_schedule_fares. "
                    "Book a ticket before confirmation -> booking_preflight, not make_booking. "
                    "Only explicit confirmation -> make_booking. "
                    "Cancel a booking -> cancel_booking. "
                    "Policy/rules/refund/luggage/bicycle/退款/補償/行李/寵物 -> search_policy. "
                    "Route/directions/fastest/how-to-get/怎麼去/路線 -> find_route. "
                    "Adjacent/direct station connections/相鄰/直接連到 -> get_station_connections. "
                    "Delay/延誤/hops -> get_delay_ripple. "
                    "Metro fare/price/cost/票價/多少錢 -> get_metro_fare. "
                    "Schedule/timetable/trains/services/班次/時刻表 -> availability tools. "
                    "Only call a tool when needed."
                ),
            )
        except ConnectionError as exc:
            tool_calls = []
            if debug:
                debug_info.append(f"**Tool selection unavailable:** {exc}")
        raw_tool_selection = tool_calls
    else:
        selection_response = ""
        try:
            selection_response = llm.chat(
                messages=[{"role": "user", "content": tool_selection_prompt}],
                system_prompt="JSON only. You are a router. Output valid JSON. No empty string param values.",
            )
            tool_calls = _parse_tool_calls(selection_response) or []
        except Exception as exc:
            tool_calls = []
            if debug:
                debug_info.append(f"**Tool selection unavailable:** {exc}")
        raw_tool_selection = selection_response

    lower = augmented_message.lower()
    station_ids = _unique_preserve_order(
        re.findall(r"(MS\d{2}|NR\d{2})", augmented_message, re.IGNORECASE)
    )
    schedule_ids = _unique_preserve_order(
        re.findall(r"(NR_SCH\d{2}|MS_SCH\d{2})", augmented_message, re.IGNORECASE)
    )
    booking_ids = re.findall(r"((?:BK|MT)[A-Z0-9-]*\d+[A-Z0-9-]*)", augmented_message, re.IGNORECASE)
    two_stations = len(station_ids) >= 2
    stops_match = re.search(r"\b(\d+)\s*(?:stops?|站)\b", lower)
    stops_travelled = int(stops_match.group(1)) if stops_match else None
    fare_class = None
    if "first" in lower or "頭等" in lower:
        fare_class = "first"
    elif "standard" in lower or "標準" in lower:
        fare_class = "standard"

    # Safety rule: booking requests are read-only until the latest user message
    # confirms. If Gemini jumps to make_booking too early, rewrite it to
    # booking_preflight before any tool can execute.
    confirmed_now, confirmation_source = _booking_confirmed(user_message, history)
    if debug and confirmed_now:
        debug_info.append(f"**Booking confirmation:** {confirmation_source}")
    original_tool_calls = tool_calls
    tool_calls = _redirect_unconfirmed_booking_calls(tool_calls, confirmed_now)
    if debug:
        if tool_calls != original_tool_calls:
            debug_info.append(f"**Raw tool selection:** {raw_tool_selection}")
            debug_info.append(f"**Tool selection:** {tool_calls}")
        elif raw_tool_selection:
            debug_info.append(f"**Tool selection:** {raw_tool_selection}")

    def _tool_selected(name: str, *required_params) -> bool:
        call = next((c for c in tool_calls if c.get("name") == name), None)
        if not call:
            return False
        params = call.get("params") or call.get("parameters") or {}
        return all(params.get(k) for k in required_params)

    def _fallback(name: str, params: dict, reason: str) -> None:
        nonlocal tool_calls
        tool_calls = [{"name": name, "params": params}]
        if debug:
            debug_info.append(f"**Fallback:** {reason} -> {name}({params})")

    # Rule-based fallbacks cover the fixed demo questions and short Chinese
    # prompts where even Gemini may choose an overly broad or write-oriented tool.
    route_triggers = {
        "fastest route",
        "quickest route",
        "shortest route",
        "cheapest route",
        "best route",
        "how to get",
        "directions from",
        "route from",
        "route to",
        "get from",
        "travel from",
        "way from",
        "path from",
        "最快路線",
        "最短路線",
        "最便宜路線",
        "最便宜",
        "最快",
        "怎麼去",
        "如何前往",
        "路線規劃",
        "路線查詢",
        "怎麼走",
        "如何去",
        "如何搭",
        "怎麼搭",
        "搭到",
        "轉乘",
        "換乘",
        "怎麼轉",
        "如何轉乘",
    }
    fare_triggers = {
        "fare",
        "price",
        "cost",
        "ticket price",
        "多少錢",
        "票價",
        "價格",
        "費用",
    }
    date_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", lower)
    travel_date = date_match.group(0) if date_match else None

    # Booking/payment/cancellation references are deterministic enough to route
    # with regex, so prefer direct routing over another LLM guess.
    if booking_ids and not tool_calls:
        booking_id = booking_ids[0].upper()
        if any(kw in lower for kw in ["cancel", "取消"]):
            _fallback("cancel_booking", {"booking_id": booking_id}, "cancel booking query")
        elif any(kw in lower for kw in ["payment", "付款", "付款方式", "金額"]):
            _fallback("get_payment_info", {"booking_id": booking_id}, "payment info query")

    if not tool_calls and any(kw in lower for kw in ["cancel", "取消"]):
        previous_ids = re.findall(
            r"((?:BK|MT)[A-Z0-9-]*\d+[A-Z0-9-]*)",
            _history_text(history),
            re.IGNORECASE,
        )
        if previous_ids:
            _fallback(
                "cancel_booking",
                {"booking_id": previous_ids[-1].upper()},
                "cancel previous booking query",
            )

    if schedule_ids and not tool_calls:
        schedule_id = schedule_ids[0].upper()
        if any(kw in lower for kw in ["seat", "seats", "座位"]):
            if travel_date and fare_class:
                _fallback(
                    "get_available_seats",
                    {
                        "schedule_id": schedule_id,
                        "travel_date": travel_date,
                        "fare_class": fare_class,
                    },
                    "available seats query",
                )
        elif schedule_id.startswith("NR_SCH") and stops_travelled and fare_class:
            _fallback(
                "get_national_rail_fare",
                {
                    "schedule_id": schedule_id,
                    "fare_class": fare_class,
                    "stops_travelled": stops_travelled,
                },
                "national rail fare with stops query",
            )
        elif schedule_id.startswith("MS_SCH") and stops_travelled:
            _fallback(
                "calculate_metro_fare",
                {
                    "schedule_id": schedule_id,
                    "stops_travelled": stops_travelled,
                },
                "metro fare with stops query",
            )

    if (
        schedule_ids
        and any(kw in lower for kw in fare_triggers)
        and not _tool_selected("get_national_rail_schedule_fares", "schedule_id")
        and not tool_calls
    ):
        schedule_id = schedule_ids[0].upper()
        if schedule_id.startswith("NR_SCH"):
            _fallback(
                "get_national_rail_schedule_fares",
                {"schedule_id": schedule_id},
                "national rail schedule fare query",
            )

    if not tool_calls and len(station_ids) >= 3 and any(
        kw in lower for kw in ["avoid", "避開", "alternative"]
    ):
        _fallback(
            "find_alternative_routes",
            {
                "origin_id": station_ids[0].upper(),
                "destination_id": station_ids[1].upper(),
                "avoid_station_id": station_ids[2].upper(),
                "network": "auto",
            },
            "alternative route query",
        )

    if not tool_calls and station_ids and any(
        kw in lower for kw in ["delay", "delayed", "延誤", "影響", "hops", "hop"]
    ):
        hops_match = re.search(r"\b(\d+)\s*hops?\b", lower)
        if not hops_match:
            hops_match = re.search(r"(\d+)\s*hops?", lower)
        hops = int(hops_match.group(1)) if hops_match else 2
        _fallback(
            "get_delay_ripple",
            {"station_id": station_ids[0].upper(), "hops": hops},
            "delay ripple query",
        )

    if not tool_calls and station_ids and any(
        kw in lower for kw in ["相鄰", "直接連", "直接相鄰", "direct", "adjacent", "connections"]
    ):
        _fallback(
            "get_station_connections",
            {"station_id": station_ids[0].upper()},
            "station connections query",
        )

    if not tool_calls and any(kw in lower for kw in ["我想訂", "我要訂", "訂票", "book", "booking"]):
        booking_params = _extract_booking_params(augmented_message)
        if booking_params:
            tool_calls = [{"name": "booking_preflight", "params": booking_params}]
            if debug:
                debug_info.append(f"**Fallback:** booking request -> booking_preflight({booking_params})")

    if (
        not tool_calls
        and
        two_stations
        and any(kw in lower for kw in fare_triggers)
        and not any(
            _tool_selected(name, "origin_id", "destination_id")
            for name in ("get_metro_fare", "get_national_rail_journey_fares", "find_route")
        )
    ):
        origin_id = station_ids[0].upper()
        destination_id = station_ids[1].upper()
        same_metro = origin_id.startswith("MS") and destination_id.startswith("MS")
        same_rail = origin_id.startswith("NR") and destination_id.startswith("NR")
        if same_metro:
            _fallback(
                "get_metro_fare",
                {"origin_id": origin_id, "destination_id": destination_id},
                "metro station fare query",
            )
        elif same_rail:
            params = {"origin_id": origin_id, "destination_id": destination_id}
            if travel_date:
                params["travel_date"] = travel_date
            if "first" in lower or "頭等" in lower or "first class" in lower:
                params["fare_class"] = "first"
            elif "standard" in lower or "標準" in lower:
                params["fare_class"] = "standard"
            _fallback(
                "get_national_rail_journey_fares",
                params,
                "national rail station fare query",
            )
        else:
            _fallback(
                "find_route",
                {
                    "origin_id": origin_id,
                    "destination_id": destination_id,
                    "optimise_by": "cost",
                },
                "cross-network fare query",
            )

    is_route = (
        any(kw in lower for kw in route_triggers)
        or (two_stations and "route" in lower)
        or (two_stations and "路線" in lower)
    )
    if (
        not tool_calls
        and is_route
        and two_stations
        and not _tool_selected("find_route", "origin_id", "destination_id")
    ):
        optimise_by = "cost" if any(
            kw in lower for kw in ["cheap", "cheapest", "lowest cost", "最便宜", "最低票價"]
        ) else "time"
        _fallback(
            "find_route",
            {
                "origin_id": station_ids[0].upper(),
                "destination_id": station_ids[1].upper(),
                "optimise_by": optimise_by,
            },
            "route query",
        )

    elif not tool_calls and two_stations:
        availability_triggers = {
            "train",
            "trains",
            "service",
            "services",
            "run from",
            "runs from",
            "schedule",
            "timetable",
            "available",
            "availability",
            "班次",
            "時刻表",
            "列車",
            "服務",
            "有沒有車",
            "幾點有車",
            "查車",
        }
        if any(kw in lower for kw in availability_triggers):
            origin_id = station_ids[0].upper()
            destination_id = station_ids[1].upper()
            params = {"origin_id": origin_id, "destination_id": destination_id}
            if travel_date:
                params["travel_date"] = travel_date
            tool = "check_national_rail_availability" if origin_id.startswith("NR") else "check_metro_availability"
            _fallback(tool, params, "availability query")

    if current_user_email and not tool_calls:
        personal_triggers = {
            "my booking",
            "my ticket",
            "my trip",
            "my journey",
            "my history",
            "my reservation",
            "show booking",
            "view booking",
            "check booking",
            "list booking",
            "show my",
            "view my",
            "我的訂票",
            "我的票",
            "我的行程",
            "訂票紀錄",
            "查詢訂票",
            "我訂的",
            "我的車票",
        }
        if any(kw in lower for kw in personal_triggers):
            _fallback("get_user_bookings", {}, "personal booking query")

    if current_user_email and not tool_calls:
        profile_triggers = {
            "my account",
            "my profile",
            "my info",
            "account details",
            "我的帳號",
            "我的資料",
            "帳號資訊",
            "個人資料",
        }
        if any(kw in lower for kw in profile_triggers):
            _fallback("get_user_profile", {}, "profile query")

    if not tool_calls:
        policy_triggers = {
            "refund",
            "policy",
            "compensation",
            "luggage",
            "bicycle",
            "pet",
            "退款",
            "補償",
            "政策",
            "行李",
            "寵物",
            "腳踏車",
            "規定",
        }
        if any(kw in lower for kw in policy_triggers):
            _fallback("search_policy", {"query": user_message}, "policy query")

    if not tool_calls and confirmed_now:
        # On "confirm" turns, recover the pending booking details from recent
        # conversation text so make_booking can run with concrete parameters.
        recovered = _extract_booking_params(_history_text(history) + "\n" + augmented_message)
        if recovered:
            tool_calls = [{"name": "make_booking", "params": recovered}]
            if debug:
                debug_info.append(f"**Fallback:** booking confirmation -> make_booking({recovered})")
=======
        contextual_prompt = SYSTEM_PROMPT + "\n\n目前沒有使用者登入。訂票和取消需要先登入。"
>>>>>>> 4836b765bf1e177ac0fef698aec75593eac5dcd5
>>>>>>> Stashed changes

    # ══════════════════════════════════════════════════════════════════
    # Step 4: Execute based on category
    # ══════════════════════════════════════════════════════════════════
    tool_results = []
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
    if any(c.get("name") in {"make_booking", "booking_preflight"} for c in tool_calls):
        if not confirmed_now:
            # Unconfirmed booking intent becomes a read-only preflight sequence:
            # availability -> fare -> seats.
            preflight_results = []
            for call in tool_calls:
                if call.get("name") not in {"make_booking", "booking_preflight"}:
                    continue
                preflight_results.extend(_booking_preflight_results(
                    call.get("params") or call.get("parameters", {}),
                    current_user_email,
                ))
>>>>>>> Stashed changes

    if category == "booking" and len(_station_ids) >= 2:
        if not current_user_email and debug:
            debug_info.append("**Pre-login check:** not logged in")
        tool_results = _chain_booking_query(
            _station_ids[0], _station_ids[1], _travel_date, _fare_class,
            _seat_pref, current_user_email, debug_info, debug)
        if not current_user_email:
            tool_results.append({"tool": "login_reminder", "params": {},
                "result": json.dumps({"reminder": "需要登入才能訂票"}),
                "summary": json.dumps({"reminder": "需要登入"})})
        if _ticket_type != "single":
            tool_results.append({"tool": "ticket_type_info", "params": {},
                "result": json.dumps({"requested_ticket_type": _ticket_type}),
                "summary": json.dumps({"requested_ticket_type": _ticket_type})})

    elif category == "route" and len(_station_ids) >= 2:
        opt = "cost" if any(kw in _lower for kw in ["cheap", "cheapest", "最便宜"]) else "time"
        params = {"origin_id": _station_ids[0], "destination_id": _station_ids[1], "optimise_by": opt}
        if debug:
            debug_info.append(f"**Direct call:** find_route({params})")
        r = _execute_tool("find_route", params, current_user_email)
        tool_results.append({"tool": "find_route", "params": params, "result": r, "summary": r})

    elif category == "availability" and len(_station_ids) >= 2:
        o, d = _station_ids[0], _station_ids[1]
        tn = "check_national_rail_availability" if o.startswith("NR") else "check_metro_availability"
        params = {"origin_id": o, "destination_id": d}
        if _travel_date:
            params["travel_date"] = _travel_date
        if debug:
            debug_info.append(f"**Direct call:** {tn}({params})")
        r = _execute_tool(tn, params, current_user_email)
        tool_results.append({"tool": tn, "params": params, "result": r, "summary": r})

    elif category == "fare" and len(_station_ids) >= 2:
        o, d = _station_ids[0], _station_ids[1]
        if o.startswith("NR"):
            params = {"origin_id": o, "destination_id": d}
            if _travel_date:
                params["travel_date"] = _travel_date
            r = _execute_tool("check_national_rail_availability", params, current_user_email)
            tool_results.append({"tool": "check_national_rail_availability", "params": params,
                                  "result": r, "summary": r})
            try:
                data = json.loads(r)
                if isinstance(data, list) and data:
                    s = data[0]
                    fp = {"schedule_id": s["schedule_id"], "fare_class": _fare_class,
                          "stops_travelled": s["stops_travelled"]}
                    fr = _execute_tool("get_national_rail_fare", fp, current_user_email)
                    tool_results.append({"tool": "get_national_rail_fare", "params": fp,
                                          "result": fr, "summary": fr})
            except (json.JSONDecodeError, KeyError):
                pass
        else:
            params = {"origin_id": o, "destination_id": d}
            r = _execute_tool("get_metro_fare", params, current_user_email)
            tool_results.append({"tool": "get_metro_fare", "params": params,
                                  "result": r, "summary": r})

<<<<<<< Updated upstream
    elif category == "policy":
        params = {"query": user_message}
        if debug:
            debug_info.append(f"**Direct call:** search_policy({params})")
        r = _execute_tool("search_policy", params, current_user_email)
        tool_results.append({"tool": "search_policy", "params": params, "result": r, "summary": r})

    elif category == "personal":
        filtered = _filter_tools(TOOLS, category)
        if llm.get_chat_provider() == "ollama":
            tc = llm.ollama_tool_call(
                history[-4:] if len(history) > 4 else history, filtered, _augmented,
                system_prompt=f"Tool router. User: {current_user_email or 'none'}. "
                              "bookings→get_user_bookings, profile→get_user_profile, "
                              "payment→get_payment_info(booking_id).")
        else:
            tc = [{"name": "get_user_bookings", "params": {}}]
        if debug:
            debug_info.append(f"**Tool selection (filtered {len(filtered)} tools):** {tc}")
        for call in tc:
            n = call.get("name", "")
            p = call.get("params") or {}
            if any(v == "" for v in p.values()):
                continue
            r = _execute_tool(n, p, current_user_email)
            tool_results.append({"tool": n, "params": p, "result": r, "summary": r})

    elif category == "cancel":
        bk = re.search(r'(BK-[A-Z0-9]+)', user_message, re.IGNORECASE)
        if bk:
            params = {"booking_id": bk.group(1)}
            if debug:
                debug_info.append(f"**Direct call:** cancel_booking({params})")
            r = _execute_tool("cancel_booking", params, current_user_email)
            tool_results.append({"tool": "cancel_booking", "params": params,
                                  "result": r, "summary": r})
        else:
            filtered = _filter_tools(TOOLS, category)
            if llm.get_chat_provider() == "ollama":
                tc = llm.ollama_tool_call(history[-4:] if len(history) > 4 else history,
                    filtered, _augmented, system_prompt="Extract booking ID, call cancel_booking.")
            else:
                tc = []
            if debug:
                debug_info.append(f"**Tool selection (filtered):** {tc}")
            for call in tc:
                n = call.get("name", "")
                p = call.get("params") or {}
                r = _execute_tool(n, p, current_user_email)
                tool_results.append({"tool": n, "params": p, "result": r, "summary": r})

    elif category == "delay":
        if _station_ids:
            params = {"station_id": _station_ids[0], "hops": 2}
            if debug:
                debug_info.append(f"**Direct call:** get_delay_ripple({params})")
            r = _execute_tool("get_delay_ripple", params, current_user_email)
            tool_results.append({"tool": "get_delay_ripple", "params": params,
                                  "result": r, "summary": r})

    # ══════════════════════════════════════════════════════════════════
    # Step 5: Compose final answer
    # ══════════════════════════════════════════════════════════════════
    _DB_KW = {"booking", "ticket", "schedule", "fare", "route", "seat",
              "train", "metro", "journey", "trip", "history", "reservation",
              "訂票", "班次", "票價", "路線", "座位", "捷運", "列車"}

=======
    for call in tool_calls:
        tool_name = call.get("name", "")
        params = _normalise_tool_params(
            tool_name,
            call.get("params") or call.get("parameters", {}),
        )
=======
>>>>>>> 4836b765bf1e177ac0fef698aec75593eac5dcd5

    if category == "booking" and len(_station_ids) >= 2:
        if not current_user_email and debug:
            debug_info.append("**Pre-login check:** not logged in")
        tool_results = _chain_booking_query(
            _station_ids[0], _station_ids[1], _travel_date, _fare_class,
            _seat_pref, current_user_email, debug_info, debug)
        if not current_user_email:
            tool_results.append({"tool": "login_reminder", "params": {},
                "result": json.dumps({"reminder": "需要登入才能訂票"}),
                "summary": json.dumps({"reminder": "需要登入"})})
        if _ticket_type != "single":
            tool_results.append({"tool": "ticket_type_info", "params": {},
                "result": json.dumps({"requested_ticket_type": _ticket_type}),
                "summary": json.dumps({"requested_ticket_type": _ticket_type})})

    elif category == "route" and len(_station_ids) >= 2:
        opt = "cost" if any(kw in _lower for kw in ["cheap", "cheapest", "最便宜"]) else "time"
        params = {"origin_id": _station_ids[0], "destination_id": _station_ids[1], "optimise_by": opt}
        if debug:
            debug_info.append(f"**Direct call:** find_route({params})")
        r = _execute_tool("find_route", params, current_user_email)
        tool_results.append({"tool": "find_route", "params": params, "result": r, "summary": r})

    elif category == "availability" and len(_station_ids) >= 2:
        o, d = _station_ids[0], _station_ids[1]
        tn = "check_national_rail_availability" if o.startswith("NR") else "check_metro_availability"
        params = {"origin_id": o, "destination_id": d}
        if _travel_date:
            params["travel_date"] = _travel_date
        if debug:
            debug_info.append(f"**Direct call:** {tn}({params})")
        r = _execute_tool(tn, params, current_user_email)
        tool_results.append({"tool": tn, "params": params, "result": r, "summary": r})

    elif category == "fare" and len(_station_ids) >= 2:
        o, d = _station_ids[0], _station_ids[1]
        if o.startswith("NR"):
            params = {"origin_id": o, "destination_id": d}
            if _travel_date:
                params["travel_date"] = _travel_date
            r = _execute_tool("check_national_rail_availability", params, current_user_email)
            tool_results.append({"tool": "check_national_rail_availability", "params": params,
                                  "result": r, "summary": r})
            try:
                data = json.loads(r)
                if isinstance(data, list) and data:
                    s = data[0]
                    fp = {"schedule_id": s["schedule_id"], "fare_class": _fare_class,
                          "stops_travelled": s["stops_travelled"]}
                    fr = _execute_tool("get_national_rail_fare", fp, current_user_email)
                    tool_results.append({"tool": "get_national_rail_fare", "params": fp,
                                          "result": fr, "summary": fr})
            except (json.JSONDecodeError, KeyError):
                pass
        else:
            params = {"origin_id": o, "destination_id": d}
            r = _execute_tool("get_metro_fare", params, current_user_email)
            tool_results.append({"tool": "get_metro_fare", "params": params,
                                  "result": r, "summary": r})

    elif category == "policy":
        params = {"query": user_message}
        if debug:
            debug_info.append(f"**Direct call:** search_policy({params})")
        r = _execute_tool("search_policy", params, current_user_email)
        tool_results.append({"tool": "search_policy", "params": params, "result": r, "summary": r})

    elif category == "personal":
        filtered = _filter_tools(TOOLS, category)
        if llm.get_chat_provider() == "ollama":
            tc = llm.ollama_tool_call(
                history[-4:] if len(history) > 4 else history, filtered, _augmented,
                system_prompt=f"Tool router. User: {current_user_email or 'none'}. "
                              "bookings→get_user_bookings, profile→get_user_profile, "
                              "payment→get_payment_info(booking_id).")
        else:
            tc = [{"name": "get_user_bookings", "params": {}}]
        if debug:
            debug_info.append(f"**Tool selection (filtered {len(filtered)} tools):** {tc}")
        for call in tc:
            n = call.get("name", "")
            p = call.get("params") or {}
            if any(v == "" for v in p.values()):
                continue
            r = _execute_tool(n, p, current_user_email)
            tool_results.append({"tool": n, "params": p, "result": r, "summary": r})

    elif category == "cancel":
        bk = re.search(r'(BK-[A-Z0-9]+)', user_message, re.IGNORECASE)
        if bk:
            params = {"booking_id": bk.group(1)}
            if debug:
                debug_info.append(f"**Direct call:** cancel_booking({params})")
            r = _execute_tool("cancel_booking", params, current_user_email)
            tool_results.append({"tool": "cancel_booking", "params": params,
                                  "result": r, "summary": r})
        else:
            filtered = _filter_tools(TOOLS, category)
            if llm.get_chat_provider() == "ollama":
                tc = llm.ollama_tool_call(history[-4:] if len(history) > 4 else history,
                    filtered, _augmented, system_prompt="Extract booking ID, call cancel_booking.")
            else:
                tc = []
            if debug:
                debug_info.append(f"**Tool selection (filtered):** {tc}")
            for call in tc:
                n = call.get("name", "")
                p = call.get("params") or {}
                r = _execute_tool(n, p, current_user_email)
                tool_results.append({"tool": n, "params": p, "result": r, "summary": r})

    elif category == "delay":
        if _station_ids:
            params = {"station_id": _station_ids[0], "hops": 2}
            if debug:
                debug_info.append(f"**Direct call:** get_delay_ripple({params})")
            r = _execute_tool("get_delay_ripple", params, current_user_email)
            tool_results.append({"tool": "get_delay_ripple", "params": params,
                                  "result": r, "summary": r})

    # ══════════════════════════════════════════════════════════════════
    # Step 5: Compose final answer
    # ══════════════════════════════════════════════════════════════════
    _DB_KW = {"booking", "ticket", "schedule", "fare", "route", "seat",
              "train", "metro", "journey", "trip", "history", "reservation",
              "訂票", "班次", "票價", "路線", "座位", "捷運", "列車"}

<<<<<<< HEAD
        if debug:
            debug_info.append(
                f"**Result (raw):** ```json\n{result_json[:300]}\n```\n"
                f"**Summary sent to LLM:** {summary}"
            )

        tool_results.append(_tool_result(tool_name, params, result_json))

    db_keywords = {
        "booking",
        "ticket",
        "schedule",
        "fare",
        "route",
        "seat",
        "train",
        "metro",
        "journey",
        "trip",
        "history",
        "reservation",
        "訂票",
        "班次",
        "票價",
        "路線",
        "座位",
        "捷運",
        "列車",
    }
    data_block = ""
=======
>>>>>>> 4836b765bf1e177ac0fef698aec75593eac5dcd5
>>>>>>> Stashed changes
    if tool_results:
        data_block = "\n\n".join(
            f"[{tr['tool']}]\n{_normalise_result(tr['tool'], tr['result'])}"
            for tr in tool_results)
        if debug:
            debug_info.append(f"**Data (normalised):**\n{data_block}")
        content = (
            f"DATA FROM TRANSITFLOW DATABASE:\n{data_block}"
            f"\n\nUser asks: {user_message}"
<<<<<<< Updated upstream
            f"\n\nAnswer using only the data above. Use emojis and clear formatting."
            f"\nIf booking query: show ALL schedules, ask which one user wants, "
            f"include schedule_id/station IDs/date in confirmation message.")
    elif any(kw in user_message.lower() for kw in _DB_KW):
        content = (f"User asks: {user_message}\n\n"
                   "No data retrieved. Do NOT invent data. Apologise and suggest alternatives.")
    else:
        content = user_message

    answer = llm.chat(
        messages=history + [{"role": "user", "content": content}],
        system_prompt=contextual_prompt)
=======
<<<<<<< HEAD
            "\n\nAnswer using only the data above. Use emojis and clear formatting."
            "\nIf the user is trying to book and the data includes availability, fares, or seats, "
            "do NOT say the booking is complete. Summarise the available service options, "
            "show the fare and a few available seat IDs, then ask the user to choose/confirm "
            "the exact schedule and seat before booking:"
        )
    elif any(kw in user_message.lower() for kw in db_keywords):
        content = (
            f"User asks: {user_message}\n\n"
            "IMPORTANT: No data was retrieved from the TransitFlow database for this query. "
            "Apologise politely in the user's language and suggest what they can try instead. "
            "Do NOT invent any bookings, fares, schedules, seat numbers, or travel times."
        )
    else:
        content = user_message

    final_messages = history + [{"role": "user", "content": content}]
    try:
        answer = llm.chat(messages=final_messages, system_prompt=contextual_prompt)
    except Exception as exc:
        if tool_results:
            answer = f"目前 LLM 回應失敗；先直接提供資料庫查詢結果：\n\n{data_block}"
        else:
            answer = (
                "目前 LLM 回應失敗，所以我無法產生 AI 回覆。"
                "請確認目前選用的模型服務可用後再試一次。"
            )
        if debug:
            debug_info.append(f"**LLM unavailable:** {exc}")
=======
            f"\n\nAnswer using only the data above. Use emojis and clear formatting."
            f"\nIf booking query: show ALL schedules, ask which one user wants, "
            f"include schedule_id/station IDs/date in confirmation message.")
    elif any(kw in user_message.lower() for kw in _DB_KW):
        content = (f"User asks: {user_message}\n\n"
                   "No data retrieved. Do NOT invent data. Apologise and suggest alternatives.")
    else:
        content = user_message

    answer = llm.chat(
        messages=history + [{"role": "user", "content": content}],
        system_prompt=contextual_prompt)
>>>>>>> 4836b765bf1e177ac0fef698aec75593eac5dcd5
>>>>>>> Stashed changes

    updated_history = history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": answer},
    ]
    if debug:
        return answer, updated_history, "\n\n".join(debug_info)
    return answer, updated_history
