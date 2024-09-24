import asyncio
from collections import defaultdict

import grpc
import redis.asyncio as redis

import seniority_pb2
import seniority_pb2_grpc
from config import (
    BUCKET,
    DOWNLOAD_PREFIX,
    GRPC_HOST,
    GRPC_PORT,
    REDIS_HOST,
    REDIS_PORT,
    UPLOAD_PREFIX,
)
from jobs import JobPosting, ProcessedJobPosting
from transfer import stream_new_postings, upload_postings_from_timestamp

CACHE_BATCH_SIZE = 1000
INFERENCE_BATCH_SIZE = 1000
LOG_PRINT_INTERVAL = 100


class SeniorityClient:
    def __init__(
        self,
        *,
        redis_client: redis.Redis,
        grpc_channel: grpc.aio.Channel,
        ingestion_queue: asyncio.Queue,
        save_hash_queue: asyncio.Queue,
    ) -> None:
        self.redis_client = redis_client
        self.grpc_stub = seniority_pb2_grpc.SeniorityModelStub(grpc_channel)
        self.ingestion_queue: asyncio.Queue = ingestion_queue
        self.save_hash_queue: asyncio.Queue = save_hash_queue
        self.inference_queue: asyncio.Queue = asyncio.Queue()
        self.save_queue: asyncio.Queue = asyncio.Queue()

    async def run_queues(self) -> None:
        """Monitors and processes all queues."""
        ingestion_task = asyncio.create_task(self.consume_ingestion_queue(CACHE_BATCH_SIZE))
        inference_task = asyncio.create_task(self.consume_inference_queue(INFERENCE_BATCH_SIZE))
        save_task = asyncio.create_task(self.consume_save_queue())

        await asyncio.gather(ingestion_task, inference_task, save_task)

    async def consume_ingestion_queue(self, batch_size: int) -> None:
        cache_read_dict: dict[str, list[JobPosting]] = defaultdict(list)
        while True:
            job_posting = await self.ingestion_queue.get()
            cache_key = job_posting.cache_key
            cache_read_dict[cache_key].append(job_posting)
            if len(cache_read_dict) >= batch_size or self.ingestion_queue.empty():
                # read cache all at once to reduce the number of calls
                redis_values = await self.redis_client.mget(cache_read_dict.keys())
                for key, cached_value in zip(cache_read_dict.keys(), redis_values, strict=True):
                    if cached_value is not None:
                        postings_hit = cache_read_dict[key]
                        for posting in postings_hit:
                            processed_posting = ProcessedJobPosting(
                                **posting.model_dump(), seniority=int(cached_value)
                            )
                            await self.save_queue.put(processed_posting)
                        continue
                    postings_miss = cache_read_dict[key]
                    for missed_posting in postings_miss:
                        await self.inference_queue.put(missed_posting)
                cache_read_dict.clear()
            self.ingestion_queue.task_done()

    async def consume_inference_queue(self, batch_size: int) -> None:
        inference_dict: dict[str, list[JobPosting]] = defaultdict(list)
        cache_write_dict: dict[str, int] = {}
        while True:
            job_posting = await self.inference_queue.get()
            inference_dict[job_posting.uuid].append(job_posting)
            if len(inference_dict) >= batch_size or self.inference_queue.empty():
                grpc_batch = []
                for postings in inference_dict.values():
                    grpc_request = seniority_pb2.SeniorityRequest(
                        uuid=postings[0].uuid, company=postings[0].company, title=postings[0].title
                    )
                    grpc_batch.append(grpc_request)
                grpc_response = await self.grpc_stub.InferSeniority(
                    seniority_pb2.SeniorityRequestBatch(batch=grpc_batch)
                )
                for response in grpc_response.batch:
                    seniority_level = response.seniority
                    for posting in inference_dict[response.uuid]:
                        await self.save_queue.put(
                            ProcessedJobPosting(**posting.model_dump(), seniority=seniority_level)
                        )
                    # use last posting since the cache keys are all the same
                    cache_write_dict[posting.cache_key] = seniority_level
                # write cache all at once to reduce the number of calls
                await self.redis_client.mset(cache_write_dict)
                inference_dict.clear()
                cache_write_dict.clear()
            self.inference_queue.task_done()

    async def consume_save_queue(self) -> None:
        """Consumes the save_queue and uploads files to S3.

        Monitor save_queue and save_hash_queue concurrently, and upload files
        once all records are ready.
        """
        # store processed records organized by file of origin
        pending_files: dict[int, set[ProcessedJobPosting]] = defaultdict(set)
        # track the hashes for records that have not been processed yet
        missing_hashes_dict: dict[int, set[int]] = defaultdict(set)

        # process the save_queue (records ready to be saved)
        async def process_save_queue() -> None:
            process_count = 0
            while True:
                posting = await self.save_queue.get()
                process_count += 1
                if process_count % 100 == 0:
                    print(f"Processed {process_count} total records")
                    print("Records still needed for each timestamped file:")
                    for filename, missing_hashes_set in missing_hashes_dict.items():
                        print(f"\t{filename}.jsonl: {len(missing_hashes_set)}")
                posting_hash = hash(posting)

                for filename, missing_hashes_set in missing_hashes_dict.items():
                    if posting_hash in missing_hashes_set:
                        pending_files[filename].add(posting)
                        missing_hashes_set.remove(posting_hash)

                        # upload file once all postings are collected
                        if not missing_hashes_set:
                            upload_postings_from_timestamp(
                                bucket=BUCKET,
                                prefix=UPLOAD_PREFIX,
                                timestamp=filename,
                                postings=pending_files[filename],
                            )

                self.save_queue.task_done()

        # processing the save_hash_queue (tuples with filenames and hash lists)
        async def process_save_hash_queue() -> None:
            while True:
                filename, hash_list = await self.save_hash_queue.get()
                missing_hashes_dict[filename] = set(hash_list)
                self.save_hash_queue.task_done()

        # run both coroutines concurrently
        await asyncio.gather(process_save_queue(), process_save_hash_queue())


async def subscribe() -> None:
    # create Redis client
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    # create gRPC channel to connect to the gRPC server
    async with grpc.aio.insecure_channel(f"{GRPC_HOST}:{GRPC_PORT}") as channel:
        # create two queues to pass data between downloader and client
        ingestion_queue: asyncio.Queue = asyncio.Queue()
        save_hash_queue: asyncio.Queue = asyncio.Queue()

        seniority_client = SeniorityClient(
            redis_client=redis_client,
            grpc_channel=channel,
            ingestion_queue=ingestion_queue,
            save_hash_queue=save_hash_queue,
        )
        start_timestamp = 0

        # run downloader and client in parallel
        downloader_task = asyncio.create_task(
            stream_new_postings(
                ingestion_queue=ingestion_queue,
                save_hash_queue=save_hash_queue,
                bucket=BUCKET,
                prefix=DOWNLOAD_PREFIX,
                start_timestamp=start_timestamp,
            )
        )
        client_task = asyncio.create_task(seniority_client.run_queues())

        await asyncio.gather(downloader_task, client_task)


def main() -> None:
    asyncio.run(subscribe())


if __name__ == "__main__":
    main()
