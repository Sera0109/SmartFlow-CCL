from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import quote

import boto3

from .config import get_settings


def _client(service: str) -> Any:
    return boto3.client(service, region_name=get_settings().aws_region)


def notify(subject: str, message: str) -> None:
    settings = get_settings()
    if settings.smartflow_local:
        print(f"[SmartFlow notification] {subject}: {message}")
        return
    if not settings.sns_arn:
        raise RuntimeError("SNS topic is not configured")
    _client("sns").publish(TopicArn=settings.sns_arn, Subject=subject[:100], Message=message)


def queue_send(body: str) -> None:
    settings = get_settings()
    if settings.smartflow_local:
        path = Path(settings.local_queue_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(body + "\n")
        return
    if not settings.sqs_url:
        raise RuntimeError("SQS queue is not configured")
    _client("sqs").send_message(QueueUrl=settings.sqs_url, MessageBody=body)


def queue_receive() -> list[dict[str, str]]:
    settings = get_settings()
    if settings.smartflow_local:
        path = Path(settings.local_queue_file)
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        return [
            {"Body": line, "ReceiptHandle": line}
            for line in lines
            if line
        ]
    if not settings.sqs_url:
        raise RuntimeError("SQS queue is not configured")
    response = _client("sqs").receive_message(
        QueueUrl=settings.sqs_url, MaxNumberOfMessages=10, WaitTimeSeconds=20
    )
    return [
        {"Body": item["Body"], "ReceiptHandle": item["ReceiptHandle"]}
        for item in response.get("Messages", [])
    ]


def queue_delete(handle: str) -> None:
    settings = get_settings()
    if settings.smartflow_local:
        path = Path(settings.local_queue_file)
        if not path.exists():
            return
        lines = path.read_text(encoding="utf-8").splitlines()
        try:
            lines.remove(handle)
        except ValueError:
            return
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        return
    _client("sqs").delete_message(QueueUrl=settings.sqs_url, ReceiptHandle=handle)


def upload_proof(fileobj: BinaryIO, key: str, content_type: str) -> None:
    settings = get_settings()
    if settings.smartflow_local:
        path = Path(settings.local_s3_dir) / key
        path.parent.mkdir(parents=True, exist_ok=True)
        fileobj.seek(0)
        path.write_bytes(fileobj.read())
        return
    _client("s3").upload_fileobj(
        fileobj,
        settings.s3_bucket,
        key,
        ExtraArgs={"ContentType": content_type, "ServerSideEncryption": "AES256"},
    )


def presign_proof(key: str) -> str:
    settings = get_settings()
    if settings.smartflow_local:
        return f"/local-proof/{quote(key)}"
    return _client("s3").generate_presigned_url(
        "get_object", Params={"Bucket": settings.s3_bucket, "Key": key}, ExpiresIn=300
    )