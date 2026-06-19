
# Running BDA Notebooks

This folder contains two notebooks:

1. `01-EDA-flight-delays.ipynb` (EDA on 2015 US flights).
2. `02-EDA-flight-delays-timeseries.ipynb` (Time series analysis from 2009–2018).

## Prerequisites

1. Python **3.13.5** (as specified in `.python-version`).
2. Internet access (datasets are downloaded via `kagglehub`).
3. A Jupyter environment.

## Environment Setup

Run the following commands from the project root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

```

## Launching

```bash
source .venv/bin/activate
jupyter lab

```

Open and run the notebooks in this order:

1. `01-EDA-flight-delays.ipynb`
2. `02-EDA-flight-delays-timeseries.ipynb`

## Operating Notes for Notebooks

1. Both notebooks use local utilities from `statlib/`, so make sure to launch them from the right folder.
2. `01-EDA-flight-delays.ipynb` uses `FAST_SAMPLE = True` and `SAMPLE_SIZE = 5000` for a fast and reproducible execution.
3. `02-EDA-flight-delays-timeseries.ipynb` downloads the annual files (`2009.csv` ... `2018.csv`) via `load_datasets_timeseries(...)`.
4. Inside `02-EDA-flight-delays-timeseries.ipynb`, there are cells containing `! pip install ...`. If you have already installed `requirements.txt`, you can skip them.

## Expected Outputs

1. EDA tables/plots, cleaning, imputation, outlier analysis, and metrics in notebook `01`.
2. Stationarity analysis, ACF/PACF plots, seasonal decomposition, and autoregressive models in notebook `02`.
