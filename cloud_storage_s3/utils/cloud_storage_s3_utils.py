# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""
Thin wrapper around boto3 so ir_attachment.py doesn't import boto3 directly.
Works with any S3-compatible provider (MinIO, AWS S3, ...).
"""
import boto3
from botocore.client import Config


def get_s3_client(endpoint_url, access_key, secret_key, region=None, **kwargs):
    return boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region or 'sg-01',
        config=Config(signature_version='s3v4'),
    )
