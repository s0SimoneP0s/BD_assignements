from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Callable



ColKind = Literal["code", "string", "numeric", "boolean"]

@dataclass
class ColSchema:
    """
    Declares the expected type and optional post-load transform for a column.

    kind:
        'code'    -> cast to string, strip + upper  (join keys, IATA codes, ...)
        'string'  -> cast to string, strip only
        'numeric' -> pd.to_numeric (coerce errors to NaN)
        'boolean' -> cast to bool
    transform:
        optional extra callable applied after the kind-cast
    """
    kind: ColKind
    transform: Callable[[pd.Series], pd.Series] | None = None


@dataclass
class FileSchema:
    """Schema for a single CSV file."""
    columns: dict[str, ColSchema] = field(default_factory=dict)


# -----------------------------------------------------------------------
# schemas declaration  (add / edit freely)
# -----------------------------------------------------------------------
_SCHEMAS: dict[str, FileSchema] = {
    "flights.csv": FileSchema(columns={
        # join keys / codes
        "ORIGIN_AIRPORT":       ColSchema("code"),
        "DESTINATION_AIRPORT":  ColSchema("code"),
        "AIRLINE":              ColSchema("code"),
        # strings
        "TAIL_NUMBER":          ColSchema("string"),
        "CANCELLATION_REASON":  ColSchema("string"),
        # numerics (mixed-type columns that pandas may misread)
        "DEPARTURE_TIME":       ColSchema("numeric"),
        "DEPARTURE_DELAY":      ColSchema("numeric"),
        "TAXI_OUT":             ColSchema("numeric"),
        "WHEELS_OFF":           ColSchema("numeric"),
        "SCHEDULED_TIME":       ColSchema("numeric"),
        "ELAPSED_TIME":         ColSchema("numeric"),
        "AIR_TIME":             ColSchema("numeric"),
        "WHEELS_ON":            ColSchema("numeric"),
        "TAXI_IN":              ColSchema("numeric"),
        "ARRIVAL_TIME":         ColSchema("numeric"),
        "ARRIVAL_DELAY":        ColSchema("numeric"),
        "AIR_SYSTEM_DELAY":     ColSchema("numeric"),
        "SECURITY_DELAY":       ColSchema("numeric"),
        "AIRLINE_DELAY":        ColSchema("numeric"),
        "LATE_AIRCRAFT_DELAY":  ColSchema("numeric"),
        "WEATHER_DELAY":        ColSchema("numeric"),
        # booleans
        "DIVERTED":             ColSchema("boolean"),
        "CANCELLED":            ColSchema("boolean"),
    }),
    "airports.csv": FileSchema(columns={
        "IATA_CODE":  ColSchema("code"),
        "AIRPORT":    ColSchema("string"),
        "CITY":       ColSchema("string"),
        "STATE":      ColSchema("code"),
        "COUNTRY":    ColSchema("code"),
        "LATITUDE":   ColSchema("numeric"),
        "LONGITUDE":  ColSchema("numeric"),
    }),
    "airlines.csv": FileSchema(columns={
        "IATA_CODE": ColSchema("code"),
    }),
}

# -----------------------------------------------------------------------


def _apply_schema(df: 'pd.DataFrame', schema: FileSchema) -> 'pd.DataFrame':
    """Cast and normalise columns according to the declared schema."""
    import pandas as pd
    _KIND_CAST: dict[ColKind, Callable[[pd.Series], pd.Series]] = {
        "code":    lambda s: s.astype("string").str.strip().str.upper(),
        "string":  lambda s: s.astype("string").str.strip(),
        "numeric": lambda s: pd.to_numeric(s, errors="coerce"),
        "boolean": lambda s: s.astype(bool),
    }
    for col, col_schema in schema.columns.items():
        if col not in df.columns:
            continue
        df[col] = _KIND_CAST[col_schema.kind](df[col])
        if col_schema.transform is not None:
            df[col] = col_schema.transform(df[col])
    return df


#-------------------------------
#  Exposed
#-------------------------------


def load_datasets(list_file_pathname:list, omogenize : bool = False) -> dict:
    """
    Load datasets from Kaggle using kagglehub.
    custom function for flight dataset

    """
    import kagglehub
    from kagglehub import KaggleDatasetAdapter

    import os
    import warnings
    import pandas as pd
    from pandas.errors import DtypeWarning

    r: dict[str, pd.DataFrame] = {}
    for file_pathname in list_file_pathname:
        print(f"Loading {file_pathname}...")
        try: # deprecation warning
            df= kagglehub.load_dataset( KaggleDatasetAdapter.PANDAS, "usdot/flight-delays", file_pathname, )

        except:
            df= kagglehub.dataset_load( KaggleDatasetAdapter.PANDAS, "usdot/flight-delays", file_pathname, )
        
        # normalize results
        if omogenize:  
            schema = _SCHEMAS.get(file_pathname, FileSchema())
            df = _apply_schema(df, schema)
        r[file_pathname] = df


    return r




def load_datasets_timeseries(list_file_pathname:list, 
                             omogenize : bool = False) -> dict:
    """
    Load datasets from Kaggle using kagglehub.
    custom function for flight dataset

    """
    import kagglehub
    from kagglehub import KaggleDatasetAdapter

    import os
    import warnings
    import pandas as pd
    from pandas.errors import DtypeWarning
    from pathlib import Path
    out_dir = Path("time_series_datasets")
    out_dir.mkdir(exist_ok=True)
    ts_filnames = [
        "2009.csv",
        "2010.csv",
        "2011.csv",
        "2012.csv",
        "2013.csv",
        "2014.csv",
        "2015.csv",
        "2016.csv",
        "2017.csv",
        "2018.csv",
    ]
    r: dict[str, pd.DataFrame] = {}
    for file_pathname in list_file_pathname:
        print(f"Loading {file_pathname}...")
        if not Path(f"time_series_datasets/{file_pathname}").exists():
            try: # deprecation warning
                df= kagglehub.load_dataset( KaggleDatasetAdapter.PANDAS, "yuanyuwendymu/airline-delay-and-cancellation-data-2009-2018", file_pathname, )

            except:
                df= kagglehub.dataset_load( KaggleDatasetAdapter.PANDAS, "yuanyuwendymu/airline-delay-and-cancellation-data-2009-2018", file_pathname, )
        else:
            df = pd.read_csv(f"time_series_datasets/{file_pathname}")
        # normalize results
        if omogenize: 
            actual_name = 'flights.csv' if file_pathname in  ts_filnames else file_pathname
            schema = _SCHEMAS.get(actual_name, FileSchema())
            df = _apply_schema(df, schema)
        r[file_pathname] = df


    return r