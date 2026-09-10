# SAIL Deploy (Docker Compose)

Simple deployment of a SAIL server and a debug driver container using Docker Compose.

SAIL was selected as the query engine for distributed data processing in this experiment as a spark drop-in replacement. The setup is intended for local testing and development of SAIL-based workloads.

## Requirements

* Docker
* Docker Compose (`docker compose` plugin)

## Architecture

The deployment consists of:

| Service | Host Port | Internal Port | Purpose |
| :------ | :-------- | :------------ | :------ |
| `sail-server` | `6066` | `50051` | SAIL gRPC server |
| `sail-driver-debug` | `4040` | `4040` | Python debug driver container |

The server is exposed on:

* `docker-host:6066`

## Start the Environment

From the project directory:

```bash
docker compose up -d --build
```

This is the recommended command for a continuous build, so the image is rebuilt whenever the local Docker configuration changes.

Check the status:

```bash
docker compose ps
```

Check logs:

```bash
docker compose logs -f
```

## Stop the Environment

```bash
docker compose down
```

To also remove the created containers:

```bash
docker compose down -v
```
