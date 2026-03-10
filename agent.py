import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

import streamlit as st
client = Groq(api_key=st.secrets["GROQ_API_KEY"])


# ─────────────────────────────────────────────
#  HELPERS — safe parsing of messy real-world data
# ─────────────────────────────────────────────

def safe_float(value):
    """Parse currency/numeric strings like '$1,200', '1200.50', 'N/A' safely."""
    if not value:
        return None
    cleaned = re.sub(r"[^\d.]", "", str(value).replace(",", ""))
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def safe_text(value):
    """Return stripped text or None for empty/null values."""
    if value is None:
        return None
    v = str(value).strip()
    return v if v and v.lower() not in ("null", "n/a", "-", "") else None


def normalize_status(value):
    """Normalize inconsistent status strings."""
    if not value:
        return "Unknown"
    v = str(value).strip().lower()
    mappings = {
        "done": "Completed", "complete": "Completed", "completed": "Completed",
        "in progress": "In Progress", "in-progress": "In Progress", "wip": "In Progress",
        "stuck": "Stuck", "blocked": "Stuck",
        "not started": "Not Started", "new": "Not Started",
        "won": "Won", "closed won": "Won",
        "lost": "Lost", "closed lost": "Lost",
        "proposal": "Proposal", "negotiation": "Negotiation",
        "qualified": "Qualified", "lead": "Lead"
    }
    return mappings.get(v, value.strip().title())


def get_col(item, *title_keywords):
    """
    Find a column value by trying multiple keyword matches (case-insensitive).
    Returns the first non-empty match across all keywords.
    Also tries exact match first, then partial match.
    """
    cols = item.get("column_values", [])
    for keyword in title_keywords:
        kw = keyword.lower()
        # Exact title match first
        for col in cols:
            if col["column"]["title"].lower() == kw:
                v = safe_text(col.get("text"))
                if v:
                    return v
        # Partial match fallback
        for col in cols:
            if kw in col["column"]["title"].lower():
                v = safe_text(col.get("text"))
                if v:
                    return v
    return None


def get_all_col_values(item):
    """Return dict of {column_title: text} for all columns — used for diagnostics."""
    return {
        col["column"]["title"]: col.get("text", "")
        for col in item.get("column_values", [])
    }


def detect_column_map(items, board_name):
    """
    Scan the first few items of a board to discover actual column names.
    Returns a dict of {role: actual_column_title} for key fields.
    This handles boards where columns are named differently than expected.
    """
    if not items:
        return {}

    # Collect all column titles from first 5 items
    all_titles = set()
    for item in items[:5]:
        for col in item.get("column_values", []):
            t = col["column"]["title"].strip()
            if t:
                all_titles.add(t)

    col_map = {}

    VALUE_KEYWORDS = ["budget", "value", "amount", "revenue", "price", "deal value",
                      "contract", "cost", "total", "fee", "worth"]
    STATUS_KEYWORDS = ["status", "stage", "phase", "state", "pipeline stage", "deal stage"]
    OWNER_KEYWORDS = ["owner", "person", "assigned", "salesperson", "rep", "manager",
                      "account manager", "contact", "lead owner", "deal owner"]
    SECTOR_KEYWORDS = ["sector", "industry", "vertical", "segment", "category", "type",
                       "market", "domain"]
    CLIENT_KEYWORDS = ["client", "customer", "company", "account", "organization", "org"]
    DATE_KEYWORDS = ["close", "date", "deadline", "due", "expected", "target date"]

    def find_best(keywords):
        for kw in keywords:
            for title in all_titles:
                if kw == title.lower():
                    return title
        for kw in keywords:
            for title in all_titles:
                if kw in title.lower():
                    return title
        return None

    col_map["value"] = find_best(VALUE_KEYWORDS)
    col_map["status"] = find_best(STATUS_KEYWORDS)
    col_map["owner"] = find_best(OWNER_KEYWORDS)
    col_map["sector"] = find_best(SECTOR_KEYWORDS)
    col_map["client"] = find_best(CLIENT_KEYWORDS)
    col_map["date"] = find_best(DATE_KEYWORDS)

    return col_map


# ─────────────────────────────────────────────
#  DATA EXTRACTION — both boards
# ─────────────────────────────────────────────

def get_col_by_title(item, exact_title):
    """Get column value by exact title (used after column map detection)."""
    if not exact_title:
        return None
    for col in item.get("column_values", []):
        if col["column"]["title"] == exact_title:
            return safe_text(col.get("text"))
    return None


def extract_all_metrics(data):
    """
    Extract metrics from both Deals and Work Orders boards.
    Uses dynamic column detection to handle any column naming convention.
    Returns structured metrics + data quality report.
    """
    boards = data.get("boards", [])

    deals = []
    work_orders = []
    quality_issues = []
    board_diagnostics = []

    # Deduplicate boards: if same name appears twice (e.g. "Work Orders Tracker"),
    # pick the one with more items
    seen_boards = {}
    for board in boards:
        name = board.get("name", "")
        item_count = len(board.get("items_page", {}).get("items", []))
        if name not in seen_boards or item_count > len(seen_boards[name].get("items_page", {}).get("items", [])):
            seen_boards[name] = board

    for board_name, board in seen_boards.items():
        items = board.get("items_page", {}).get("items", [])
        if not items:
            continue

        # Auto-detect column names for this board
        col_map = detect_column_map(items, board_name)
        board_diagnostics.append({
            "board": board_name,
            "item_count": len(items),
            "detected_columns": col_map
        })

        # ── DEALS BOARD ──
        if "deal" in board_name.lower():
            value_missing = 0
            owner_missing = 0

            for item in items:
                name = safe_text(item.get("name"))

                # Use detected column map, fall back to keyword search
                raw_value = (
                    get_col_by_title(item, col_map.get("value"))
                    or get_col(item, "budget", "deal value", "value", "amount", "revenue", "price", "contract value")
                )
                value = safe_float(raw_value)

                raw_status = (
                    get_col_by_title(item, col_map.get("status"))
                    or get_col(item, "status", "stage", "deal stage", "pipeline stage", "phase")
                )
                status = normalize_status(raw_status)

                raw_owner = (
                    get_col_by_title(item, col_map.get("owner"))
                    or get_col(item, "owner", "person", "assigned to", "salesperson", "rep", "account manager", "deal owner")
                )
                owner = safe_text(raw_owner)

                raw_sector = (
                    get_col_by_title(item, col_map.get("sector"))
                    or get_col(item, "sector", "industry", "vertical", "segment", "market", "category")
                )
                sector = safe_text(raw_sector)

                close_date = (
                    get_col_by_title(item, col_map.get("date"))
                    or get_col(item, "close date", "closing date", "expected close", "target date", "close", "date")
                )

                if value is None:
                    value_missing += 1
                if not owner:
                    owner_missing += 1

                deals.append({
                    "name": name or "Unnamed",
                    "value": value or 0,
                    "status": status,
                    "owner": owner or "Unassigned",
                    "sector": sector or "Unknown",
                    "close_date": close_date
                })

            if value_missing:
                quality_issues.append(f"{value_missing}/{len(items)} deals in '{board_name}' have no parseable value (detected column: '{col_map.get('value', 'none')}').")
            if owner_missing:
                quality_issues.append(f"{owner_missing}/{len(items)} deals in '{board_name}' have no assigned owner (detected column: '{col_map.get('owner', 'none')}').")

        # ── WORK ORDERS BOARD ──
        elif any(kw in board_name.lower() for kw in ["work", "order", "project", "tracker"]):
            revenue_missing = 0

            for item in items:
                name = safe_text(item.get("name"))

                raw_revenue = (
                    get_col_by_title(item, col_map.get("value"))
                    or get_col(item, "revenue", "contract value", "value", "amount", "total", "budget", "price", "fee")
                )
                revenue = safe_float(raw_revenue)

                raw_status = (
                    get_col_by_title(item, col_map.get("status"))
                    or get_col(item, "status", "stage", "phase", "state", "progress")
                )
                status = normalize_status(raw_status)

                client_name = (
                    get_col_by_title(item, col_map.get("client"))
                    or get_col(item, "client", "customer", "company", "account", "organization")
                )

                raw_sector = (
                    get_col_by_title(item, col_map.get("sector"))
                    or get_col(item, "sector", "industry", "vertical", "segment", "market", "category", "type")
                )
                sector = safe_text(raw_sector)

                assignee = (
                    get_col_by_title(item, col_map.get("owner"))
                    or get_col(item, "owner", "person", "assigned", "manager", "lead", "pilot", "engineer")
                )

                if revenue is None:
                    revenue_missing += 1

                work_orders.append({
                    "name": name or "Unnamed",
                    "revenue": revenue or 0,
                    "status": status,
                    "client": safe_text(client_name) or "Unknown",
                    "sector": sector or "Unknown",
                    "assignee": safe_text(assignee) or "Unassigned"
                })

            if revenue_missing:
                quality_issues.append(f"{revenue_missing}/{len(items)} work orders in '{board_name}' have no parseable revenue (detected column: '{col_map.get('value', 'none')}').")

    # ── DEAL METRICS ──
    total_pipeline = sum(d["value"] for d in deals)
    won_deals = [d for d in deals if d["status"] == "Won"]
    won_value = sum(d["value"] for d in won_deals)
    deals_by_status = {}
    deals_by_owner = {}
    deals_by_sector = {}

    for d in deals:
        deals_by_status[d["status"]] = deals_by_status.get(d["status"], 0) + 1
        deals_by_owner[d["owner"]] = deals_by_owner.get(d["owner"], {"count": 0, "value": 0})
        deals_by_owner[d["owner"]]["count"] += 1
        deals_by_owner[d["owner"]]["value"] += d["value"]
        deals_by_sector[d["sector"]] = deals_by_sector.get(d["sector"], {"count": 0, "value": 0})
        deals_by_sector[d["sector"]]["count"] += 1
        deals_by_sector[d["sector"]]["value"] += d["value"]

    # ── WORK ORDER METRICS ──
    total_wo_revenue = sum(w["revenue"] for w in work_orders)
    completed_orders = [w for w in work_orders if w["status"] == "Completed"]
    completed_revenue = sum(w["revenue"] for w in completed_orders)
    wo_by_status = {}
    wo_by_sector = {}

    for w in work_orders:
        wo_by_status[w["status"]] = wo_by_status.get(w["status"], 0) + 1
        wo_by_sector[w["sector"]] = wo_by_sector.get(w["sector"], {"count": 0, "revenue": 0})
        wo_by_sector[w["sector"]]["count"] += 1
        wo_by_sector[w["sector"]]["revenue"] += w["revenue"]

    return {
        "deals": {
            "raw": deals,
            "total_count": len(deals),
            "total_pipeline_value": total_pipeline,
            "won_count": len(won_deals),
            "won_value": won_value,
            "by_status": deals_by_status,
            "by_owner": deals_by_owner,
            "by_sector": deals_by_sector,
        },
        "work_orders": {
            "raw": work_orders,
            "total_count": len(work_orders),
            "total_revenue": total_wo_revenue,
            "completed_count": len(completed_orders),
            "completed_revenue": completed_revenue,
            "by_status": wo_by_status,
            "by_sector": wo_by_sector,
        },
        "quality_issues": quality_issues[:20],
        "board_diagnostics": board_diagnostics,
        "cross_board": {
            "combined_revenue": total_wo_revenue + won_value,
            "sectors_in_both": list(
                set(deals_by_sector.keys()) & set(wo_by_sector.keys()) - {"Unknown"}
            )
        }
    }


def format_metrics_for_prompt(metrics):
    """Convert metrics dict into a readable text block for the LLM prompt."""
    d = metrics["deals"]
    w = metrics["work_orders"]
    cb = metrics["cross_board"]

    # Deals section
    status_lines = "\n".join(f"  - {s}: {c}" for s, c in sorted(d["by_status"].items(), key=lambda x: -x[1]))
    owner_lines = "\n".join(
        f"  - {o}: {v['count']} deals, ${v['value']:,.0f}" for o, v in sorted(d["by_owner"].items(), key=lambda x: -x[1]["value"])
    )
    sector_lines_d = "\n".join(
        f"  - {s}: {v['count']} deals, ${v['value']:,.0f}" for s, v in sorted(d["by_sector"].items(), key=lambda x: -x[1]["value"])
    )

    # Work orders section
    wo_status_lines = "\n".join(f"  - {s}: {c}" for s, c in sorted(w["by_status"].items(), key=lambda x: -x[1]))
    sector_lines_w = "\n".join(
        f"  - {s}: {v['count']} orders, ${v['revenue']:,.0f}" for s, v in sorted(w["by_sector"].items(), key=lambda x: -x[1]["revenue"])
    )

    quality_text = (
        "\n".join(f"  - {q}" for q in metrics["quality_issues"])
        if metrics["quality_issues"]
        else "  No significant issues detected."
    )

    return f"""
=== DEALS PIPELINE ===
Total Deals: {d['total_count']}
Total Pipeline Value: ${d['total_pipeline_value']:,.2f}
Won Deals: {d['won_count']} (${d['won_value']:,.2f})
Win Rate: {(d['won_count']/d['total_count']*100 if d['total_count'] else 0):.1f}%

By Stage/Status:
{status_lines}

By Owner (deals + value):
{owner_lines}

By Sector (deals + value):
{sector_lines_d}

=== WORK ORDERS ===
Total Work Orders: {w['total_count']}
Total Revenue: ${w['total_revenue']:,.2f}
Completed: {w['completed_count']} (${w['completed_revenue']:,.2f})
Completion Rate: {(w['completed_count']/w['total_count']*100 if w['total_count'] else 0):.1f}%

By Status:
{wo_status_lines}

By Sector (orders + revenue):
{sector_lines_w}

=== CROSS-BOARD INSIGHTS ===
Combined Revenue (Won Deals + Completed Orders): ${cb['combined_revenue']:,.2f}
Sectors active in both boards: {', '.join(cb['sectors_in_both']) or 'None identified'}

=== DATA QUALITY NOTES ===
{quality_text}
"""


# ─────────────────────────────────────────────
#  MAIN AGENT — with conversation history
# ─────────────────────────────────────────────

def ask_agent(question, data, chat_history=None):
    """
    Use Groq LLM to answer a founder-level business question.
    Supports multi-turn conversation via chat_history.

    Args:
        question: Current user question
        data: Raw monday.com API response dict (with 'data' key)
        chat_history: List of {"role": "user"/"assistant", "content": "..."} dicts

    Returns:
        str: Markdown-formatted answer
    """
    if chat_history is None:
        chat_history = []

    metrics = extract_all_metrics(data["data"])
    metrics_text = format_metrics_for_prompt(metrics)

    system_prompt = f"""You are a senior business intelligence analyst embedded with a founder/executive team.

You have access to live data from two monday.com boards: a Deals Pipeline and a Work Orders tracker.
Here is the latest computed data snapshot:

{metrics_text}

Your job:
- Answer founder-level business questions clearly and concisely
- Reference specific numbers from the data above
- If a question is vague (e.g. "how's it going?"), ask ONE targeted clarifying question
- If data is missing or low-quality, say so — don't make up numbers
- When relevant, connect insights across both boards (e.g. deals won vs orders executing)
- Format responses with Markdown: use ### headings, bullet points, and **bold** for key numbers
- Do NOT write code. Do NOT repeat the raw data back. Provide insight and interpretation.

Structure your responses as:
### Summary
One-sentence direct answer.

### Key Numbers
The most important metrics relevant to the question.

### Insights
2-4 analytical observations, including cross-board patterns where relevant.

### Data Caveats
Only if there are real quality issues affecting this answer. Skip section if data is clean.
"""

    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history (last 10 turns to stay within context)
    for turn in chat_history[-10:]:
        messages.append({"role": turn["role"], "content": turn["content"]})

    # Add current question
    messages.append({"role": "user", "content": question})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=1024,
            temperature=0.3
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"⚠️ Error generating response: {str(e)}\n\nPlease check your GROQ_API_KEY and try again."


def generate_leadership_update(data):
    """
    Generate a pre-formatted leadership/board update from current data.
    Suitable for pasting into Slack, email, or a presentation.
    """
    metrics = extract_all_metrics(data["data"])
    metrics_text = format_metrics_for_prompt(metrics)

    prompt = f"""You are preparing a weekly leadership update for a drone services company.

Using this data:
{metrics_text}

Write a concise, professional leadership update in this format:

## 📊 Weekly Business Update

**Pipeline Health**
- [Key deals metrics, top opportunities, pipeline value]

**Operations**
- [Work orders status, completion rate, any blockers]

**Top Sectors This Period**
- [Which sectors are performing, any trends]

**Wins & Risks**
- ✅ [2-3 wins or positives]
- ⚠️ [1-2 risks or watch items]

**Recommended Actions**
- [2-3 concrete next steps for leadership]

Keep it under 300 words. Be specific with numbers. Write for a non-technical executive audience.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.2
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Could not generate leadership update: {str(e)}"
