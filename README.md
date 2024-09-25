# Seniority Data Pipeline

## Overview

This project is a data pipeline that processes data from a CSV file and loads it into a PostgreSQL database. The data is then used to generate a report that shows the average seniority of employees in each department.

## Installation

The recommended installation is to use [`uv`](https://docs.astral.sh/uv/). This will handle virtual environment creation, dependencies installation (including fetching the correct version of Python if needed), as well as running the application.

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# Alternatively using Homebrew
brew install uv
```

Additionally, you will need to have Docker installed to run the Redis server. You may install Docker and Redis using Homebrew with the following commands:

```bash
brew install --cask docker
brew install redis
```

To start the Redis server, run the following command:

```bash
docker run --name redis -p 6379:6379 -d redis
```

To (re-)generate the gRPC code from the `seniority.proto` file, run the following command:

```bash
uv run python -m grpc_tools.protoc -I=src/protobufs/ --python_out=src/ --pyi_out=src/ --grpc_python_out=src/ src/protobufs/seniority.proto
```

## Usage

To start the mock gRPC server, run the following command to run [`src/seniority/server.py`](src/seniority/server.py):

```bash
uv run server
```

Similarly, to start the client, run the following command to run [`src/seniority/client.py`](src/seniority/client.py):

```bash
uv run client
```

You may also generate example data using [`src/seniority/sample_generator.py`](src/seniority/sample_generator.py) by running the following command:

```bash
uv run sample
# Specify the number of total job postings and the number of job postings to split into each file
uv run sample --total 20000 --split 7000
```

## Design

The data pipeline consists of four parts: downloading the data, retrieving the cached seniority levels, inferring the seniority levels for new company-title pairs, and uploading the data back to S3. In order to handle large amounts of data as quickly and efficiently as possible, the pipeline uses asynchronous processing to send data between the different components.

There are two main components to the pipeline: the data downloader and the data processor. These run simultaneously and share two queues: the ingestion queue (where each raw job posting is sent) and the record hash queue (containing metadata on which postings belong in which file). Once the data is picked up by the processor, it is grouped into batches of 1000 and sent to the caching layer to retrieve the seniority levels. This is done to reduce the number of API calls to Redis in order to be more efficient. After this, the records that returned a cache hit are modified and sent to the save queue and the ones that returned a cache miss are sent to the inference queue.

The inference queue is consumed by the `consume_inference_queue` method, which also batches the data into groups of 1000 and sends them to the gRPC server. Once the server returns the data, the postings are also modified to include the inferred seniority levels and sent to the save queue. Additionally, the the returned seniority levels are written to the caching layer in a single batch, where each key is a hash of the company and title and the value is the corresponding seniority level.

Finally, the data is read from the save queue, as well as the record hash queue, and uploaded to S3. Since we cannot append data to files in S3, all of the records are collected together and only uploaded once all the job postings from the original file are present.


## Design Decisions and Comments

### Sequential Downloading

Since the expectation is that new job postings will be uploaded onto a single file every minute, I chose to download files sequentially instead of asynchronously. Even if multiple files are available, the client will download them sequentially and send the postings into the ingestion queue for the client to pick up and process.

### gRPC UUID

One thing to note is that the UUID for each `SeniorityRequest` may have too small of a range to comfortably avoid collisions. Given a space of $N$ possible hash values and $k$ unique integers, an [approximation](https://preshing.com/20110504/hash-collision-probabilities/) for the probability of a hash collision (assuming $k$ is not too small and $N$ is much larger than $k$) is given by $\frac{k^2}{2N}$. Since each batch contains $k$ = 1000 unique company-title pairs and $N$ is an `int32`, the probability of collision in any given batch is $\frac{1000^2}{2\times2^{32}}$, which is approximately 1 in 8600. Hence, the probability of there being at least one collision in any of the batches over 2 million unique pairs (i.e. 2000 batches) is approximately

$$1 - \left(1-\frac{1}{8600}\right)^{2000} \approx 0.208.$$

It's possible that we may still wish to accept this level of risk given that it is likely that the accuracy of the inference model itself may be a much larger source of error, and that increasing the UUID size would increase the size of the data being sent over the network.

### Failure Handling

Since we are passing data asynchronously in queues, careful consideration must be made to ensure that the data is not lost in the event of a failure. The way I chose to handle this was to ensure that the processed job postings from a single input file are only uploaded once all of them have been processed. This way, if the client fails unexpectedly while processing a file, the job can restart from an earlier timestamp and re-ingest the missing data. This also has the benefit that any records that have run through the inference model will not be reprocessed since they will have been stored in the Redis cache.

### Choice of Caching Layer

I chose to use Redis as the caching layer for the inference model since it is an in-memory key-value store that is well-suited for caching. The inference model is stored in Redis as a dictionary where the keys are the hashed company-title pairs and the values are the inferred seniority levels. This allows for fast lookups and updates to the model. Additionally, Redis has built-in support for data persistence and replication, which can be useful for ensuring that the data is not lost in the event of a failure.

Additionally, the amount of data that needs to be stored in the cache is relatively small: each key is a `sha256` hash with 64 characters, and the seniority level is also just a single digit. This means that the entire cache database for a claimed 20 million unique pairs in the past year would only take up around 2 GB. Using AWS ElastiCache, this would cost around $7 per day with continuous usage.

Alternatives to Redis were also considered, such as DynamoDB, but whereas reads and writes are comparatively cheaper than storage, DynamoDB is cheap to store but expensive to read and write to.

### Cache invalidation

One thing that was also considered was the matter of cache invalidation. If the inference model is updated, it is reasonable to assume that the cached seniority levels are no longer valid. One way to handle this would be to version the inference model and store the version number in the cache. When a request is made to the cache, the version number is checked against the current version of the model. If they do not match, the cache is invalidated and the request is forwarded to the inference model to get the updated seniority level. However, since it is not expected that we would care about the output of an outdated version of the model, it is simpler to just clear the cache when the model is updated.

## Performance

The pipeline is able to handle a very heavy load of job postings. It is able to process 50,000 job postings in under 1 minute, including the time taken to download the raw data, and with a fresh cache. This is well above the expected average of 5,555 job postings per minute and very close to the theoretical maximum of 60,000 job postings per minute. Note that this was done while throttling the response speed of the gRPC server to a maximum of one batch response per second.

```bash
# Generate 200,000 job postings
uv run sample --total 200000 --split 20000
# Upload the data to S3 manually
# Start the server
uv run server
# Run the pipeline
uv run client
```

Using a full cache, the entire processing pipeline for 200,000 postings runs in under 5 seconds, with the main blocking factor being network speed, limiting how fast it is able to download and upload the data to S3.
