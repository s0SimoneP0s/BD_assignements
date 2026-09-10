# Spark Cluster (Docker Compose)

Configurazione di un cluster Apache Spark standalone per eseguire e verificare
job PySpark in ambiente Docker. Il cluster comprende un master, tre worker e un
container driver dedicato al debug e all'esecuzione di `spark-submit`.

## Requirements

* Docker
* Docker Compose (`docker compose` plugin)

## Architecture

La configurazione utilizza l'immagine
`spark:4.1.2-scala2.13-java17-python3-r-ubuntu` per tutti i container.

I servizi disponibili sono:

| Servizio | Porta host | Porta interna | Scopo |
| :------ | :-------- | :------------ | :------ |
| `spark-master` | `7077`, `8080` | `7077`, `8080` | Master Spark e Web UI |
| `spark-worker-1` | - | `8081` | Worker Spark, 2 core e 2 GB |
| `spark-worker-2` | - | `8081` | Worker Spark, 2 core e 2 GB |
| `spark-worker-3` | - | `8081` | Worker Spark, 2 core e 2 GB |
| `spark-driver-debug` | `4040` | `4040` | Container driver per debug e job |

Tutti i servizi comunicano sulla rete Docker `spark-cluster`. Il master è
raggiungibile dai container tramite `spark://spark-master:7077`.

La Web UI del master è disponibile su
[`http://localhost:8080`](http://localhost:8080), mentre la UI dell'applicazione
Spark sarà esposta su
[`http://localhost:4040`](http://localhost:4040) quando un job è in esecuzione.

I dati e gli script locali sono montati nel container driver come segue:

| Percorso locale | Percorso nel container |
| :-------------- | :--------------------- |
| `./jobs` | `/opt/spark/jobs` |
| `./data-driver` | `/opt/spark/data` |

Ogni worker utilizza inoltre la propria directory locale (`data-worker-1`,
`data-worker-2` o `data-worker-3`) montata in `/opt/spark/data`.

## Start the Environment

Eseguire i comandi dalla directory dell'esperimento, cioè quella che contiene
`docker-compose.yaml`.

Avviare il cluster:

```bash
docker compose up -d
```

Il file compose utilizza direttamente un'immagine Docker predefinita, quindi non
è necessario effettuare una build locale.

Controllare lo stato dei servizi:

```bash
docker compose ps
```

Visualizzare i log di tutti i servizi:

```bash
docker compose logs -f
```

Per seguire i log di un singolo servizio, ad esempio il master:

```bash
docker compose logs -f spark-master
```

## Eseguire un job

Inserire gli script PySpark nella directory `jobs`. Il container driver rimane
attivo in attesa di comandi e può essere utilizzato con `docker exec`.

Per eseguire `test.py` in modalità client:

```bash
docker exec -it spark-driver-debug \
	/opt/spark/bin/spark-submit \
	--master spark://spark-master:7077 \
	/opt/spark/jobs/test.py
```

In alternativa, aprire una shell nel container driver:

```bash
docker exec -it spark-driver-debug /bin/bash
```

e lanciare da lì il comando `spark-submit`.

## Fermare l'ambiente

```bash
docker compose down
```

Per fermare e rimuovere anche i container creati:

```bash
docker compose down 
```
