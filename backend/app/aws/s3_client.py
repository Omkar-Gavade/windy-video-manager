"""boto3 S3 client factory.

The client is built once per process and reused. Credentials are resolved by
the standard boto3 provider chain (IAM role in production; environment or
shared config locally) — never read or stored by application code.

Signature version ``s3v4`` is pinned so presigned URLs are valid in every
region.
"""

from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config.settings import get_settings


@lru_cache
def get_s3_client():
    """Return a cached, region-bound S3 client configured for presigning."""
    settings = get_settings()
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        config=Config(
            signature_version="s3v4",
            # Virtual-hosted addressing keeps presigned URLs on the regional
            # endpoint (bucket.s3.<region>.amazonaws.com). Without this, buckets
            # outside us-east-1 get a global host that 307-redirects and breaks
            # the SigV4 host signature.
            s3={"addressing_style": "virtual"},
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


def object_exists(key: str) -> bool:
    """Return True if ``key`` exists in the configured bucket.

    A missing object yields ``False``; any other S3 error propagates so the
    service layer can translate it into a storage error.
    """
    settings = get_settings()
    client = get_s3_client()
    try:
        client.head_object(Bucket=settings.s3_bucket, Key=key)
        return True
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise


def generate_presigned_get_url(key: str, expiry: int, disposition: str) -> str:
    """Create a short-lived presigned GET URL for ``key``.

    ``disposition`` sets ``Content-Disposition`` on the response — ``inline``
    for preview (play in the browser) or ``attachment`` for download.
    """
    settings = get_settings()
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": key,
            "ResponseContentDisposition": disposition,
        },
        ExpiresIn=expiry,
    )


def upload_fileobj(fileobj: Any, key: str, content_type: str) -> None:
    """Stream a file-like object to the configured bucket under ``key``.

    ``ContentType`` is set so S3 serves the object with the correct type when
    it is later streamed to an HTML5 player via a presigned URL.
    """
    settings = get_settings()
    client = get_s3_client()
    client.upload_fileobj(
        fileobj,
        settings.s3_bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )


def list_objects(prefix: str) -> list[dict[str, Any]]:
    """List every object under ``prefix`` in the configured bucket.

    Follows the ``ContinuationToken`` so the full set is returned even past the
    1000-object per-response cap. "Folder marker" keys (the prefix itself or
    keys ending in ``/``) are skipped.

    Returns raw object dicts with ``Key``, ``Size``, and ``LastModified``.
    """
    settings = get_settings()
    client = get_s3_client()

    objects: list[dict[str, Any]] = []
    continuation_token: str | None = None

    while True:
        kwargs: dict[str, Any] = {"Bucket": settings.s3_bucket, "Prefix": prefix}
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token

        response = client.list_objects_v2(**kwargs)

        for obj in response.get("Contents", []):
            key = obj["Key"]
            if key == prefix or key.endswith("/"):
                continue
            objects.append(obj)

        if response.get("IsTruncated"):
            continuation_token = response.get("NextContinuationToken")
        else:
            break

    return objects
