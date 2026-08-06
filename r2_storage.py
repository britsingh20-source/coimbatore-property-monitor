"""Cloudflare R2 (S3-compatible) storage helpers for the own-stock library and
owner-supplied property footage.

Two footguns this module exists to close, both of which have bitten this repo
before:

1. In GitHub Actions, ``${{ vars.X }}`` only resolves values set under
   Settings -> Secrets and variables -> Actions -> **Variables**. If X was
   actually added under **Secrets** (as R2_ACCOUNT_ID, R2_ACCESS_KEY_ID,
   R2_SECRET_ACCESS_KEY, and R2_BUCKET_NAME are here), ``vars.X`` silently
   resolves to an empty string rather than failing the workflow. The fix is
   at the workflow level -- read these via ``secrets.*``, not ``vars.*`` (see
   .github/workflows/generate-video.yml and seed-stock-library.yml) -- but
   this module is the second line of defence.
2. An empty-string env var (`FOO=""`) is still "set" as far as
   ``os.environ.get("FOO") is not None`` is concerned, so a naive check lets
   a blank value slip through and reach boto3 as e.g. ``Bucket=""``, which
   fails in a way that's easy to swallow with a bare except and never notice.
   Every credential lookup here goes through `_env()`, which treats blank
   (or whitespace-only) values exactly the same as unset.
"""

from __future__ import annotations

import os
from pathlib import Path

REQUIRED_VARS = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME")


def _env(name: str) -> str | None:
    """Read an env var, treating '', whitespace-only, and unset identically as None."""
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def r2_configured() -> bool:
    missing = [name for name in REQUIRED_VARS if not _env(name)]
    if missing:
        print(f"R2 not configured -- missing/blank: {', '.join(missing)}")
        return False
    return True


def _client():
    import boto3

    account_id = _env("R2_ACCOUNT_ID")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=_env("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=_env("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )


def download_prefix(prefix: str, destination: Path) -> int:
    """Download every object under `prefix` in the bucket into `destination`.

    Returns the number of files downloaded. Returns 0 (without raising) if R2
    isn't configured, so callers can treat R2 as an optional accelerator/cache
    rather than a hard dependency.
    """
    if not r2_configured():
        return 0
    bucket = _env("R2_BUCKET_NAME")
    client = _client()
    destination.mkdir(parents=True, exist_ok=True)
    prefix = prefix.rstrip("/") + "/"
    count = 0
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue
            relative = key[len(prefix):]
            if not relative:
                continue
            local_path = destination / relative
            local_path.parent.mkdir(parents=True, exist_ok=True)
            client.download_file(bucket, key, str(local_path))
            count += 1
    print(f"Downloaded {count} object(s) from r2://{bucket}/{prefix}")
    return count


def upload_prefix(local_dir: Path, prefix: str, skip_names: frozenset = frozenset({".gitkeep", "README.md"})) -> int:
    """Upload every file under `local_dir` to `prefix` in the bucket.

    Returns the number of files uploaded. Returns 0 (without raising) if R2
    isn't configured.
    """
    if not r2_configured():
        return 0
    if not local_dir.exists():
        return 0
    bucket = _env("R2_BUCKET_NAME")
    client = _client()
    prefix = prefix.rstrip("/")
    count = 0
    for path in local_dir.rglob("*"):
        if path.is_dir() or path.name in skip_names:
            continue
        relative = path.relative_to(local_dir).as_posix()
        key = f"{prefix}/{relative}"
        client.upload_file(str(path), bucket, key)
        count += 1
    print(f"Uploaded {count} object(s) to r2://{bucket}/{prefix}")
    return count


def sync_library_down(local_dir: Path = Path("assets/library")) -> int:
    """Pull the shared stock-cache library down from R2 before a run."""
    return download_prefix("stock-cache/library", local_dir)


def sync_library_up(local_dir: Path = Path("assets/library")) -> int:
    """Push any newly-cached stock media back up to R2 after a run."""
    return upload_prefix(local_dir, "stock-cache/library")


def sync_own_footage_down(local_dir: Path = Path("assets/properties")) -> int:
    """Pull owner-supplied per-property photos/footage down from R2 before a run."""
    return download_prefix("own-footage", local_dir)
