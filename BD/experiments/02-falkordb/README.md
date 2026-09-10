# FalkorDB Cluster Deploy (Docker Compose)

Simple deployment of a 3-node FalkorDB cluster using Docker Compose.

The cluster is intended for graph analysis workloads where graph data and queries are distributed across multiple FalkorDB nodes.

Falker DB was selected because of the internals usage of redis.

## Requirements

* Docker
* Docker Compose (`docker compose` plugin)

## Cluster Architecture

The deployment consists of three FalkorDB nodes:

| Node              | Host Database Port | Host Web UI Port | Data Directory   |
| :---------------- | :----------------- | :--------------- | :--------------- |
| `falkordb-node-1` | `6379`             | `3000`           | `/mnt/falkordb1` |
| `falkordb-node-2` | `6380`             | `3001`           | `/mnt/falkordb2` |
| `falkordb-node-3` | `6381`             | `3002`           | `/mnt/falkordb3` |

Inside the Docker network, every node uses:

* Database: `6379`
* Web UI: `3000`

The host port mappings allow each node to be accessed independently.

## Web UI

The Web UI is available at:

* [http://localhost:3000](http://localhost:3000)
* [http://localhost:3001](http://localhost:3001)
* [http://localhost:3002](http://localhost:3002)

Each URL connects to the Web UI of the corresponding FalkorDB node.

## Start the Cluster

From the project directory:

```bash
docker compose up -d
```

Check the status of the containers:

```bash
docker compose ps
```

Check the logs:

```bash
docker compose logs -f
```

## Using the Cluster for Graph Analysis

The three FalkorDB instances form the database layer used by the graph analysis environment.

Applications and analysis tools can connect to the FalkorDB nodes through their exposed Redis-compatible ports:

```text
localhost:6379
localhost:6380
localhost:6381
```

The nodes can be used to distribute graph data and graph queries across the cluster.

For graph analysis, the typical workflow is:

1. Load graph data into FalkorDB.
2. Create the required graph structures and indexes.
3. Execute Cypher queries for graph exploration and analysis.
4. Use the results in external analysis tools or applications.

The Web UI can be used to inspect graphs and execute Cypher queries interactively.

## Persistence

Each node stores its data on the host:

```text
/mnt/falkordb1
/mnt/falkordb2
/mnt/falkordb3
```

So we need to create the folder

```sh
rm -rf /mnt/falkordb{1,2,3}/*
mkdir -p /mnt/falkordb{1,2,3}
```

The directories are mounted into the corresponding containers, so the graph data survives container restarts and recreation if needed.

## Stop the Cluster

Stop and remove the containers:

```bash
docker compose down
```

To also remove the Docker volumes created by Compose:

```bash
docker compose down -v
```

The host-mounted data directories are not removed by `docker compose down -v`.

Follow logs for a single node:

```bash
docker compose logs -f falkordb-node-1
```
