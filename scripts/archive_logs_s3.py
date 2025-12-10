#!/usr/bin/env python3
"""Archive rotated logs to S3 for long-term compliance retention."""
import glob
import logging
import os
from datetime import datetime
from pathlib import Path

import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv

# Load env (default to repo root .env)
load_dotenv()

LOG_ARCHIVE_DIR = os.getenv("LOG_ARCHIVE_DIR", "/opt/aitrapp/logs/archive")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
S3_PREFIX = os.getenv("S3_LOG_PREFIX", "compliance_logs")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def upload_to_s3(local_file: str, s3_file: str) -> bool:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    try:
        s3.upload_file(local_file, BUCKET_NAME, s3_file)
        logging.info("Uploaded %s -> s3://%s/%s", local_file, BUCKET_NAME, s3_file)
        return True
    except FileNotFoundError:
        logging.error("File not found: %s", local_file)
        return False
    except NoCredentialsError:
        logging.error("AWS credentials not available")
        return False
    except Exception as e:
        logging.error("Upload failed for %s: %s", local_file, e)
        return False


def main() -> None:
    if not BUCKET_NAME:
        logging.error("S3_BUCKET_NAME not set; aborting archival.")
        return

    archive_path = Path(LOG_ARCHIVE_DIR)
    if not archive_path.exists():
        logging.info("Archive directory does not exist: %s", archive_path)
        return

    files = glob.glob(str(archive_path / "*.gz"))
    if not files:
        logging.info("No compressed log files found to archive in %s", archive_path)
        return

    date_prefix = datetime.utcnow().strftime("%Y/%m/%d")
    for file_path in files:
        filename = os.path.basename(file_path)
        s3_key = f"{S3_PREFIX}/{date_prefix}/{filename}"
        upload_to_s3(file_path, s3_key)
        # Optional cleanup: keep local copy unless CLEANUP_ON_UPLOAD=1
        if os.getenv("CLEANUP_ON_UPLOAD", "0") == "1":
            try:
                os.remove(file_path)
                logging.info("Removed local file after upload: %s", file_path)
            except Exception as e:
                logging.warning("Could not remove %s: %s", file_path, e)


if __name__ == "__main__":
    main()
