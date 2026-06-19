
# Running Notebook `03-GA-US-flight-2015.ipynb`

This notebook builds and analyzes a graph of 2015 US flights using **Neo4j** + **Graph Data Science (GDS)**, with data loaded from Kaggle (`usdot/flight-delays`).

## 1. Prerequisites

1. Python 3.13.5 (tested within the project using the `python3` environment).
2. A running and reachable Neo4j instance.
3. **GDS** plugin installed on Neo4j (the notebook executes `CALL gds.*`).
4. An internet connection to download the datasets via `kagglehub`.

## 2. Environment Setup

From the project root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

```

## 3. Neo4j Connection Configuration

Inside the notebook, you will find a cell containing:

```python
NEO4J_URI = "..."
NEO4J_USER = "..."
NEO4J_PASSWORD = "..."
DATABASE = "neo4j"

```

Update these values with your credentials before running the notebook.

## 4. Launching the Notebook


Open `03-GA-US-flight-2015.ipynb` and run the cells sequentially from top to bottom.

## 5. Expected Outputs

During execution, the following are generated:

1. Intermediate CSV files in `neo4j_ready/` (`airports_nodes.csv`, `flights_rels.csv`, `preprocess_fill_report.csv`).
2. Population of the Neo4j graph (`Airport`, `Airline`, `Flight`, `Route`, `ROUTE_TO`, etc.).
3. GDS analysis (WCC, SCC, Centrality, PageRank, Louvain, Shortest Path).

## 6. Quick Notes

1. The notebook includes `FAST_SAMPLE = True` and `SAMPLE_SIZE = 5000` to speed up execution.
2. To use the full dataset, set `FAST_SAMPLE = False` in the corresponding cell.