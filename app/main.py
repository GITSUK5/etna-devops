import asyncio
import random
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.requests import Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from .chaos import MODES, activate, get_mode, reset as chaos_reset
from .database import get_conn, init_db
from .metrics import (
    CONTENT_TYPE_LATEST,
    REQUEST_COUNT,
    REQUEST_LATENCY,
    generate_latest,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="order-service", version="1.0.0", lifespan=lifespan)

_SKIP_PATHS = {"/health", "/metrics", "/chaos"}


class OrderIn(BaseModel):
    item: str
    quantity: int


class ChaosIn(BaseModel):
    mode: Optional[str] = None


@app.middleware("http")
async def middleware(request: Request, call_next):
    if request.url.path in _SKIP_PATHS:
        return await call_next(request)

    start = time.perf_counter()
    mode = get_mode()

    if mode == "slow_response":
        await asyncio.sleep(random.uniform(3, 8))
    elif mode == "high_error_rate" and random.random() < 0.7:
        REQUEST_COUNT.labels(request.method, request.url.path, "500").inc()
        return JSONResponse(
            status_code=500, content={"detail": "chaos: high_error_rate"}
        )

    response = await call_next(request)
    duration = time.perf_counter() - start

    REQUEST_COUNT.labels(
        request.method, request.url.path, str(response.status_code)
    ).inc()
    REQUEST_LATENCY.labels(request.url.path).observe(duration)

    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/orders")
def list_orders():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM orders").fetchall()
    return [dict(r) for r in rows]


@app.post("/orders", status_code=201)
def create_order(order: OrderIn):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO orders (item, quantity) VALUES (?, ?)",
            (order.item, order.quantity),
        )
        order_id = cur.lastrowid
    return {"id": order_id, **order.model_dump(), "status": "pending"}


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="order not found")
    return dict(row)


@app.post("/chaos")
def trigger_chaos(body: Optional[ChaosIn] = Body(default=None)):
    if body is None or body.mode is None:
        mode = random.choice(MODES)
    elif body.mode == "reset":
        chaos_reset()
        return {"mode": "reset", "status": "chaos disabled"}
    else:
        mode = body.mode

    try:
        activated = activate(mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"mode": activated, "status": "chaos activated"}
