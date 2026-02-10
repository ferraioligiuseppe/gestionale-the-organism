
import os
import boto3
from botocore.exceptions import ClientError

def _env(key: str, default: str = "") -> str:
    v = os.getenv(key)
    return v if v not in (None, "") else default

def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=_env("S3_ACCESS_KEY"),
        aws_secret_access_key=_env("S3_SECRET_KEY"),
        region_name=_env("S3_REGION", "eu-west-1"),
    )

def upload_bytes(data: bytes, key: str, content_type: str = "application/pdf") -> str:
    bucket = _env("S3_BUCKET")
    if not bucket:
        raise RuntimeError("S3_BUCKET mancante")
    s3 = get_s3_client()
    s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
    return key

def presign_get(key: str, expires: int = 86400) -> str:
    bucket = _env("S3_BUCKET")
    s3 = get_s3_client()
    try:
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=int(_env("PRESIGN_EXPIRE_SECONDS", str(expires))),
        )
    except ClientError as e:
        raise RuntimeError(f"Errore presign: {e}")
