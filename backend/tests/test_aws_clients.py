from pathlib import Path

from app import aws_clients
from app.config import get_settings


def test_local_queue_uses_shared_capitalized_message_keys(tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "local_queue_file", str(tmp_path / "local_queue.txt"))
    monkeypatch.setattr(settings, "smartflow_local", True)

    aws_clients.queue_send('{"order_id": 7}')
    messages = aws_clients.queue_receive()

    assert messages == [{"Body": '{"order_id": 7}', "ReceiptHandle": '{"order_id": 7}'}]
    aws_clients.queue_delete(messages[0]["ReceiptHandle"])
    assert Path(settings.local_queue_file).read_text(encoding="utf-8") == ""


def test_aws_proof_urls_expire_after_five_minutes(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "smartflow_local", False)
    calls = {}

    class S3:
        def generate_presigned_url(self, operation, Params, ExpiresIn):
            calls.update(operation=operation, params=Params, expires=ExpiresIn)
            return "https://example.test/proof"

    monkeypatch.setattr(aws_clients, "_client", lambda service: S3())
    monkeypatch.setattr(settings, "s3_bucket", "smartflow-private")

    assert aws_clients.presign_proof("proof/order-8.jpg") == "https://example.test/proof"
    assert calls == {
        "operation": "get_object",
        "params": {"Bucket": "smartflow-private", "Key": "proof/order-8.jpg"},
        "expires": 300,
    }
