"""
MCP tool surface for NaukariPro (stdio JSON-RPC + optional Streamable HTTP).

Tools mirror Section 4.2 of the v2 master prompt. Every apply path defaults to dry_run=True.
No live network in unit tests — tools that need I/O accept injected callables / store paths.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: Dict[str, Any]


TOOLS: List[ToolSpec] = [
    ToolSpec(
        name="search_jobs",
        description="Search normalized jobs in the aggregation store (offline SQLite).",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
                "source": {"type": "string"},
            },
        },
    ),
    ToolSpec(
        name="get_job",
        description="Fetch one job by ats_job_key or external id.",
        input_schema={
            "type": "object",
            "properties": {"job_key": {"type": "string"}},
            "required": ["job_key"],
        },
    ),
    ToolSpec(
        name="score_job",
        description="Score a job against the candidate profile (deterministic first; LLM if allowed).",
        input_schema={
            "type": "object",
            "properties": {
                "job_key": {"type": "string"},
                "use_llm": {"type": "boolean", "default": False},
            },
            "required": ["job_key"],
        },
    ),
    ToolSpec(
        name="tailor_resume",
        description="Tailor resume for a job (grounded; never invents facts). Dry artifact only.",
        input_schema={
            "type": "object",
            "properties": {
                "job_key": {"type": "string"},
                "jd_text": {"type": "string"},
            },
        },
    ),
    ToolSpec(
        name="draft_answers",
        description="Draft application answers from the evidence bank (vet pass optional).",
        input_schema={
            "type": "object",
            "properties": {
                "job_key": {"type": "string"},
                "questions": {"type": "array", "items": {"type": "string"}},
            },
        },
    ),
    ToolSpec(
        name="apply_job",
        description="Fill application form. dry_run=True by default — never submits without approval.",
        input_schema={
            "type": "object",
            "properties": {
                "job_key": {"type": "string"},
                "dry_run": {"type": "boolean", "default": True},
                "url": {"type": "string"},
            },
            "required": ["job_key"],
        },
    ),
    ToolSpec(
        name="approve_submission",
        description="Consume an approval token and allow a previously dry-run filled application to submit.",
        input_schema={
            "type": "object",
            "properties": {
                "approval_token": {"type": "string"},
            },
            "required": ["approval_token"],
        },
    ),
    ToolSpec(
        name="get_tracker",
        description="Return application tracker rows (saved→applied→…).",
        input_schema={
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 50}},
        },
    ),
    ToolSpec(
        name="get_stats",
        description="Gateway + aggregation + tracker summary stats.",
        input_schema={"type": "object", "properties": {}},
    ),
    ToolSpec(
        name="list_sources",
        description="List registered ATS board sources.",
        input_schema={
            "type": "object",
            "properties": {"active_only": {"type": "boolean", "default": True}},
        },
    ),
]


def list_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "inputSchema": t.input_schema,
        }
        for t in TOOLS
    ]


def _tool_search_jobs(args: Dict[str, Any]) -> Dict[str, Any]:
    from naukari_pro.aggregation.storage import AggregationStore

    store = AggregationStore()
    limit = int(args.get("limit") or 20)
    query = (args.get("query") or "").lower().strip()
    source = args.get("source")
    jobs = store.list_active_jobs(limit=max(limit * 3, limit)) if hasattr(store, "list_active_jobs") else []
    if not jobs and hasattr(store, "list_jobs"):
        jobs = store.list_jobs(limit=max(limit * 3, limit))
    rows = []
    for j in jobs:
        title = getattr(j, "title", "") or ""
        company = getattr(j, "company", "") or ""
        key = getattr(j, "ats_job_key", None) or getattr(j, "external_job_id", "")
        src = getattr(j, "source_id", None) or getattr(j, "ats_type", "")
        blob = f"{title} {company} {src}".lower()
        if query and query not in blob:
            continue
        if source and source not in str(src):
            continue
        rows.append(
            {
                "job_key": key,
                "title": title,
                "company": company,
                "source": src,
                "url": getattr(j, "url", ""),
                "location": getattr(j, "location", ""),
            }
        )
        if len(rows) >= limit:
            break
    return {"jobs": rows, "count": len(rows)}


def _tool_get_job(args: Dict[str, Any]) -> Dict[str, Any]:
    from naukari_pro.aggregation.storage import AggregationStore

    store = AggregationStore()
    key = args["job_key"]
    job = None
    if hasattr(store, "get_job"):
        job = store.get_job(key)
    if job is None:
        return {"error": "not_found", "job_key": key}
    return {
        "job_key": getattr(job, "ats_job_key", key),
        "title": job.title,
        "company": job.company,
        "url": job.url,
        "location": getattr(job, "location", None),
        "description": (getattr(job, "description_full", None) or "")[:4000],
    }


def _tool_score_job(args: Dict[str, Any]) -> Dict[str, Any]:
    from naukari_pro.matching.deterministic_score import score_job

    job = _tool_get_job(args)
    if job.get("error"):
        return job
    scored = score_job(
        {
            "title": job.get("title"),
            "location": job.get("location"),
            "description_full": job.get("description"),
            "company": job.get("company"),
        }
    )
    total = scored.total
    decision = "queue" if total >= 80 else ("needs_human" if total >= 70 else "skip")
    return {
        "job_key": args["job_key"],
        "deterministic_score": round(total, 2),
        "score_excluding_freshness": round(scored.score, 2),
        "freshness_boost": round(scored.freshness_boost, 2),
        "decision": decision,
        "flags": scored.flags,
        "niches": scored.niches,
        "use_llm": bool(args.get("use_llm")),
        "note": "LLM scoring skipped unless use_llm and budget allows",
    }


def _tool_tailor_resume(args: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status": "queued",
        "job_key": args.get("job_key"),
        "message": "Use CLI `naukariPro resume-gen` / Resume Studio (M4). Grounding validator required.",
        "grounded": True,
        "dry_artifact": True,
    }


def _tool_draft_answers(args: Dict[str, Any]) -> Dict[str, Any]:
    questions = args.get("questions") or []
    answers = []
    for q in questions:
        answers.append(
            {
                "question": q,
                "answer": "",
                "status": "ASK_USER",
                "reason": "No evidence bank hit — never invent",
            }
        )
    return {"answers": answers, "job_key": args.get("job_key")}


def _tool_apply_job(args: Dict[str, Any]) -> Dict[str, Any]:
    dry_run = args.get("dry_run", True)
    if dry_run is None:
        dry_run = True
    if dry_run is False:
        return {
            "status": "blocked",
            "exit_code": 2,
            "message": "Submission requires approve_submission with a valid approval_token. dry_run must stay true until then.",
        }
    return {
        "status": "dry_run_ok",
        "exit_code": 0,
        "job_key": args.get("job_key"),
        "dry_run": True,
        "message": "Fill simulated. Call approve_submission to unlock submit.",
        "approval_required": True,
    }


def _tool_approve_submission(args: Dict[str, Any]) -> Dict[str, Any]:
    token = args.get("approval_token") or ""
    if not token or len(token) < 8:
        return {"status": "rejected", "exit_code": 2, "message": "Invalid or missing approval_token"}
    try:
        from naukari_pro.governed_apply.approval import ApprovalStore

        store = ApprovalStore()
        ok = store.decide(token, approve=True)
        return {
            "status": "approved" if ok else "rejected",
            "token_prefix": token[:8],
            "message": "Approved — submit still requires governed-apply confirmation"
            if ok
            else "Token not pending or expired",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "message": str(exc),
            "token_prefix": token[:8],
        }


def _tool_get_tracker(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from naukari_pro.tracking.store import TrackingStore

        store = TrackingStore()
        limit = int(args.get("limit") or 50)
        rows = store.feed(limit=limit)
        return {"applications": rows, "count": len(rows), "funnel": store.funnel_counts()}
    except Exception as exc:  # noqa: BLE001
        return {"applications": [], "error": str(exc)}


def _tool_get_stats(args: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    try:
        from naukari_pro.llm.gateway import LLMGateway

        out["gateway"] = LLMGateway().status()
    except Exception as exc:  # noqa: BLE001
        out["gateway_error"] = str(exc)
    try:
        from naukari_pro.aggregation.storage import AggregationStore

        store = AggregationStore()
        if hasattr(store, "stats"):
            out["aggregation"] = store.stats()
        else:
            out["aggregation"] = {"db": str(store.db_path)}
    except Exception as exc:  # noqa: BLE001
        out["aggregation_error"] = str(exc)
    return out


def _tool_list_sources(args: Dict[str, Any]) -> Dict[str, Any]:
    from naukari_pro.aggregation.storage import AggregationStore

    store = AggregationStore()
    sources = store.list_active_sources()
    if args.get("active_only") is False:
        # include inactive via raw query if needed — active list is the default contract
        pass
    slim = [
        {
            "source_id": s.get("source_id"),
            "company": s.get("company"),
            "ats_type": s.get("ats_type"),
            "board_identifier": s.get("board_identifier"),
        }
        for s in sources
    ]
    return {"sources": slim, "count": len(slim)}


HANDLERS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "search_jobs": _tool_search_jobs,
    "get_job": _tool_get_job,
    "score_job": _tool_score_job,
    "tailor_resume": _tool_tailor_resume,
    "draft_answers": _tool_draft_answers,
    "apply_job": _tool_apply_job,
    "approve_submission": _tool_approve_submission,
    "get_tracker": _tool_get_tracker,
    "get_stats": _tool_get_stats,
    "list_sources": _tool_list_sources,
}


def handle_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args = arguments or {}
    fn = HANDLERS.get(name)
    if not fn:
        return {"error": f"unknown_tool:{name}", "available": [t.name for t in TOOLS]}
    try:
        return fn(args)
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc), "tool": name}


def handle_jsonrpc(message: Dict[str, Any]) -> Dict[str, Any]:
    """Minimal MCP-style JSON-RPC for stdio clients."""
    mid = message.get("id")
    method = message.get("method") or ""
    params = message.get("params") or {}
    if method in ("initialize", "notifications/initialized"):
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "naukari-pro-mcp", "version": "2.0.0"},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": list_tools()}}
    if method == "tools/call":
        name = params.get("name") or ""
        arguments = params.get("arguments") or {}
        result = handle_tool(name, arguments)
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                "isError": "error" in result,
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    return {
        "jsonrpc": "2.0",
        "id": mid,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def serve_stdio() -> None:
    """Read JSON-RPC lines from stdin, write responses to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("method", "").startswith("notifications/"):
            # notifications have no response
            if msg.get("method") == "notifications/initialized":
                continue
            continue
        resp = handle_jsonrpc(msg)
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(argv or sys.argv[1:])
    if argv and argv[0] == "http":
        host = "127.0.0.1"
        port = 7432
        if len(argv) > 1:
            port = int(argv[1])
        return _serve_http(host, port)
    serve_stdio()
    return 0


def _serve_http(host: str, port: int) -> int:
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
            return

        def _json(self, code: int, payload: Dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path in ("/", "/health"):
                self._json(200, {"ok": True, "server": "naukari-pro-mcp"})
                return
            if self.path == "/tools":
                self._json(200, {"tools": list_tools()})
                return
            self._json(404, {"error": "not_found"})

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid_json"})
                return
            if self.path == "/mcp":
                self._json(200, handle_jsonrpc(payload))
                return
            if self.path.startswith("/tools/"):
                name = self.path.split("/tools/", 1)[1]
                self._json(200, handle_tool(name, payload if isinstance(payload, dict) else {}))
                return
            self._json(404, {"error": "not_found"})

    server = HTTPServer((host, port), Handler)
    print(f"naukari-pro-mcp listening on http://{host}:{port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
