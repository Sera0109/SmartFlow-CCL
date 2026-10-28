import json
import logging
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field

from . import aws_clients, db
from .config import get_settings

logger = logging.getLogger(__name__)

app = FastAPI(title="SmartFlow Delivery API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ORDER_STATUSES = ("Placed", "Assigned", "Out for Delivery", "Delivered")
AGENT_STATUSES = ("Free", "Busy", "Offline")
TRANSITIONS = {
    "Placed": {"Assigned"},
    "Assigned": {"Out for Delivery"},
    "Out for Delivery": {"Delivered"},
    "Delivered": set(),
}


class OrderRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    item: str = Field(min_length=1, max_length=255)
    pickup_lat: float = Field(ge=-90, le=90)
    pickup_lng: float = Field(ge=-180, le=180)
    drop_address: str = Field(min_length=1, max_length=500)


class AgentStatusRequest(BaseModel):
    status: str


def _not_found(message: str = "Resource not found") -> HTTPException:
    return HTTPException(status_code=404, detail=message)


def _get_order(order_id: int) -> dict:
    order = db.fetch_one(
        """SELECT o.*, c.name AS customer_name, c.email AS customer_email,
                  a.name AS agent_name, a.email AS agent_email
           FROM orders o JOIN customers c ON c.id=o.customer_id
           LEFT JOIN agents a ON a.id=o.agent_id WHERE o.id=%s""",
        (order_id,),
    )
    if not order:
        raise _not_found("Order not found")
    order["history"] = db.fetch_all(
        """SELECT status, changed_at FROM delivery_status
           WHERE order_id=%s ORDER BY changed_at, id""",
        (order_id,),
    )
    return order


def _record_status(conn, order_id: int, status: str) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO delivery_status (order_id, status) VALUES (%s, %s)",
            (order_id, status),
        )


def proof_key_for_order(order_id: int) -> str:
    return f"proof/order-{order_id}.jpg"


def _is_jpeg_upload(file: UploadFile) -> bool:
    file.file.seek(0)
    signature = file.file.read(3)
    file.file.seek(0)
    return signature == b"\xff\xd8\xff"


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/orders", status_code=201)
def create_order(request: OrderRequest) -> dict:
    try:
        with db.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO customers (name,email) VALUES (%s,%s)
                       ON DUPLICATE KEY UPDATE name=VALUES(name)""",
                    (request.name, str(request.email)),
                )
                cursor.execute("SELECT id FROM customers WHERE email=%s", (str(request.email),))
                customer_id = cursor.fetchone()["id"]
                cursor.execute(
                    """INSERT INTO orders
                       (customer_id,item,pickup_lat,pickup_lng,drop_address,status)
                       VALUES (%s,%s,%s,%s,%s,'Placed')""",
                    (
                        customer_id,
                        request.item,
                        request.pickup_lat,
                        request.pickup_lng,
                        request.drop_address,
                    ),
                )
                order_id = cursor.lastrowid
                _record_status(conn, order_id, "Placed")
            conn.commit()
        aws_clients.queue_send(json.dumps({"order_id": order_id}))
        return {"order_id": order_id, "status": "Placed"}
    except HTTPException:
        raise
 
    except Exception as exc:
        logger.exception("Order creation failed")
        raise HTTPException(status_code=503, detail="Unable to create order") from exc



@app.get("/orders/{order_id}")
def get_order(order_id: int) -> dict:
    return _get_order(order_id)


@app.get("/agents")
def get_agents() -> list[dict]:
    return db.fetch_all("SELECT id, name, status FROM agents ORDER BY id")


@app.post("/agents/{agent_id}/status")
def update_agent_status(agent_id: int, request: AgentStatusRequest) -> dict:
    if request.status not in AGENT_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid agent status")
    if not db.fetch_one("SELECT id FROM agents WHERE id=%s", (agent_id,)):
        raise _not_found("Agent not found")
    db.execute("UPDATE agents SET status=%s WHERE id=%s", (request.status, agent_id))
    return {"ok": True}


@app.get("/agents/{agent_id}/orders")
def get_agent_orders(agent_id: int) -> list[dict]:
    if not db.fetch_one("SELECT id FROM agents WHERE id=%s", (agent_id,)):
        raise _not_found("Agent not found")
    return db.fetch_all(
        """SELECT * FROM orders
           WHERE agent_id=%s AND status IN ('Assigned', 'Out for Delivery')
           ORDER BY created_at DESC""",
        (agent_id,),
    )


def _transition(order_id: int, target: str) -> dict:
    order = _get_order(order_id)
    if target not in TRANSITIONS[order["status"]]:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot move order from {order['status']} to {target}",
        )
    db.execute("UPDATE orders SET status=%s WHERE id=%s", (target, order_id))
    with db.connection() as conn:
        _record_status(conn, order_id, target)
        conn.commit()
    return _get_order(order_id)


@app.post("/orders/{order_id}/out-for-delivery")
def out_for_delivery(order_id: int) -> dict:
    order = _get_order(order_id)
    if not order.get("agent_id"):
        raise HTTPException(status_code=409, detail="Order has not been assigned")
    _transition(order_id, "Out for Delivery")
    return {"status": "Out for Delivery"}


@app.post("/orders/{order_id}/proof")
def upload_delivery_proof(order_id: int, file: UploadFile = File(...)) -> dict:
    order = _get_order(order_id)
    if order["status"] != "Out for Delivery":
        raise HTTPException(status_code=409, detail="Proof requires an out-for-delivery order")
    if file.content_type != "image/jpeg" or not _is_jpeg_upload(file):
        raise HTTPException(
            status_code=415,
            detail="Delivery proof must be a JPEG image",
        )
    key = proof_key_for_order(order_id)
    try:
        aws_clients.upload_proof(file.file, key, file.content_type)
        with db.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO deliveries (order_id,agent_id,proof_key,delivered_at)
                       VALUES (%s,%s,%s,CURRENT_TIMESTAMP)
                       ON DUPLICATE KEY UPDATE proof_key=VALUES(proof_key),
                       delivered_at=VALUES(delivered_at)""",
                    (order_id, order["agent_id"], key),
                )
                cursor.execute("UPDATE orders SET status='Delivered' WHERE id=%s", (order_id,))
                cursor.execute(
                    "UPDATE agents SET status='Free' WHERE id=%s", (order["agent_id"],)
                )
                _record_status(conn, order_id, "Delivered")
            conn.commit()
        aws_clients.notify("Order delivered", f"Order {order_id} has been delivered.")
        return {"status": "Delivered", "proof_key": key}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to save delivery proof") from exc


@app.get("/orders/{order_id}/proof-url")
def get_proof_url(order_id: int) -> dict[str, str]:
    _get_order(order_id)
    delivery = db.fetch_one("SELECT proof_key FROM deliveries WHERE order_id=%s", (order_id,))
    if not delivery or not delivery["proof_key"]:
        raise _not_found("Delivery proof not found")
    return {"url": aws_clients.presign_proof(delivery["proof_key"])}


@app.get("/analytics")
def analytics() -> dict:
    status_rows = db.fetch_all("SELECT status, COUNT(*) AS count FROM orders GROUP BY status")
    agent_rows = db.fetch_all(
        """SELECT a.name, COUNT(o.id) AS count
           FROM agents a LEFT JOIN orders o ON o.agent_id=a.id
           GROUP BY a.id, a.name ORDER BY a.id"""
    )
    delivery_average = db.fetch_one(
        """SELECT AVG(TIMESTAMPDIFF(SECOND, placed.changed_at, delivered.changed_at)) / 60
           AS avg_delivery_minutes
           FROM delivery_status placed
           JOIN delivery_status delivered ON delivered.order_id=placed.order_id
           WHERE placed.status='Placed' AND delivered.status='Delivered'"""
    ) or {}
    return {
        "by_status": {row["status"]: row["count"] for row in status_rows},
        "per_agent": {row["name"]: row["count"] for row in agent_rows},
        "avg_delivery_minutes": delivery_average.get("avg_delivery_minutes"),
    }


@app.get("/local-proof/{key:path}")
def local_proof(key: str):
    settings = get_settings()
    if not settings.smartflow_local:
        raise _not_found()
    path = Path(settings.local_s3_dir) / key
    if not path.is_file():
        raise _not_found("Proof file not found")
    return FileResponse(path)