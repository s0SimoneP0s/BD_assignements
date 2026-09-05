from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Callable

import pandas as pd



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



def plot_main_community_routes_map(
    main_community_routes: 'pd.DataFrame',
    title: str = "Main community routes on US map",
    airport_color: str = "#ff7f0e",
    figsize: tuple[int, int] = (16, 10),
    tmpdir: 'Path' | None = None,
    dfs_kv: dict = None,
    red_intensity: float = 1.0

):
    # Import required libraries
    import pandas as pd
    import geopandas as gpd
    import matplotlib.pyplot as plt
    from IPython.display import display
    from shapely.geometry import LineString
    from sklearn.preprocessing import MinMaxScaler
    import numpy as np
    
    scaler = MinMaxScaler()

    # Check if routes data is provided
    if main_community_routes is None or main_community_routes.empty:
        raise ValueError("main_community_routes is empty")

    # Validate required columns exist
    if "origin" not in main_community_routes.columns or "dest" not in main_community_routes.columns:
        raise KeyError("main_community_routes must contain origin and dest columns")

    # Find shapefile in temporary directory
    shp_files = list(tmpdir.glob("*.shp"))
    if not shp_files:
        raise FileNotFoundError("No shapefile found in tmpdir")

    # Load US states geometry
    states_gdf = gpd.read_file(shp_files[0])

    # Get airports data from dictionary
    airports_raw = dfs_kv["airports.csv"].copy()

    # Validate airports have IATA codes
    if "IATA_CODE" not in airports_raw.columns:
        display(airports_raw.head())
        raise KeyError("airports.csv must contain IATA_CODE")

    # Create GeoDataFrame with airport positions
    airports_raw = gpd.GeoDataFrame(
        airports_raw,
        geometry=gpd.points_from_xy(
            airports_raw["LONGITUDE"],
            airports_raw["LATITUDE"],
        ),
        crs="EPSG:4326",
    )

    # Rename IATA column for consistency
    airports_raw = airports_raw.rename(columns={"IATA_CODE": "iata"}).copy()

    # Clean route data and standardize IATA codes
    routes = main_community_routes.copy()
    routes["origin"] = routes["origin"].astype(str).str.upper()
    routes["dest"] = routes["dest"].astype(str).str.upper()

    # Prepare airports for merging
    airports = airports_raw[["iata", "geometry"]].dropna().copy()
    airports["iata"] = airports["iata"].astype(str).str.upper()

    # Merge origin and destination coordinates into routes
    routes = routes.merge(
        airports.rename(columns={"iata": "origin", "geometry": "origin_geom"}),
        on="origin",
        how="left",
    ).merge(
        airports.rename(columns={"iata": "dest", "geometry": "dest_geom"}),
        on="dest",
        how="left",
    )

    # Remove routes with missing coordinates
    routes = routes.dropna(subset=["origin_geom", "dest_geom"]).copy()
    if routes.empty:
        raise ValueError("No routes can be plotted because origin/dest coordinates are missing")

    # Align coordinate reference systems
    if states_gdf.crs is not None and airports_raw.crs is not None and states_gdf.crs != airports_raw.crs:
        states_gdf = states_gdf.to_crs(airports_raw.crs)

    # Create LineString geometries for each route
    routes_gdf = gpd.GeoDataFrame(
        routes,
        geometry=[LineString([o, d]) for o, d in zip(routes["origin_geom"], routes["dest_geom"])],
        crs=airports_raw.crs,
    )

    # Clamp red_intensity between 0 and 1
    red_intensity = max(0.0, min(1.0, red_intensity))
    
    # Calculate color intensity based on flight count
    if "flights" in routes_gdf.columns:
        values = pd.to_numeric(routes_gdf["flights"], errors="coerce").fillna(1.0)
        
        # Use MinMaxScaler to normalize values to [0, 1]
        normalized = scaler.fit_transform(values.values.reshape(-1, 1)).flatten()
        routes_gdf["alpha"] = normalized  # Store normalized values for potential use
        
        # Apply power transformation for better visual distinction
        # Lower values become more visible, higher values become more intense
        normalized = np.power(normalized, 0.7)  
        
        # Map to red shades: from light red (0.2) to dark red (0.9)
        # Multiply by red_intensity for global control
        routes_gdf["color"] = [
            (
                1 - (x * red_intensity), 
                0.5 - 0.5 *x * red_intensity, 
                0.0
             ) 
            for x in normalized
        ]
    else:
        # If no flights column, use uniform red
        # If no flights column, use uniform color based on red_intensity
        red = 1.0 * red_intensity
        green = 0.5 - 0.5 * red_intensity
        routes_gdf["color"] = [(red, green, 0.0)] * len(routes_gdf)

    # Create figure and axis
    fig, ax = plt.subplots(figsize=figsize)

    # Plot US states as background
    states_gdf.plot(ax=ax, color="#f2f2f2", edgecolor="#444444", linewidth=0.6)
    
    # Plot routes as lines
    for idx, row in routes_gdf.iterrows():
        ax.plot(
            *row.geometry.xy,
            color=row["color"],
            linewidth=1.5,  
            alpha=row["alpha"],  
            zorder=2
        )    
    
    # Plot airports as points
    airports_raw.plot(ax=ax, color=airport_color, markersize=6, alpha=0.9, zorder=3)

    # Set title and remove axes
    ax.set_title(title, fontweight="bold", fontsize=14)
    ax.set_axis_off()
    
    # Display the plot
    plt.tight_layout()
    plt.show()

    # Return the routes GeoDataFrame for further use
    return routes_gdf



#-------------------------------
# Preprocessing functions
#-------------------------------


def build_df_final_clean_from_airports_raw(
    flights_raw: 'pd.DataFrame',
    airports_raw: 'pd.DataFrame',
) -> 'pd.DataFrame':
    """
    Build the cleaned flight dataframe used by the notebook preprocessing step.
    """
    import pandas as pd
    import numpy as np

    def pick_col(df: 'pd.DataFrame', candidates: list[str], required: bool = True) -> str | None:
        for c in candidates:
            if c in df.columns:
                return c
        if required:
            raise KeyError(f"Missing required column. Tried: {candidates}")
        return None

    def format_hhmm(value):
        if pd.isna(value):
            return pd.NA
        try:
            value = int(value)
        except Exception:
            return pd.NA
        if value == 2400:
            value = 0
        if value < 0 or value > 2359:
            return pd.NA
        s = f"{value:04d}"
        hh, mm = int(s[:2]), int(s[2:])
        if hh > 23 or mm > 59:
            return pd.NA
        return pd.Timestamp(2000, 1, 1, hh, mm).time()

    def total_delay(row):
        arr = row.get("ARRIVAL_DELAY", pd.NA)
        dep = row.get("DEPARTURE_DELAY", pd.NA)
        arr = arr if pd.notna(arr) and arr > 0 else 0
        dep = dep if pd.notna(dep) and dep > 0 else 0
        cancel_reason = row.get("CANCELLATION_REASON", pd.NA)
        if pd.isna(cancel_reason) or cancel_reason == "":
            return (arr + dep) / 2
        return pd.NA

    def max_delay_if_cancelled(row, max_delay_value):
        if bool(row.get("DIVERTED", False)):
            return max_delay_value
        cancel_reason = row.get("CANCELLATION_REASON", pd.NA)
        if pd.isna(cancel_reason) or cancel_reason == "":
            return row.get("TOTAL_DELAY", pd.NA)
        return max_delay_value

    # Canonical column aliases to support small naming differences across datasets
    COLUMN_ALIASES = {
        "AIRLINE": ["AIRLINE", "AIRLINES_IATA_CODE"],
        "ORIGIN_IATA": ["ORIGIN_AIRPORT_IATA_CODE", "ORIGIN_AIRPORT"],
        "DEST_IATA": ["DESTINATION_AIRPORT_IATA_CODE", "DESTINATION_AIRPORT"],
    }

    # Cancellation short description
    BTS_MAP_CANCELLATION_REASON = {
        "A": "Carrier",
        "B": "Weather",
        "C": "National Air System",
        "D": "Late Aircraft",
    }

    # create working copies
    flights_raw = flights_raw.copy()
    airports_raw = airports_raw.copy()

    # Canonical flight column aliases.
    AIRLINE_COL = pick_col(flights_raw, ["AIRLINE", "AIRLINES_IATA_CODE"])
    ORIGIN_COL = pick_col(flights_raw, ["ORIGIN_AIRPORT_IATA_CODE", "ORIGIN_AIRPORT"])
    DEST_COL = pick_col(flights_raw, ["DESTINATION_AIRPORT_IATA_CODE", "DESTINATION_AIRPORT"])

    # Date merging
    date_parts = ["YEAR", "MONTH", "DAY"]
    if all(c in flights_raw.columns for c in date_parts):
        flights_raw["DATETIME"] = pd.to_datetime(flights_raw[date_parts], errors="coerce")

    # Core categorical casts for flights data
    if "CANCELLED" in flights_raw.columns:
        flights_raw["CANCELLED"] = flights_raw["CANCELLED"].astype(bool)
    for c in [AIRLINE_COL, ORIGIN_COL, DEST_COL, "CANCELLATION_REASON"]:
        if c in flights_raw.columns:
            flights_raw[c] = flights_raw[c].astype("category")

    # Cast airport metadata columns to categorical type for compact storage.
    for c in ["CITY", "STATE", "COUNTRY", "AIRPORTS_IATA_CODE"]:
        if c in airports_raw.columns:
            airports_raw[c] = airports_raw[c].astype("category")

    # HHMM -> time conversion 
    for c in ["SCHEDULED_DEPARTURE", "DEPARTURE_TIME", "SCHEDULED_ARRIVAL", "ARRIVAL_TIME"]:
        if c in flights_raw.columns:
            flights_raw[c] = flights_raw[c].apply(format_hhmm)

    # Standardize codes and merge airport geo fields for origin/destination
    flights_df = flights_raw.copy()
    flights_df[ORIGIN_COL] = flights_df[ORIGIN_COL].astype(str).str.strip().str.upper()
    flights_df[DEST_COL] = flights_df[DEST_COL].astype(str).str.strip().str.upper()

    AIRPORT_CODE_COL = pick_col(airports_raw, ["AIRPORTS_IATA_CODE", "IATA_CODE"])

    origin_airports = airports_raw.rename(columns={
        AIRPORT_CODE_COL: "ORIGIN_AIRPORTS_IATA_CODE",
        "CITY": "ORIGIN_CITY",
        "STATE": "ORIGIN_STATE",
        "COUNTRY": "ORIGIN_COUNTRY",
        "LATITUDE": "ORIGIN_LATITUDE",
        "LONGITUDE": "ORIGIN_LONGITUDE",
    }).copy()
    origin_airports["ORIGIN_AIRPORTS_IATA_CODE"] = origin_airports["ORIGIN_AIRPORTS_IATA_CODE"].astype(str).str.strip().str.upper()


    # Rename the destination airport fields to a distinct prefix before merging.

    dest_airports = airports_raw.rename(columns={
        AIRPORT_CODE_COL: "DEST_AIRPORTS_IATA_CODE",
        "CITY": "DEST_CITY",
        "STATE": "DEST_STATE",
        "COUNTRY": "DEST_COUNTRY",
        "LATITUDE": "DEST_LATITUDE",
        "LONGITUDE": "DEST_LONGITUDE",
    }).copy()
    dest_airports["DEST_AIRPORTS_IATA_CODE"] = dest_airports["DEST_AIRPORTS_IATA_CODE"].astype(str).str.strip().str.upper()


    # merge flight rows with origin airport 
    df = pd.merge(
        flights_df,
        origin_airports,
        left_on=ORIGIN_COL,
        right_on="ORIGIN_AIRPORTS_IATA_CODE",
        how="left",
    )

    # Merge the destination airport 

    df = pd.merge(
        df,
        dest_airports,
        left_on=DEST_COL,
        right_on="DEST_AIRPORTS_IATA_CODE",
        how="left",
    )

    # Compute total delay and apply the cancellation/diversion policy.

    df["TOTAL_DELAY"] = df.apply(total_delay, axis=1)
    max_delay = pd.to_numeric(df["TOTAL_DELAY"], errors="coerce").max()
    df["TOTAL_DELAY"] = df.apply(max_delay_if_cancelled, axis=1, max_delay_value=max_delay)


    # Drop other kind of delay
    to_drop = [
        "AIRLINE_DELAY",
        "LATE_AIRCRAFT_DELAY",
        "AIR_SYSTEM_DELAY",
        "WEATHER_DELAY",
        "SECURITY_DELAY",
    ]

    for i in to_drop:
        df.drop(columns=i, inplace=True)

    # Keep a Neo4j-oriented subset 
    neo_fields = [
        "DATETIME",
        AIRLINE_COL,
        ORIGIN_COL,
        DEST_COL,
        "ORIGIN_AIRPORTS_IATA_CODE",
        "ORIGIN_CITY",
        "ORIGIN_STATE",
        "ORIGIN_LATITUDE",
        "ORIGIN_LONGITUDE",
        "DEST_AIRPORTS_IATA_CODE",
        "DEST_CITY",
        "DEST_STATE",
        "DEST_LATITUDE",
        "DEST_LONGITUDE",
        "DISTANCE",
        "CANCELLATION_REASON",
        "TOTAL_DELAY",
    ]
    neo_fields = [c for c in neo_fields if c in df.columns]
    df_base_final = df[neo_fields].copy()

    # Normalize cancellation reason labels 
    if "CANCELLATION_REASON" in df_base_final.columns:
        cr = df_base_final["CANCELLATION_REASON"].astype("string")
        df_base_final["CANCELLATION_REASON"] = cr.map(BTS_MAP_CANCELLATION_REASON).fillna(cr)

    # Apply the same final null policy used in the report
    nullable_cols = {"CANCELLATION_REASON"}
    colums = set(df_base_final.columns)
    not_nullable_cols = colums - nullable_cols

    # Print intermediate dataset shape
    rows_before = len(df_base_final)
    df_final_clean = df_base_final.dropna(subset=not_nullable_cols).copy()
    rows_after = len(df_final_clean)



    # Build a missing-values report before and after cleaning.
    df_final_fill_report = pd.DataFrame({
        "column": df_base_final.columns,
        "missing_before": [int(df_base_final[c].isna().sum()) for c in df_base_final.columns],
        "missing_after": [int(df_final_clean[c].isna().sum()) for c in df_base_final.columns],
    }).sort_values("missing_before", ascending=False).reset_index(drop=True)


    # Prepare node and relationship tables for Neo4j ingestion
    df_final_clean = df_final_clean.reset_index(drop=True)
    df_final_clean["FLIGHT_ID"] = np.arange(1, len(df_final_clean) + 1)

    origin_nodes = df_final_clean[[
        "ORIGIN_AIRPORTS_IATA_CODE",
        "ORIGIN_CITY",
        "ORIGIN_STATE",
        "ORIGIN_LATITUDE",
        "ORIGIN_LONGITUDE",
    ]].rename(columns={
        "ORIGIN_AIRPORTS_IATA_CODE": "IATA",
        "ORIGIN_CITY": "CITY",
        "ORIGIN_STATE": "STATE",
        "ORIGIN_LATITUDE": "LATITUDE",
        "ORIGIN_LONGITUDE": "LONGITUDE",
    })

    dest_nodes = df_final_clean[[
        "DEST_AIRPORTS_IATA_CODE",
        "DEST_CITY",
        "DEST_STATE",
        "DEST_LATITUDE",
        "DEST_LONGITUDE",
    ]].rename(columns={
        "DEST_AIRPORTS_IATA_CODE": "IATA",
        "DEST_CITY": "CITY",
        "DEST_STATE": "STATE",
        "DEST_LATITUDE": "LATITUDE",
        "DEST_LONGITUDE": "LONGITUDE",
    })

    neo_airports = pd.concat([origin_nodes, dest_nodes], ignore_index=True).drop_duplicates(subset=["IATA"])

    # Build the final flight table used for Neo4j ingestion.
    neo_flights = df_final_clean[[
        "FLIGHT_ID",
        "DATETIME",
        AIRLINE_COL,
        "ORIGIN_AIRPORTS_IATA_CODE",
        "DEST_AIRPORTS_IATA_CODE",
        "DISTANCE",
        "TOTAL_DELAY",
        "CANCELLATION_REASON",
    ]].rename(columns={
        AIRLINE_COL: "AIRLINE_CODE",
        "ORIGIN_AIRPORTS_IATA_CODE": "ORIGIN_IATA",
        "DEST_AIRPORTS_IATA_CODE": "DEST_IATA",
    })


    return df_final_clean, neo_airports, neo_flights


