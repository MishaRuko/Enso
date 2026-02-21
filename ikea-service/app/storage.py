from __future__ import annotations

import os
from io import BytesIO

import httpx

_client = None


def _is_configured() -> bool:
    return bool(os.environ.get("DO_SPACES_KEY") and os.environ.get("DO_SPACES_SECRET"))


def _get_s3_client():
    global _client
    if _client is None:
        import boto3

        _client = boto3.client(
            "s3",
            region_name=os.environ["DO_SPACES_REGION"],
            endpoint_url=f"https://{os.environ['DO_SPACES_REGION']}.digitaloceanspaces.com",
            aws_access_key_id=os.environ["DO_SPACES_KEY"],
            aws_secret_access_key=os.environ["DO_SPACES_SECRET"],
        )
    return _client


def _get_bucket() -> str:
    return os.environ["DO_SPACES_BUCKET"]


def _public_url(key: str) -> str:
    region = os.environ["DO_SPACES_REGION"]
    bucket = _get_bucket()
    return f"https://{bucket}.{region}.digitaloceanspaces.com/{key}"


async def download_and_upload_model(
    item_code: str, source_url: str, fmt: str = "glb"
) -> str | None:
    """Download a 3D model from IKEA CDN and upload to DigitalOcean Spaces.

    Returns the public URL of the uploaded file, or None if DO Spaces is not configured.
    """
    if not _is_configured():
        return None

    async with httpx.AsyncClient() as client:
        resp = await client.get(source_url, follow_redirects=True)
        resp.raise_for_status()
        data = resp.content

    key = f"models/{item_code}.{fmt}"
    content_types = {"glb": "model/gltf-binary", "usdz": "model/vnd.usdz+zip"}

    s3 = _get_s3_client()
    s3.upload_fileobj(
        BytesIO(data),
        _get_bucket(),
        key,
        ExtraArgs={
            "ContentType": content_types.get(fmt, "application/octet-stream"),
            "ACL": "public-read",
        },
    )

    return _public_url(key)


def model_exists(item_code: str, fmt: str = "glb") -> str | None:
    """Check if a model already exists in storage. Returns URL if it does."""
    if not _is_configured():
        return None

    key = f"models/{item_code}.{fmt}"
    s3 = _get_s3_client()
    try:
        s3.head_object(Bucket=_get_bucket(), Key=key)
        return _public_url(key)
    except s3.exceptions.ClientError:
        return None
