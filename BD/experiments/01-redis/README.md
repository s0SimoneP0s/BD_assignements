# Redis benchmark

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

3. Eseguire i test (solo per Redis):

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

