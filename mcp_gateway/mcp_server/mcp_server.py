# mcp_server/mcp_server.py
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import uuid
import json
import time

app = FastAPI(title="Sample MCP Math Server")


class MathPayload(BaseModel):
    a: float
    b: float


@app.post("/math/add")
async def add(payload: MathPayload):
    return {"result": payload.a + payload.b}


@app.post("/math/subtract")
async def subtract(payload: MathPayload):
    return {"result": payload.a - payload.b}


@app.post("/math/multiply")
async def multiply(payload: MathPayload):
    return {"result": payload.a * payload.b}


@app.post("/math/divide")
async def divide(payload: MathPayload):
    if payload.b == 0:
        return JSONResponse(status_code=400, content={"error": "division by zero"})
    return {"result": payload.a / payload.b}


# SSE streaming endpoint - emits incremental status updates and can accept a query param "n"
@app.get("/stream")
async def stream(request: Request, n: int = 5):
    """
    Simple SSE that streams n incremental messages with a small delay.
    Useful for testing the gateway streaming capability.
    """
    async def event_generator():
        for i in range(1, n + 1):
            if await request.is_disconnected():
                break
            data = {"event": "progress", "step": i, "total": n, "timestamp": time.time()}
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(0.8)
        # final message
        final = {"event": "done", "timestamp": time.time()}
        yield f"data: {json.dumps(final)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
