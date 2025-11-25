from typing import AsyncGenerator, Optional

import aioboto3
from botocore.client import BaseClient

from app.core.config import settings


async def create_client(
    resource: str, region_name: Optional[str] = None, profile_name: Optional[str] = None
) -> AsyncGenerator[BaseClient, None]:
    """
    Async factory to create an aioboto3 client using credentials from settings.

    Args:
        resource (str): AWS service name (e.g., 's3').
        region_name (Optional[str]): Region to use. Defaults to settings.aws_region.
        profile_name (Optional[str]): AWS profile name if needed.

    Yields:
        AsyncGenerator[BaseClient]: An async context-managed aioboto3 client.
    """
    session_kwargs = {}
    if profile_name:
        session_kwargs["profile_name"] = profile_name

    session = aioboto3.Session(**session_kwargs)
    async with session.client(
        resource,
        region_name=region_name or settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    ) as client:
        yield client


# upload to s3 and return the url
async def upload_to_s3(
    file_obj, bucket_name: str = settings.aws_bucket, object_name: Optional[str] = None
) -> str:
    """
    Upload a file-like object to an S3 bucket and return the URL.
    """
    async for s3_client in create_client("s3"):
        await s3_client.upload_fileobj(file_obj, bucket_name, object_name)
        return f"https://{bucket_name}.s3.amazonaws.com/{object_name}"


async def delete_from_s3(bucket_name: str, object_name: str) -> None:
    """
    Delete an object from an S3 bucket.
    """
    async for s3_client in create_client("s3"):
        await s3_client.delete_object(Bucket=bucket_name, Key=object_name)
