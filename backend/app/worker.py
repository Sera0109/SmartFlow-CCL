import json
import time

from . import aws_clients, db
from .assignment import choose_best_agent


def process_message(message: dict[str, str]) -> bool:
    payload = json.loads(message["Body"])
    order_id = int(payload["order_id"])
    with db.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM orders WHERE id=%s FOR UPDATE", (order_id,)
            )
            order = cursor.fetchone()
            if not order or order["status"] != "Placed":
                conn.rollback()
                return True
            cursor.execute(
                """SELECT a.*, COUNT(CASE WHEN o.status IN ('Assigned','Out for Delivery')
                    THEN o.id END) AS active_order_count
                    FROM agents a LEFT JOIN orders o ON o.agent_id=a.id
                    GROUP BY a.id"""
            )
            agent = choose_best_agent(cursor.fetchall(), float(order["pickup_lat"]), float(order["pickup_lng"]))
            if not agent:
                conn.rollback()
                return False
            cursor.execute(
                "UPDATE orders SET agent_id=%s,status='Assigned' WHERE id=%s",
                (agent["id"], order_id),
            )
            cursor.execute("UPDATE agents SET status='Busy' WHERE id=%s", (agent["id"],))
            cursor.execute(
                "INSERT INTO delivery_status (order_id,status) VALUES (%s,'Assigned')",
                (order_id,),
            )
        conn.commit()
    aws_clients.notify("Order assigned", f"Order {order_id} assigned to agent {agent['name']}.")
    return True


def run_worker(poll_seconds: int = 5) -> None:
    while True:
        messages = aws_clients.queue_receive()
        if not messages:
            time.sleep(poll_seconds)
            continue
        for message in messages:
            try:
                if process_message(message):
                    aws_clients.queue_delete(message["ReceiptHandle"])
            except Exception as exc:
                print(f"Worker error; message will be retried: {exc}")


if __name__ == "__main__":
    run_worker()