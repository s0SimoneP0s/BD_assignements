def compare_distributions(original_numerical, sample_numerical, 
                          method='wknd',): # to be implemented
    from scipy.stats import wasserstein_distance_nd
    import numpy as np
    import pandas as pd
    
    total_distance = 0
    matched_cols = 0
    
    for col in original_numerical.columns:
        if col not in sample_numerical.columns:
            continue

        orig_vals = pd.to_numeric(original_numerical[col], errors='coerce').dropna().values
        samp_vals = pd.to_numeric(sample_numerical[col], errors='coerce').dropna().values
        
        if len(orig_vals) > 1 and len(samp_vals) > 1: 
            dist = wasserstein_distance_nd(orig_vals, samp_vals)
            total_distance += dist
            matched_cols += 1   
    
    return total_distance / matched_cols if matched_cols > 0 else float('inf')



def cast_int64(s):
    import hashlib
    import numpy as np
    import pandas as pd
    if pd.isna(s):
        return np.nan
    tmp = hashlib.sha256(str(s).strip().encode('utf-8')).hexdigest()
    return int(tmp, 16) % (2**63-1)  # Fit into int64 range

def convert_to_scaled_numerical_dataset(df_original, column_type: dict, scaler=None):
    """
    Convert the original dataset to a numerical format and apply scaling.
    String columns are normalized and hashed to integers, while numerical columns are converted to numeric types.
    """
    import pandas as pd
    from sklearn.preprocessing import MinMaxScaler, StandardScaler, RobustScaler

    df = df_original.copy()
    string_columns = [col for col, typ in column_type.items() if typ == 'Str']

    # 1. string columns should be object or other dtypes , cast all to strings
    if string_columns:
        # 1. normalize string columns
        for col in string_columns:
            s = df[col].astype("string")             # pandas StringDtype
            s = s.where(s.notna(), pd.NA)            # keep pd.NA
            s = s.str.strip()                        # trim whitespace
            s = s.replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA})
            df[col] = s
        
        # normalize into int64
        for col in string_columns:
            df[col] = df[col].apply(cast_int64)

    numerical_columns = [col for col, typ in column_type.items() if typ == 'Val']
    if numerical_columns:
        for col in numerical_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')


    if scaler is None:
        scaler = StandardScaler()
        numerical_scaled = scaler.fit_transform(df)

    else:
        numerical_scaled = scaler.transform(df)
    
    numerical_dataset_scaled = pd.DataFrame(
        numerical_scaled, 
        columns=df.columns, 
        index=df.index
    )

    return numerical_dataset_scaled, scaler



def find_most_representative_sample(
        df_original, 
        column_type,
        GLOBAL_SEED:int=None,
        SAMPLE_SIZE:int=1000, 
        n_trials=10, 
        method='wsnd'
      ):
    
    """
    Parameters:
    -----------
    df_original: pandas.DataFrame
        The original dataset from which to sample.
    column_type: dict
        A dictionary mapping column names to their types ('Str' for string, 'Val' for numerical).
    GLOBAL_SEED: int, optional
        A global seed for reproducibility. If None, a random seed will be used.
    SAMPLE_SIZE: int
        The number of samples to draw for each trial.
    n_trials: int
        The number of random samples to generate and evaluate.
    method: str
        The method to use for comparing distributions. Currently only 'wsnd' (Wasserstein distance) is implemented.
    """

    # Convert the entire original dataset to numerical format
    numerical_scaled_df, scaler = convert_to_scaled_numerical_dataset( df_original, column_type)
    
    best_seed = None
    
    # Generate random seeds list
    import random
    random.seed(GLOBAL_SEED or 667)
    random_numbers = [random.randint(0, 2**32 - 1) for _ in range(n_trials)]
    random_samples = [ df_original.sample(n=SAMPLE_SIZE, random_state=seed) for seed in  random_numbers]
    scaled_random_samples = []
    for sample in random_samples:
        sample_scaled_df, _ = convert_to_scaled_numerical_dataset(sample, column_type, scaler) # the scaler is the same for all samples to ensure values comparability
        scaled_random_samples.append(sample_scaled_df)

    best_distances : float = float('inf')
    best_seed : int | None = None
    for seed_idx, sample_scaled in enumerate(scaled_random_samples):
        distance = compare_distributions(numerical_scaled_df, sample_scaled)

        if distance < best_distances:
            best_distances = distance
            best_seed = random_numbers[seed_idx]


    return df_original.sample(n=SAMPLE_SIZE, random_state=best_seed)



def generic_df_into_numeric_and_rollback(df, metadata=None): 
    """
    Return unscaled numeric and metadata

    """
    import numpy as np
    import pandas as pd
    from sklearn.feature_extraction.text import TfidfVectorizer
    # branch for first call, we compute metadata
    # Encoders
    if metadata is None: 
        df_numeric = df.copy()
        metadata = {}
        for col in df.columns:

            curr_type = str(df[col].dtype.name)
            metadata[col] = {"type":curr_type}

            if curr_type in ['int64', 'float64']:
                # numeric passthrough
                continue
            elif curr_type == 'category':
                #code_int = df[col].cat.codes # int, if NaN -> -1
                #codes_float = code_int.astype("float64")
                #codes_float[codes_float == -1] = np.nan
                #df_numeric[col] = codes_float
                # pd.factorize alternatives
                # factorize: -1 per missing, uniques con i livelli osservati
                codes, uniques = pd.factorize(df[col], sort=False, use_na_sentinel=True)

                # NaN is -1
                codes = pd.Series(codes, index=df.index).astype("float64")
                codes[codes == -1] = np.nan
                df_numeric[col] = codes

                # rollback metadata
                metadata[col] = {
                    "data": uniques.astype("string").tolist()
                }

            elif curr_type in ['string', 'object']:
                model = TfidfVectorizer(
                    analyzer="word",
                    ngram_range=(1, 1),
                    lowercase=True,
                )
                corpus = df[col].astype("string").fillna("").tolist()
                model.fit(corpus)
                Y = model.transform(corpus)
                df_numeric[col] = Y.toarray()

                # rollback metadata
                metadata[col] = {
                    "data": None
                }
            else:
                try:
                    df_numeric[col] = pd.to_numeric(df[col], errors='coerce')
                    metadata[col] = { "data": None  }
                except:
                    df_numeric[col] = df[col].apply(cast_int64)
                    metadata[col] = { "data": None  }

        return df_numeric, metadata
    
    # 2) ROLLBACK: rebuild original-like df using metadata
    df_restored = df.copy()

    for col in set(df.columns):
        
        if not (info := metadata.get(col, {})):
            print(f"Warning: no metadata for column {col}, skipping restoration.")
            continue
        curr_type = info.get("type")
        if curr_type in ['int64', 'float64']:
            continue

        elif curr_type == 'category':

            uniques = pd.Index(info["data"], dtype="string")
            x = pd.Series(df[col], index=df.index)

            # round to Int64, then map back to categories
            codes = pd.Series(np.rint(x), index=df.index).astype("Int64")
            valid = codes.notna() & (codes >= 0) & (codes < len(uniques))
            out = pd.Series(pd.NA, index=df.index, dtype="string")
            out.loc[valid] = uniques[codes.loc[valid].astype(int)].to_numpy()

            df_restored[col] = pd.Categorical(out, categories=uniques)

        else:
            continue

    return df_restored, metadata



