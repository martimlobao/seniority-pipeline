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

To (re-)generate the gRPC code from the `seniority.proto` file, run the following command:

```bash
uv run python -m grpc_tools.protoc -I=src/protobufs/ --python_out=src/ --grpc_python_out=src/ src/protobufs/seniority.proto
```

## Usage
