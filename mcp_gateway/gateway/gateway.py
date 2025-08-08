# gateway/gateway.py with control + Data planes
import asyncio
import uuid
import httpx
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime

app = FastAPI(title="MCP Gateway")

# -------------------------
# In-memory registries
# -------------------------
# Registered MCP servers: name -> {"url": "...", "meta": {...}, "registered_at": ...}
MCP_REGISTRY: Dict[str, Dict] = {}

# Session manager: session_id -> {server_name, queue, task}
SESSIONS: Dict[str, Dict] = {}

# httpx async client
http_client = httpx.AsyncClient(timeout=30.0)


# -------------------------
# Control plane models
# -------------------------
class RegisterRequest(BaseModel):
    name: str
    base_url: str
    meta: Optional[Dict] = {}


@app.post("/control/register")
async def register(req: RegisterRequest):
    if req.name in MCP_REGISTRY:
        raise HTTPException(status_code=400, detail="name already registered")
    MCP_REGISTRY[req.name] = {
        "url": req.base_url.rstrip("/"),
        "meta": req.meta or {},
        "registered_at": datetime.utcnow().isoformat()
    }
    return {"status": "ok", "registered": req.name}


@app.post("/control/unregister")
async def unregister(body: dict):
    name = body.get("name")
    if not name or name not in MCP_REGISTRY:
        raise HTTPException(status_code=404, detail="not found")
    del MCP_REGISTRY[name]
    return {"status": "ok", "unregistered": name}


@app.get("/control/list")
async def list_servers():
    return {"servers": MCP_REGISTRY}


# -------------------------
# Data plane - Sessions & SSE
# -------------------------
@app.post("/data/connect")
async def data_connect(body: dict):
    """
    Create a session with a registered MCP server.
    body: {"server": "<server_name>"}
    returns: {"session_id": "..."}
    """
    server_name = body.get("server")
    if not server_name or server_name not in MCP_REGISTRY:
        raise HTTPException(status_code=404, detail="server not found")
    session_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    # Create background task that subscribes to backend SSE and forwards to queue
    task = asyncio.create_task(_bridge_backend_stream(session_id, server_name, queue))
    SESSIONS[session_id] = {"server": server_name, "queue": queue, "task": task}
    return {"session_id": session_id, "server": server_name}


async def _bridge_backend_stream(session_id: str, server_name: str, queue: asyncio.Queue):
    """
    Bridge events from backend /stream to the gateway queue.
    If backend not providing SSE, handle failure.
    """
    backend_url = MCP_REGISTRY[server_name]["url"]
    stream_url = f"{backend_url}/stream"
    try:
        async with http_client.stream("GET", stream_url, params={"n": 50}) as resp:
            if resp.status_code != 200:
                await queue.put(json.dumps({"error": "backend stream failed", "status": resp.status_code}))
                return
            async for line in resp.aiter_lines():
                # SSE may include blank lines; parse data: prefixed lines
                if line is None:
                    continue
                if line.startswith("data:"):
                    payload = line[len("data:"):].strip()
                    await queue.put(payload)
    except httpx.RequestError as ex:
        await queue.put(json.dumps({"error": "request error", "detail": str(ex)}))
    except asyncio.CancelledError:
        # session closed, ignore
        return
    finally:
        # final sentinel message
        await queue.put(json.dumps({"event": "backend_stream_closed"}))
        return


@app.get("/data/stream/{session_id}")
async def data_stream(session_id: str, request: Request):
    """
    Expose an SSE endpoint for the client. The gateway will stream events forwarded from backend.
    Client opens this endpoint and receives server events in text/event-stream.
    """
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    q: asyncio.Queue = session["queue"]

    async def event_generator():
        try:
            while True:
                # If client disconnected, stop
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    # heartbeat
                    yield ":\n\n"
                    continue
                # payload is a JSON string; send as SSE
                yield f"data: {payload}\n\n"
                if isinstance(payload, str):
                    try:
                        j = json.loads(payload)
                        if j.get("event") == "backend_stream_closed":
                            break
                    except Exception:
                        pass
        finally:
            # cleanup on stream close: cancel background task and delete session
            await _cleanup_session(session_id)
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/data/request/{session_id}/{method}")
async def data_request(session_id: str, method: str, body: dict):
    """
    Send a request to the backend MCP server for math calls.
    method: add, subtract, multiply, divide
    body: {"a": x, "b": y}
    """
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    server_name = session["server"]
    backend_base = MCP_REGISTRY[server_name]["url"]
    url = f"{backend_base}/math/{method}"
    try:
        resp = await http_client.post(url, json=body, timeout=10.0)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=str(e))
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


# session cleanup helper
async def _cleanup_session(session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        return
    task = session.get("task")
    if task and not task.done():
        task.cancel()
        try:
            await task
        except Exception:
            pass
    # remove session
    SESSIONS.pop(session_id, None)


# Graceful shutdown: close http client
@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()
