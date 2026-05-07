import json
from functools import lru_cache
from typing import Any

import boto3
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = Field(default="dev", alias="ENVIRONMENT")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    db_secret_arn: str | None = Field(default=None, alias="DB_SECRET_ARN")
    db_proxy_endpoint: str | None = Field(default=None, alias="DB_PROXY_ENDPOINT")
    db_name: str = Field(default="clearpath", alias="DB_NAME")
    db_user: str = Field(default="clearpath_app", alias="DB_USER")
    ghl_webhook_secret: str | None = Field(default=None, alias="GHL_WEBHOOK_SECRET")
    skip_db_init: bool = Field(default=False, alias="SKIP_DB_INIT")

    model_config = SettingsConfigDict(populate_by_name=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def _secrets_client(region: str):
    return boto3.client("secretsmanager", region_name=region)


def _rds_client(region: str):
    return boto3.client("rds", region_name=region)


def fetch_secret_string(secret_ref: str, region: str) -> str:
    if not secret_ref.startswith("arn:"):
        return secret_ref

    response = _secrets_client(region).get_secret_value(SecretId=secret_ref)
    secret = response.get("SecretString")
    if not secret:
        raise RuntimeError("SecretString is empty")
    return secret


def fetch_json_secret(secret_arn: str, region: str) -> dict[str, Any]:
    return json.loads(fetch_secret_string(secret_arn, region))


def generate_iam_auth_token(hostname: str, username: str, region: str, port: int = 5432) -> str:
    return _rds_client(region).generate_db_auth_token(
        DBHostname=hostname,
        Port=port,
        DBUsername=username,
        Region=region,
    )
