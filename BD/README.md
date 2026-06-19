# Redis Big Data Experiment

Analisi CAP per database NoSQL Redis: esperimenti e script per creare un
cluster Redis in Docker e testare comportamento rispetto a Consistency,
Availability e Partition Tolerance.

## Contenuto

- `experiments/`: script e file per creare il cluster Redis e eseguire i test.

## Esperimenti Redis - CAP theorem

Questa cartella contiene script per creare un cluster Redis in Docker e testare il comportamento
rispetto al CAP theorem (consistency, availability, partition tolerance).

File principali in `experiments/`:
- `docker-compose.yaml`: definizione dei 3 container Redis usati per gli esperimenti.
- `create_and_test_cluster.sh`: script helper per creare il cluster e verificare operazioni di base.
- `test_consistency.py`: scrive su un nodo e legge dagli altri per osservare la consistenza.
- `test_availability.py`: stop/start di un container per testare la disponibilità.
- `test_partitioning.py`: disconnette/riconnette un nodo dalla rete Docker per simulare partizione.

Prerequisiti:
- Docker e Docker Compose installati.
- Python con le dipendenze: vedi `requirements.txt` in questa cartella (sono richiesti `redis` e `hiredis`).
- `redis-cli` (puoi usare `redis-tools` o il client incluso nei container).

## Esempio d'uso rapido

1. Avviare il cluster (eseguire dalla cartella `experiments`):

```sh
docker compose -f docker-compose.yaml up -d --force-recreate
```

2. Creare il cluster Redis (da un container che dispone di `redis-cli`):

Eseguire lo script dal container `redis-node-1` (consigliato):

```sh
docker cp create_and_test_cluster.sh redis-node-1:/create_cluster.sh
docker exec -it redis-node-1 sh -c "chmod +x /create_cluster.sh && /create_cluster.sh"
```

3. Eseguire i test (dalla cartella `experiments`):

```sh
bash ./run_all_tests.sh
```

Nota: gli script scrivono i log nella directory `logs/`.

## Reset del cluster (procedura passo-passo)

Se vuoi resettare completamente il cluster e ripartire da zero, segui questi passi. Esegui i comandi dalla cartella `experiments` o specifica i percorsi corretti.

1) Portare giù i container e rimuovere le reti/risorse create da Docker Compose:

```sh
docker compose -f docker-compose.yaml down
```

2) Cancellare i dati locali persistenti usati dai container (ATTENZIONE: questo rimuove tutte le chiavi Redis):

```sh
rm -rf /mnt/redis{1,2,3}/*
mkdir -p /mnt/redis{1,2,3}
```

3) Ricreare e riavviare i container con Docker Compose:

```sh
docker compose -f docker-compose.yaml up -d --force-recreate
```

4) Creazione cluster:

```sh
docker cp create_and_test_cluster.sh redis-node-1:/create_cluster.sh
docker exec -it redis-node-1 sh -c "chmod +x /create_cluster.sh && /create_cluster.sh"
```

