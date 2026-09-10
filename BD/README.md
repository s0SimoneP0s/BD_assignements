# Big Data Experiment

Analisi CAP per database NoSQL Redis: esperimenti e script per creare un
cluster Redis in Docker e testare comportamento rispetto a Consistency,
Availability e Partition Tolerance.

Analisi Grafh Database Redis based in sostituzione di Neo4J

Analisi di spark e delle feature base su pipeline esistente. Feature avanzate su dati di prova e benchmark

Replacement di Spark con un compute engine moderno come Sail, ma meno completo. 


## Contenuto

- `experiments/`: cartella principale con i diversi esperimenti e le configurazioni Docker dei sistemi testati.
- `01-redis/`: esperimenti su Redis e CAP theorem.
- `02-falkordb/`: deployment di cluster FalkorDB basato su Redis e modello graph database.
- `03-engine_spark/`: configurazione ed esempi di Spark per elaborazione distribuita in-memory.
- `04-sail/`: ambiente SAIL per test e sviluppo di workload distribuite.

- **Notebook**: vari esperimenti di replacement su pipeline esistenti di dati per
comprendere l'effort di un replacement

## Esperimenti Redis - CAP theorem

Questa cartella contiene script per creare un cluster Redis in Docker e testare il comportamento
rispetto al CAP theorem (consistency, availability, partition tolerance).

File principali in `experiments/`:
- `docker-compose.yaml`: definizione dei 3 container Redis usati per gli esperimenti.
- `create_and_test_cluster.sh`: script helper per creare il cluster e verificare operazioni di base.
- `test_consistency.py`: scrive su un nodo e legge dagli altri per osservare la consistenza.
- `test_availability.py`: stop/start di un container per testare la disponibilità.
- `test_partitioning.py`: disconnette/riconnette un nodo dalla rete Docker per simulare partizione.

## Altri esperimenti disponibili

Oltre all'esperimento su Redis, il progetto include anche altri test e deployment dedicati a diversi engine Big Data e graph processing:

- `01-redis/`: cluster Redis con verifica di consistenza, disponibilità e partizione.
- `02-falkordb/`: deployment di un cluster FalkorDB con Docker Compose, utile per testare un database grafico costruito su Redis e per valutare il comportamento di query graph-based.
- `03-engine_spark/`: setup Spark per benchmarking e elaborazione distribuita, con documentazione e esempi di workflow in-memory.
- `04-sail/`: ambiente SAIL con server e driver di debug per test locali e sviluppo di workload distribuite.

Prerequisiti:
- Docker e Docker Compose installati.
- Python con le dipendenze: vedi `requirements.txt` in questa cartella (sono richiesti `redis` e `hiredis`).
- `redis-cli` (puoi usare `redis-tools` o il client incluso nei container).


## Riferimenti dettagliati

- [Redis](experiments/01-redis/README.md)
- [FalkorDB](experiments/02-falkordb/README.md)
- [Spark](experiments/03-engine_spark/README.md)
- [Sail](experiments/04-sail/README.md)

