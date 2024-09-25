"""Transfer module for streaming job postings to and from S3."""

import asyncio
from collections.abc import AsyncIterable

import boto3
from mypy_boto3_s3.client import S3Client

from jobs import JobPosting, ProcessedJobPosting

CHECK_INTERVAL: int = 30  # new file every minute, check every 30 seconds
S3_CLIENT: S3Client = boto3.client("s3")


def list_new_files(
    *, bucket: str, prefix: str, since_timestamp: int = 0, s3_client: S3Client = S3_CLIENT
) -> list[str]:
    """Lists new files in S3 that have not yet been ingested.

    Returns:
        list[str]: A list of new files to ingest.
    """
    new_files: list[str] = []
    last_file_prefix: str = f"{prefix}/{since_timestamp}.jsonl"
    # only get back files after the last ingested file, this is must faster
    # than listing all files and filtering them out afterwards
    response: dict = s3_client.list_objects_v2(
        Bucket=bucket, Prefix=prefix, StartAfter=last_file_prefix
    )

    for obj in response.get("Contents", []):
        filepath: str = obj["Key"]
        try:
            timestamp, filetype = filepath.split("/")[-1].split(".")
        except ValueError:
            continue
        if not timestamp.isdigit() or int(timestamp) <= since_timestamp or filetype != "jsonl":
            continue
        new_files.append(filepath)

    # shouldn't be necessary in general, but sort files by timestamp to ingest
    # them in the correct order just in case there happens to be more than one
    # new file
    return sorted(new_files, key=lambda filename: int(filename.split("/")[-1].split(".")[0]))


async def get_postings_from_file(
    *, bucket: str, filepath: str, s3_client: S3Client = S3_CLIENT
) -> AsyncIterable[JobPosting]:
    """Reads job postings from a file in S3.

    Yields:
        Iterator[JobPosting]: A generator of job postings.
    """
    obj: dict = s3_client.get_object(Bucket=bucket, Key=filepath)
    # load the data in a separate thread to avoid blocking the event loop
    data = await asyncio.to_thread(obj["Body"].read)

    for line in data.decode("utf-8").splitlines():
        yield JobPosting.model_validate_json(line)


async def upload_postings_from_timestamp(
    *,
    bucket: str,
    prefix: str,
    timestamp: int,
    postings: list[ProcessedJobPosting],
    s3_client: S3Client = S3_CLIENT,
) -> None:
    """Uploads processed job postings to S3."""
    filepath: str = f"{prefix}/{timestamp}.jsonl"
    print(f"Uploading {len(postings)} processed job postings to s3://{bucket}/{filepath}")
    body: str = "\n".join([posting.model_dump_json() for posting in postings])
    await asyncio.to_thread(
        s3_client.put_object,  # The S3 client method to be called in a separate thread
        Bucket=bucket,  # Arguments to pass to the S3 put_object call
        Key=filepath,
        Body=body,
    )
    print(f"Finished uploading s3://{bucket}/{filepath}")


async def stream_new_postings(
    *,
    ingestion_queue: asyncio.Queue,
    save_hash_queue: asyncio.Queue,
    bucket: str,
    prefix: str,
    start_timestamp: int,
    s3_client: S3Client = S3_CLIENT,
) -> None:
    """Streams new job postings from S3 to the ingestion queue."""
    while True:
        print(f"Checking for new files, last ingested timestamp: {start_timestamp}")

        # list all new files that haven't been ingested yet
        new_files: list[str] = list_new_files(
            bucket=bucket, prefix=prefix, since_timestamp=start_timestamp, s3_client=s3_client
        )

        if not new_files:
            # only wait if no new files are found
            print("No new files found. Waiting for the next check...")
            await asyncio.sleep(CHECK_INTERVAL)
            continue

        for filepath in new_files:
            print(f"Found new file to ingest: {filepath}")
            timestamp: int = int(filepath.split("/")[-1].split(".")[0])
            hashes: list[int] = []
            async for posting in get_postings_from_file(
                bucket=bucket, filepath=filepath, s3_client=s3_client
            ):
                await ingestion_queue.put(posting)
                hashes.append(hash(posting))

            # the hash for the original posting must match the hash for the
            # processed one
            await save_hash_queue.put((timestamp, hashes))
            print(f"Finished ingesting file: {filepath}")

        start_timestamp = timestamp
