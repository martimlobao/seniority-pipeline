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
