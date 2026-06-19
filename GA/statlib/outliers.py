# check outliers



def _sinkhorn_knopp(M: 'pd.DataFrame', iterations: int = 100, tol: float = 1e-7) -> 'pd.DataFrame':
    import numpy as np
    import pandas as pd
    A = M.to_numpy(dtype=float)
    
    # no zero div
    epsilon = 1e-12
    A = np.maximum(A, epsilon)
    
    for _ in range(iterations):
        # row norm
        row_sums = A.sum(axis=1, keepdims=True)
        A /= np.where(row_sums > 0, row_sums, 1.0)
        
        # column norm
        col_sums = A.sum(axis=0, keepdims=True)
        A /= np.where(col_sums > 0, col_sums, 1.0)
        
        # convergence
        if np.allclose(A.sum(axis=1), 1.0, atol=tol) and np.allclose(A.sum(axis=0), 1.0, atol=tol):
            break
            
    return pd.DataFrame(A, index=M.index, columns=M.columns)




def esimate_outliers( 
                      df : 'pd.DataFrame', 
                      LIMITS:dict  ,
                      method : str = 'count',
                      lower_percentile: float = 0.25, 
                      upper_percentile: float = 0.75,
                      ) -> 'pd.Series':
    """
    
    True is an outliers

    Need a dictionary for manual limit due to domain knowledge

    Example limits
    
    LIMITS = {                                   # Field:(min,max) generically
        'Density': (0.9, 1.1),                    # g/cm³ (corpo umano ~1.0)
        'BodyFat': (3, 60),                       # % (atleti 3-15%, obesi >40%)
    }
    """
    import numpy as np
    import pandas as pd
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.preprocessing import StandardScaler
    df_score = pd.DataFrame(index=df.index, columns=df.columns)
    
    if method == 'percentile': # write hown min max value
        for col in df.columns:
            qmin, qmax = df[col].quantile([lower_percentile, upper_percentile])
            LIMITS[col] = (qmin, qmax)
    
    for col in df.columns:
        low, high = LIMITS[col]
        s = df[col]
        df_score[col] = (df[col] < low) | (df[col] > high) # True 1, False 0

    if method == 'sinkhorn':
        df_score = _sinkhorn_knopp(df_score)
    if method == 'count':
        pass
    
    score = df_score.sum(axis=1)
    score.name = 'outliers_score'

    alt_scaler = StandardScaler()
    scaler=MinMaxScaler(feature_range=(0, 1))

    return  scaler.fit_transform(score.values.reshape(-1, 1)).flatten()  # normalized in P





def cast_numeric_dummy_category(
    df_input: 'pd.DataFrame',
    metadata : dict | None=None,
    category_encoding : str ="codes",
):
    """
    Convert DataFrame to numeric and rollback with metadata.

    Category encoding modes:
    - codes: category -> integer code (reversible)

    If metadata is None:
        returns (df_numeric, metadata)
    If metadata is provided:
        treats df as encoded numeric and rebuilds original-like df:
        returns (df_restored, metadata)
    """
    import numpy as np
    import pandas as pd
    from exam.GA.statlib.representative_sample import cast_int64

    prefix_sep = "__"
    drop_first = True

    allowed_enc = {"codes", "dummy", "onehot"}
    if category_encoding not in allowed_enc:
        raise ValueError(f"Unsupported category_encoding='{category_encoding}'. Allowed: {sorted(allowed_enc)}")

    # ----------------------------
    # ENCODE BRANCH
    # ----------------------------
    if metadata is None:
        df_numeric = pd.DataFrame(index=df_input.index)
        metadata = {
            "columns": {},
            "category_encoding": category_encoding,
            "prefix_sep": prefix_sep,
            "drop_first": drop_first,
        }

        for col in df_input.columns:
            s = df_input[col]
            curr_type = str(s.dtype.name)
            info = {"type": curr_type, "encoding": "passthrough"}

            if curr_type in ["int64", "float64"]:
                df_numeric[col] = pd.to_numeric(s, errors="coerce")

            elif curr_type in ["bool", "boolean"]:
                df_numeric[col] = s.astype("float64")
                info["encoding"] = "bool_to_float"

            elif curr_type.startswith("datetime64"):        
                x = s.astype("int64").astype("int64")
                x[s.isna()] = np.nan
                df_numeric[col] = x
                info["encoding"] = "datetime_int64"

            elif curr_type == "category":
                cats = s.cat.categories.astype("string")
                info["data"] = cats.tolist()

                if category_encoding == "codes":
                    codes = s.cat.codes.astype("float64")
                    #codes[codes < 0] = np.nan
                    df_numeric[col] = codes
                    info["encoding"] = "codes"
                elif category_encoding in ("dummy", "onehot"):
                    dummies = pd.get_dummies(
                        s,
                        prefix=col,
                        prefix_sep=prefix_sep,
                        drop_first=drop_first,
                        dtype="float64",
                    )
                    #df_numeric = pd.concat([df_numeric, dummies], axis=1)
                    df_numeric = pd.concat([df_numeric, dummies], axis=1)
                    df_numeric.drop(columns=[col], inplace=True, errors="ignore")
                    info["encoding"] = category_encoding
                    info["onehot_columns"] = dummies.columns.tolist()
                    info["dropped_category"] = str(cats[0]) if (drop_first and len(cats) > 0) else None
                    info["prefix_sep"] = prefix_sep
                else:
                    raise ValueError(f"Unsupported category_encoding='{category_encoding}' for category dtype.")

            else:
                num = pd.to_numeric(s, errors="coerce")
                if num.notna().sum() > 0:
                    df_numeric[col] = num
                    info["encoding"] = "to_numeric"
                else:
                    df_numeric[col] = s.apply(cast_int64)
                    info["encoding"] = "hash_int64"

            metadata["columns"][col] = info

        return df_numeric, metadata

    # ----------------------------
    # ROLLBACK BRANCH
    # ----------------------------
    columns_meta = metadata.get("columns", metadata)
    df_restored = pd.DataFrame(index=df_input.index)

    for col, info in columns_meta.items():
        enc = info.get("encoding", "passthrough")

        if enc in ("passthrough", "to_numeric"):
            if col in df_input.columns:
                df_restored[col] = pd.to_numeric(df_input[col], errors="coerce")
            else:
                df_restored[col] = np.nan
            continue

        if enc == "bool_to_float":
            if col in df_input.columns:
                x = pd.to_numeric(df_input[col], errors="coerce")
                out = pd.Series(pd.NA, index=df_input.index, dtype="boolean")
                valid = x.notna()
                out.loc[valid] = x.loc[valid] >= 0.5
                df_restored[col] = out
            else:
                df_restored[col] = pd.Series(pd.NA, index=df_input.index, dtype="boolean")
            continue

        if enc == "datetime_int64":
            if col in df_input.columns:
                x = pd.to_numeric(df_input[col], errors="coerce")
                vals = pd.Series(np.rint(x), index=df_input.index).astype("Int64")
                df_restored[col] = pd.to_datetime(vals, unit="ns", errors="coerce")
            else:
                df_restored[col] = pd.NaT
            continue

        if enc == "codes":
            cats = pd.Index(info.get("data", []), dtype="string")
            if col in df_input.columns:
                x = pd.Series(df_input[col], index=df_input.index)
                codes = pd.Series(np.rint(x), index=df_input.index).astype("Int64")
                valid = codes.notna() & (codes >= 0) & (codes < len(cats))
                out = pd.Series(pd.NA, index=df_input.index, dtype="string")
                if valid.any():
                    out.loc[valid] = cats[codes.loc[valid].astype(int)].to_numpy()
                df_restored[col] = pd.Categorical(out, categories=cats)
            else:
                df_restored[col] = pd.Categorical(
                    pd.Series(pd.NA, index=df_input.index, dtype="string"),
                    categories=cats,
                )
            continue

        if enc in ("dummy", "onehot", "onehot_drop_first"):
            cats = pd.Index(info.get("data", []), dtype="string")
            onehot_cols = list(info.get("onehot_columns", []))
            sep = info.get("prefix_sep", metadata.get("prefix_sep", prefix_sep))
            dropped = info.get("dropped_category")

            block = pd.DataFrame(index=df_input.index)
            for oh_col in onehot_cols:
                if oh_col in df_input.columns:
                    block[oh_col] = pd.to_numeric(df_input[oh_col], errors="coerce").fillna(0.0)
                else:
                    block[oh_col] = 0.0

            if dropped is not None:
                dropped_col = f"{col}{sep}{dropped}"
                if dropped_col not in block.columns:
                    base = (block.sum(axis=1) <= 0).astype("float64")
                    block.insert(0, dropped_col, base)

            out = pd.Series(pd.NA, index=df_input.index, dtype="string")
            if block.shape[1] > 0:
                mat = block.to_numpy(dtype="float64")
                argm = np.argmax(mat, axis=1)
                maxv = mat[np.arange(len(block)), argm]
                labels = pd.Index(
                    [
                        c.split(f"{col}{sep}", 1)[1]
                        if c.startswith(f"{col}{sep}")
                        else c
                        for c in block.columns
                    ],
                    dtype="string",
                )
                valid = maxv > 0
                if valid.any():
                    out.loc[valid] = labels[argm[valid]].to_numpy()

            df_restored[col] = pd.Categorical(out, categories=cats)
            continue

        if enc == "hash_int64":
            if col in df_input.columns:
                df_restored[col] = pd.to_numeric(df_input[col], errors="coerce")
            else:
                df_restored[col] = np.nan
            continue

        if col in df_input.columns:
            df_restored[col] = df_input[col]
        else:
            df_restored[col] = np.nan

    return df_restored, metadata




def outliers_mask(df_input: 'pd.DataFrame', method: str = "zscore", 
                  value_1 : float|int|None = None, 
                  value_2 : float|int|None = None) -> 'pd.Series':

    """
    
        df_input : numeric scaled not null values are required 
        method : one of "zscore", "mahalanobis", "iqr", "kde", "dbscan", "lof"
    """

    from scipy.stats import zscore, chi2
    from sklearn.preprocessing import StandardScaler
    from sklearn.covariance import MinCovDet
    from sklearn.neighbors import KernelDensity, LocalOutlierFactor
    from sklearn.cluster import DBSCAN
    import numpy as np
    import pandas as pd

    method = method.lower().strip()

    # default all rows to False; only valid rows can become True
    

    if method == "zscore":
        threshold = float(value_1) if value_1 is not None else 3.0
        z_values = zscore(df_input, axis=0, nan_policy='omit')
        mask = (np.abs(z_values) > threshold).any(axis=1) 

    elif method == "iqr":
        k = float(value_1) if value_1 is not None else 1.5
        q1 = df_input.quantile(0.25)
        q3 = df_input.quantile(0.75)
        iqr = q3 - q1
        low = q1 - k * iqr
        high = q3 + k * iqr
        mask = (df_input.lt(low, axis=1) | df_input.gt(high, axis=1)).any(axis=1)

    elif method == "mahalanobis":
        alpha = float(value_1) if value_1 is not None else 0.95
        model = MinCovDet()
        model.fit(df_input)
        md2 = model.mahalanobis(df_input)
        threshold = chi2.ppf(alpha, df=df_input.shape[1])
        mask = md2 > threshold

    elif method == "kde":
        bandwidth = float(value_1) if value_1 is not None else 1.0
        quantile_cutoff = float(value_2) if value_2 is not None else 0.02

        model = KernelDensity(bandwidth=bandwidth)
        model.fit(df_input)
        scores = model.score_samples(df_input)
        threshold = np.quantile(scores, quantile_cutoff)
        mask = scores > threshold

    elif method == "dbscan":
        eps = float(value_1) if value_1 is not None else 0.8
        min_samples = int(value_2) if value_2 is not None else 10
        model = DBSCAN(eps=eps, min_samples=min_samples)
        model.fit(df_input)
        mask = model.labels_ == -1

    elif method == "lof":
        n_neighbors = int(value_1) if value_1 is not None else 20
        contamination = float(value_2) if value_2 is not None else 0.02

        lof = LocalOutlierFactor(
            n_neighbors=n_neighbors,
            contamination=contamination,
            novelty=False,
        )
        labels = lof.fit_predict(df_input)
        mask = labels == -1

    else:
        raise ValueError(
            "Method not supported. Use one of: "
            "'zscore', 'mahalanobis', 'iqr', 'kde', 'dbscan', 'lof'"
        )

    return pd.Series(mask, index=df_input.index, name="is_outlier")




def plot_pca_2d(
    df_input: 'pd.DataFrame',
    title="PCA 2D",
    seed=0,
    outlier_mask=None,
    figsize=(6, 5),
    method : str = 'pca'
):
    from sklearn.decomposition import PCA, KernelPCA
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    if method=="pca":
        reducer=PCA(n_components=2, random_state=seed)
    elif method=="poly_k":
        reducer = KernelPCA(
            n_components=2,
            kernel="poly",
            degree=2,          # polynomial degree
            gamma=1.0,         # scaling of inner product
            coef0=1.0,         # adds lower-order terms
            fit_inverse_transform=False,
            eigen_solver="auto"
        )

    pipe_pca = Pipeline([
        ("scaler", StandardScaler()),
        ("pca", reducer),
    ])

    pca_vect = pipe_pca.fit_transform(df_input)
    x_pca= pca_vect[:, 0]
    y_pca= pca_vect[:, 1]

    plt.figure(figsize=figsize)

    if outlier_mask is not None:
        outlier_mask = np.asarray(outlier_mask).astype(bool).ravel()
        inlier_mask = ~outlier_mask

        plt.scatter(
            x_pca[inlier_mask],
            y_pca[inlier_mask],
            c = "tab:blue", # stabdard values
            alpha=0.65,
        )
        plt.scatter(
            x_pca[outlier_mask],
            y_pca[outlier_mask],
            c='tab:red', # outliers
            alpha=0.95,
            marker=".",
        )


    else:
        plt.scatter(x_pca, y_pca, c="tab:blue", alpha=0.8)

    plt.title(title)
    plt.xlabel("")
    plt.ylabel("")
    plt.grid(alpha=0.2)
    plt.tight_layout()
    plt.show()
