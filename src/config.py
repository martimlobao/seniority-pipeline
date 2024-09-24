"""Configuration file for the project."""

BUCKET: str = "rl-data"  # use "quicklink-public" for testing
DOWNLOAD_PREFIX: str = "job-postings-raw"
UPLOAD_PREFIX: str = "job-postings-mod"

REDIS_HOST: str = "localhost"
REDIS_PORT: int = 6379

GRPC_HOST: str = "localhost"
GRPC_PORT: int = 50051
