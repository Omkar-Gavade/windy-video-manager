"""Shared test configuration.

Sets the environment variables required by ``Settings`` before the application
modules import them, so tests run without a real ``.env`` or AWS account.
"""

import os

os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("S3_BUCKET", "test-bucket")
os.environ.setdefault("S3_PREFIX", "videos/")
