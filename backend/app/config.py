from functools import lru_cache
import os
from pathlib import Path

import boto3
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    smartflow_local: bool = True
    aws_region: str = "ap-south-1"
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "smartflow"
    db_password: str = ""
    db_name: str = "smartflow"
    sqs_url: str = ""
    sns_arn: str = ""
    s3_bucket: str = ""
    local_queue_file: str = "local_queue.txt"
    local_s3_dir: str = "local_s3"
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if os.getenv("SMARTFLOW_LOCAL") == "1":
        settings.smartflow_local = True
    if not settings.smartflow_local:
        parameter_names = {
            "db_host": "/smartflow/db_host",
            "db_user": "/smartflow/db_user",
            "db_password": "/smartflow/db_password",
            "db_name": "/smartflow/db_name",
            "sqs_url": "/smartflow/sqs_url",
            "sns_arn": "/smartflow/sns_arn",
            "s3_bucket": "/smartflow/bucket",
        }
        response = boto3.client("ssm", region_name=settings.aws_region).get_parameters(
            Names=list(parameter_names.values()), WithDecryption=True
        )
        values = {item["Name"]: item["Value"] for item in response.get("Parameters", [])}
        for field, name in parameter_names.items():
            if not getattr(settings, field) and name in values:
                setattr(settings, field, values[name])
    return settings