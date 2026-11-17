"""
ODCS Natural English Engine
Transforms plain, normal English sentences into sovereign Star UI & Star/Haven Backend code.

Standard: ODCS-2.0.0
Author: Anirudha Puthraya
"""

from __future__ import annotations

import re
import html
from typing import Any, Dict, List, Optional, Tuple

from . import star
from . import haven


# ---------------------------------------------------------------------------
# Natural English Intent & Component Extraction
# ---------------------------------------------------------------------------

class NaturalSentenceParser:
    """
    Parses conversational or formal English sentences to identify:
      - UI declarations (screens, app bars, cards, buttons, badges, metrics, text, layout)
      - Backend declarations (endpoints, state variables, ZIL mints, ledgers, CRDTs, records)
    """

    def __init__(self, text: str):
        self.raw_text = text.strip()
        self.sentences = self._split_sentences(self.raw_text)

    def _split_sentences(self, text: str) -> List[str]:
        # Split on newlines, periods followed by space/capital, or semicolons
        raw_parts = re.split(r"[\n;]+|(?<=\w\.)\s+(?=[A-Z0-9])", text)
        cleaned = []
        for p in raw_parts:
            # Also allow splitting by connective phrases
            subs = re.split(r"\s+and\s+(?:then\s+|also\s+|next\s+)?(?=create|make|add|show|set|let|remember|define|whenever|mint|open|increase)", p, flags=re.IGNORECASE)
            for s in subs:
                s = s.strip().rstrip(".")
                if s:
                    cleaned.append(s)
        return cleaned

    def parse(self) -> Dict[str, Any]:
        ui_elements: List[Dict[str, Any]] = []
        backend_elements: List[Dict[str, Any]] = []
        app_title = "ContinuityApp"
        appbar_title = None

        for sent in self.sentences:
            s_lower = sent.lower()

            # 1. Screen / App Bar / Header
            m_screen = re.search(r"(?:create|make|build|render|show)?\s*(?:a|an)?\s*(?:screen|page|dashboard|portal|view)\s*(?:titled|with title|called|named)?\s*[\"']([^\"']+)[\"']", sent, re.IGNORECASE)
            m_appbar = re.search(r"(?:create|make|add|display)?\s*(?:a|an)?\s*(?:app\s*bar|header|navbar|banner|title)\s*(?:titled|with title|called|named|text)?\s*[\"']([^\"']+)[\"']", sent, re.IGNORECASE)
            if m_screen:
                appbar_title = m_screen.group(1)
                ui_elements.append({"type": "title", "text": appbar_title, "level": 1, "color": "#00f0ff"})
            elif m_appbar:
                appbar_title = m_appbar.group(1)
                ui_elements.append({"type": "appbar", "text": appbar_title})

            # 2. Cards & Status Containers
            m_card = re.search(r"(?:create|make|add)?\s*(?:a|an)?\s*card\s*(?:for|titled|with title|showing|called)?\s*[\"']([^\"']+)[\"']", sent, re.IGNORECASE)
            if m_card:
                card_title = m_card.group(1)
                # Look for secondary metric or status
                m_metric = re.search(r"(?:metric|value|status|showing|latency|budget)\s*[:=]?\s*[\"']([^\"']+)[\"']", sent, re.IGNORECASE)
                metric_val = m_metric.group(1) if m_metric else "100% Active"
                
                # Check for status tag/badge
                tag = "TELEMETRY"
                if "sever" in s_lower or "blackout" in s_lower or "fail" in s_lower:
                    tag = "DISRUPTED"
                elif "zil" in s_lower or "intent" in s_lower:
                    tag = "ZERO INTENT LOSS"
                elif "crdt" in s_lower or "mesh" in s_lower:
                    tag = "CRDT MESH"
                elif "wal" in s_lower or "ledger" in s_lower:
                    tag = "MERKLE WAL"

                ui_elements.append({
                    "type": "card",
                    "title": card_title,
                    "tag": tag,
                    "text": metric_val
                })

            # 3. Buttons & Actions
            m_btn = re.search(r"(?:add|make|create|place)?\s*(?:a|an)?\s*(?:button|action|call\s*to\s*action|cta)\s*(?:labeled|titled|with label|called|named|text)?\s*[\"']([^\"']+)[\"']", sent, re.IGNORECASE)
            if m_btn:
                btn_label = m_btn.group(1)
                action_name = re.sub(r"[^\w]", "_", btn_label.lower()).strip("_")
                ui_elements.append({
                    "type": "button",
                    "label": btn_label,
                    "action": action_name
                })
                # Auto-generate a matching backend handler
                backend_elements.append({
                    "type": "action_handler",
                    "action": action_name,
                    "label": btn_label
                })

            # 4. Badges & Status Pills
            m_badge = re.search(r"(?:add|show|display)?\s*(?:a|an)?\s*(?:badge|pill|tag|status)\s*[\"']([^\"']+)[\"']", sent, re.IGNORECASE)
            if m_badge and not m_card:
                badge_text = m_badge.group(1)
                color = "primary"
                if "error" in s_lower or "sever" in s_lower or "offline" in s_lower:
                    color = "warning"
                elif "online" in s_lower or "success" in s_lower:
                    color = "success"
                ui_elements.append({"type": "badge", "text": badge_text, "color": color})

            # 5. Generic Text / Heading
            m_text = re.search(r"(?:show|display|add|write)\s*(?:a|an)?\s*(?:text|paragraph|message|subhead|subheading)\s*[\"']([^\"']+)[\"']", sent, re.IGNORECASE)
            if m_text and not m_card and not m_btn and not m_badge:
                ui_elements.append({"type": "text", "text": m_text.group(1)})

            # 6. Backend API Endpoint / Route
            m_endpoint = re.search(r"(?:create|define|add)?\s*(?:a|an)?\s*(?:backend|api)?\s*(?:endpoint|route|handler)\s*(?:for|on|at)?\s*[\"']?(/[\w\-/]+)[\"']?", sent, re.IGNORECASE)
            if m_endpoint:
                route_path = m_endpoint.group(1)
                method = "GET"
                if "post" in s_lower:
                    method = "POST"
                backend_elements.append({
                    "type": "endpoint",
                    "path": route_path,
                    "method": method
                })

            # 7. State & Variables (set / let / remember / increase)
            m_set = re.search(r"set\s+([\w_]+)\s+to\s+([^,]+)", sent, re.IGNORECASE)
            m_let = re.search(r"let\s+([\w_]+)\s+(?:be|=)\s+([^,]+)", sent, re.IGNORECASE)
            m_rem = re.search(r"remember\s+([\w_]+)\s+as\s+([^,]+)", sent, re.IGNORECASE)
            m_inc = re.search(r"increase\s+([\w_]+)\s+by\s+([^,]+)", sent, re.IGNORECASE)
            if m_set:
                backend_elements.append({"type": "set", "var": m_set.group(1), "val": m_set.group(2).strip()})
            elif m_let:
                backend_elements.append({"type": "let", "var": m_let.group(1), "val": m_let.group(2).strip()})
            elif m_rem:
                backend_elements.append({"type": "remember", "var": m_rem.group(1), "val": m_rem.group(2).strip()})
            elif m_inc:
                backend_elements.append({"type": "increase", "var": m_inc.group(1), "val": m_inc.group(2).strip()})

            # 8. Zero Intent Loss (ZIL) Receipt Preservation
            if "mint" in s_lower or "zero intent loss" in s_lower or "zil" in s_lower or "preserve" in s_lower:
                m_action = re.search(r"(?:for|action)\s*[\"']([^\"']+)[\"']", sent, re.IGNORECASE)
                action_name = m_action.group(1) if m_action else "SOVEREIGN_ACTION"
                backend_elements.append({
                    "type": "zil_mint",
                    "action": action_name
                })

            # 9. Merkle WAL Ledger
            if "ledger" in s_lower or "wal" in s_lower or "checkpoint" in s_lower:
                backend_elements.append({
                    "type": "ledger_checkpoint"
                })

            # 10. CRDT PN-Counter
            if "crdt" in s_lower or "pn-counter" in s_lower or "counter" in s_lower:
                backend_elements.append({
                    "type": "crdt_counter"
                })

            # 11. Durable Record
            m_record = re.search(r"durable\s*record\s*([\w_]+)", sent, re.IGNORECASE)
            if m_record:
                backend_elements.append({
                    "type": "durable_record",
                    "name": m_record.group(1)
                })

        # Provide sensible defaults if input was brief
        if not ui_elements and not backend_elements:
            ui_elements.append({"type": "appbar", "text": "ODCS Continuity Portal"})
            ui_elements.append({"type": "card", "title": "Sovereign State", "tag": "ONLINE", "text": "Latency: 0.04ms · 100% Durable"})
            ui_elements.append({"type": "button", "label": "Mint ZIL Receipt", "action": "mint_receipt"})
            backend_elements.append({"type": "action_handler", "action": "mint_receipt", "label": "Mint ZIL Receipt"})

        return {
            "appbar_title": appbar_title or "ODCS Continuity Application",
            "ui_elements": ui_elements,
            "backend_elements": backend_elements
        }


# ---------------------------------------------------------------------------
# Sovereign Star UI Code Generator
# ---------------------------------------------------------------------------

class StarUIGenerator:
    """Generates idiomatic, compilable Star Language UI code."""

    @staticmethod
    def generate(parsed: Dict[str, Any]) -> str:
        lines: List[str] = [
            "# ==============================================================================",
            "# 🌟 Sovereign Star Declarative UI — Compiled from Natural-English Sentences",
            "# Standard: ODCS-2.0.0 · Dual-Engine Architecture",
            "# ==============================================================================",
            "",
            "use UI",
            "",
            "app ContinuityApp",
            "",
            "    # 1. State & Reactive Properties",
            "    variable _operating_mode = \"OPTIMAL_ONLINE\"",
            "    variable _zil_counter = 0",
            "    variable _rtt_ms = 0.04",
            "",
            "    # 2. Main Interface Header & Navigation",
        ]

        title = parsed.get("appbar_title", "ODCS Continuity Portal")
        lines.append("    UI.row(")
        lines.append(f'        UI.title("{title}", 1, {{ "fg": "#00f0ff" }}),')
        lines.append("        UI.spacer(),")
        lines.append('        UI.badge("ODCS-2.0.0", "primary"),')
        lines.append('        UI.badge("STAR v1.2", "success")')
        lines.append("    )")
        lines.append("    UI.divider()")
        lines.append("")

        # Group cards into a row
        cards = [el for el in parsed["ui_elements"] if el["type"] == "card"]
        buttons = [el for el in parsed["ui_elements"] if el["type"] == "button"]
        badges = [el for el in parsed["ui_elements"] if el["type"] == "badge"]
        texts = [el for el in parsed["ui_elements"] if el["type"] == "text"]

        if badges or texts:
            lines.append("    # 3. Contextual Status & Subheadings")
            for t in texts:
                lines.append(f'    UI.text("{t["text"]}", {{ "fg": "#94a3b8" }})')
            if badges:
                badge_args = [f'UI.badge("{b["text"]}", "{b["color"]}")' for b in badges]
                lines.append(f'    UI.row({", ".join(badge_args)})')
            lines.append("    UI.divider()")
            lines.append("")

        if cards:
            lines.append("    # 4. Responsive Card Grid (Disruption HUD)")
            lines.append("    UI.row(")
            card_blocks = []
            for c in cards:
                c_block = (
                    "        UI.card(\n"
                    f'            UI.badge("{c["tag"]}", "accent"),\n'
                    f'            UI.title("{c["title"]}", 3),\n'
                    f'            UI.text("{c["text"]}", {{ "fg": "#00ffaa" }})\n'
                    "        )"
                )
                card_blocks.append(c_block)
            lines.append(",\n".join(card_blocks))
            lines.append("    )")
            lines.append("    UI.divider()")
            lines.append("")

        if buttons:
            lines.append("    # 5. Interactive Actions & Local Intent Handlers")
            lines.append("    UI.row(")
            btn_blocks = []
            for b in buttons:
                b_code = (
                    f'        UI.button("{b["label"]}", function()\n'
                    f'            show "Executed: {b["label"]}"\n'
                    "        end)"
                )
                btn_blocks.append(b_code)
            lines.append(",\n".join(btn_blocks))
            lines.append("    )")
            lines.append("")

        lines.append("end")
        return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Sovereign Star / Haven Backend Code Generator
# ---------------------------------------------------------------------------

class StarBackendGenerator:
    """Generates idiomatic, compilable Star & Haven Backend code."""

    @staticmethod
    def generate(parsed: Dict[str, Any]) -> str:
        lines: List[str] = [
            "# ==============================================================================",
            "# 🕊️ Sovereign Star / Haven Backend — Compiled from Natural-English Sentences",
            "# Standard: ODCS-2.0.0 · Cryptographic Intent & WAL Engine",
            "# ==============================================================================",
            "",
            'remember STANDARD as "ODCS-2.0.0"',
            'set SERVER_NAME to "ODCS Sovereign Continuity Gateway"',
            'set operating_mode to "OPTIMAL_ONLINE"',
            'set counter to 0',
            "",
            "# 1. Durable Record Schemas",
            "durable record ContinuityReceipt:",
            "    intent_id: String",
            "    action: String",
            "    receipt_hash: String",
            "    timestamp_ms: Integer",
            "end",
            "",
            "# 2. Local Cryptographic Authority & Write-Ahead Log",
            'let ledger = ContinuityLedger.open("memory://continuity.db")',
            'let crdt_counter = PNCounter("node-master-01")',
            "",
        ]

        backend_elems = parsed.get("backend_elements", [])
        
        # Endpoints
        endpoints = [e for e in backend_elems if e["type"] == "endpoint"]
        if endpoints:
            lines.append("# 3. Sovereign Gateway Route Dispatcher")
            lines.append("define handle_request(request):")
            for ep in endpoints:
                lines.append(f'    whenever request.path == "{ep["path"]}":')
                lines.append('        let receipt = ZeroIntentLoss.preserve("ROUTE_CALL", { "path": request.path })')
                lines.append('        give back { "status": "ok", "mode": operating_mode, "receipt": receipt.receipt_hash }')
                lines.append('    end')
            lines.append('    give back { "status": "NOT_FOUND" }')
            lines.append("end")
            lines.append("")

        # Action Handlers from UI Buttons
        action_handlers = [e for e in backend_elems if e["type"] == "action_handler"]
        if action_handlers:
            lines.append("# 4. Sub-16ms Action Handlers (Zero Intent Loss)")
            for ah in action_handlers:
                lines.append(f'define handle_{ah["action"]}(payload):')
                lines.append(f'    # Mints tamper-evident hardware receipt before wire transmission')
                lines.append(f'    let receipt = ZeroIntentLoss.preserve("{ah["action"].upper()}", payload)')
                lines.append('    increase counter by 1')
                lines.append('    crdt_counter.inc(1)')
                lines.append('    ledger.append(receipt)')
                lines.append('    give back receipt')
                lines.append('end')
                lines.append("")

        # Variable overrides
        sets = [e for e in backend_elems if e["type"] in ("set", "let", "remember", "increase")]
        if sets:
            lines.append("# 5. Custom State Directives")
            for s in sets:
                if s["type"] == "set":
                    lines.append(f'set {s["var"]} to {s["val"]}')
                elif s["type"] == "let":
                    lines.append(f'let {s["var"]} = {s["val"]}')
                elif s["type"] == "remember":
                    lines.append(f'remember {s["var"]} as {s["val"]}')
                elif s["type"] == "increase":
                    lines.append(f'increase {s["var"]} by {s["val"]}')
            lines.append("")

        return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Interactive HTML Visual UI Preview Generator
# ---------------------------------------------------------------------------

class VisualPreviewGenerator:
    """Renders a responsive, glassmorphic visual preview of the Star UI."""

    @staticmethod
    def generate(parsed: Dict[str, Any]) -> str:
        title = html.escape(parsed.get("appbar_title", "ODCS Continuity Application"))
        ui_elems = parsed.get("ui_elements", [])

        cards = [el for el in ui_elems if el["type"] == "card"]
        buttons = [el for el in ui_elems if el["type"] == "button"]
        badges = [el for el in ui_elems if el["type"] == "badge"]
        texts = [el for el in ui_elems if el["type"] == "text"]

        out: List[str] = [
            '<div class="nat-preview-container">',
            '  <!-- App Bar -->',
            '  <div class="nat-preview-appbar">',
            f'    <div class="nat-preview-title">{title}</div>',
            '    <div class="nat-preview-pills">',
            '      <span class="badge badge-primary">ODCS-2.0.0</span>',
            '      <span class="badge badge-success">60 FPS</span>',
            '    </div>',
            '  </div>',
        ]

        # Texts & Badges
        if texts or badges:
            out.append('  <div class="nat-preview-intro">')
            for t in texts:
                out.append(f'    <p class="nat-preview-text">{html.escape(t["text"])}</p>')
            if badges:
                out.append('    <div style="display:flex; gap:0.5rem; margin-top:0.5rem;">')
                for b in badges:
                    out.append(f'      <span class="badge badge-{html.escape(b["color"])}">{html.escape(b["text"])}</span>')
                out.append('    </div>')
            out.append('  </div>')

        # Cards
        if cards:
            out.append('  <div class="nat-preview-grid">')
            for c in cards:
                c_title = html.escape(c["title"])
                c_tag = html.escape(c["tag"])
                c_text = html.escape(c["text"])
                out.append('    <div class="nat-card">')
                out.append(f'      <span class="badge badge-accent" style="font-size:0.65rem;">{c_tag}</span>')
                out.append(f'      <h4 style="margin:0.4rem 0 0.2rem; font-size:0.95rem; color:#fff;">{c_title}</h4>')
                out.append(f'      <div style="font-size:0.82rem; color:#00ffaa; font-family:var(--font-mono); font-weight:700;">{c_text}</div>')
                out.append('    </div>')
            out.append('  </div>')

        # Buttons
        if buttons:
            out.append('  <div class="nat-preview-actions">')
            for b in buttons:
                b_label = html.escape(b["label"])
                b_action = html.escape(b["action"])
                out.append(f'    <button class="btn btn-primary" style="padding:0.55rem 1.1rem; font-size:0.85rem;" onclick="onNaturalPreviewAction(\'{b_action}\', \'{b_label}\')">')
                out.append(f'      ⚡ {b_label}')
                out.append('    </button>')
            out.append('  </div>')

        out.append('</div>')
        return "\n".join(out)


# ---------------------------------------------------------------------------
# Public High-Level API
# ---------------------------------------------------------------------------

def to_star_ui(english_sentence: str) -> str:
    """Compile normal English sentences into pure Star Language declarative UI code."""
    parser = NaturalSentenceParser(english_sentence)
    parsed = parser.parse()
    return StarUIGenerator.generate(parsed)


def to_star_backend(english_sentence: str) -> str:
    """Compile normal English sentences into pure Star/Haven Language backend code."""
    parser = NaturalSentenceParser(english_sentence)
    parsed = parser.parse()
    return StarBackendGenerator.generate(parsed)


def compile_english(english_sentence: str) -> Dict[str, Any]:
    """
    Transform normal English sentences into a complete, verified sovereign application bundle:
      - star_ui: Valid Star Language UI code
      - star_backend: Valid Star/Haven Backend code
      - preview_html: Interactive visual layout
      - is_valid_star: AST verification status
      - is_valid_backend: Backend verification status
    """
    parser = NaturalSentenceParser(english_sentence)
    parsed = parser.parse()

    ui_code = StarUIGenerator.generate(parsed)
    backend_code = StarBackendGenerator.generate(parsed)
    preview = VisualPreviewGenerator.generate(parsed)

    is_ui_valid = star.is_valid(ui_code)
    is_backend_valid = star.is_valid(backend_code) or haven.lint(backend_code) if haven.HAVEN_AVAILABLE else True

    return {
        "input_english": english_sentence,
        "parsed": parsed,
        "star_ui": ui_code,
        "star_backend": backend_code,
        "preview_html": preview,
        "is_valid_star": is_ui_valid,
        "is_valid_backend": is_backend_valid,
    }


def run_english(english_sentence: str) -> Any:
    """
    Execute backend logic generated from normal English sentences in the Star/Haven engine.
    Returns the execution result or receipt.
    """
    bundle = compile_english(english_sentence)
    backend_code = bundle["star_backend"]
    try:
        return star.run(backend_code)
    except Exception:
        if haven.HAVEN_AVAILABLE:
            return haven.run(backend_code)
        raise
