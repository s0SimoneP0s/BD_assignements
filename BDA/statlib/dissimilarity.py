from joblib import Parallel, delayed
from sklearn.metrics.pairwise import cosine_similarity
from scipy.spatial.distance import euclidean
from scipy.spatial.distance import jaccard  # asymmetric binary distance
from sklearn.feature_extraction.text import TfidfVectorizer

# -----------------------
# Distance classes
# -----------------------

def nominal_distance(x, y):

    p = len(x)
    m = sum(1 if a == b else 0 for a, b in zip(x, y))
    return float(p - m) / p

def symmetric_binary_distance(arr1, arr2):
    """
    Compute the symmetric binary distance between two binary arrays.

    Parameters:
        arr1 (array-like): The first binary array.
        arr2 (array-like): The second binary array.

    Returns:
        float: The symmetric binary distance.
    """
    # Compute the contingency table
    ct = [[0, 0], [0, 0]]
    for a, b in zip(arr1, arr2):
        ct[a][b] += 1

    # Compute the symmetric binary distance
    numerator = ct[0][1] + ct[1][0]
    denominator = sum(sum(row) for row in ct)
    distance = numerator / denominator

    return distance

def cosine_distance_TF_IDF_BOW(tfidf_matrix, i, j):
    """
    tfidf_matrix : scipy sparse matrix of shape (n_samples, n_features)
        TF-IDF representation for one text column.
    i, j : int
        Row indices.
    """
    sim = cosine_similarity(tfidf_matrix[i], tfidf_matrix[j])[0, 0]
    return 1.0 - sim


# -----------------------
# dissimilarity function
# -----------------------
import pandas as pd
def parallel_dissimilarity_matrix(df:pd.DataFrame, dict_types : dict):
    """
    Compute a mixed-type pairwise dissimilarity matrix.

    Supported types
    ---------------
    'NO' : Nominal
    'NU' : Numerical
    'SB' : Symmetric Binary
    'AB' : Asymmetric Binary
    'TX' : Text/String using TF-IDF (single-word bag of words) + cosine dissimilarity

    Parameters
    ----------
    df : pandas.DataFrame
        Input dataframe with mixed attribute types.
    dict_types : dict
        Dictionary mapping column names to type codes.

    Returns
    -------
    pandas.DataFrame
        Symmetric dissimilarity matrix.
    """
    import numpy as np


    num_records = df.shape[0]
    dissimilarity_matrix = np.zeros((num_records, num_records), dtype=float)

    distance_functions = {
        'NO': nominal_distance,
        'NU': euclidean,
        'SB': symmetric_binary_distance,
        'AB': jaccard,
        'TX': cosine_distance_TF_IDF_BOW,   # handled separately (need to create overall vocabulary)
    }

    # Pre-extract raw data for non-text columns
    data = {col: df[col].values for col in dict_types.keys()}

    # --------------------------------------------------
    # Precompute TF-IDF matrices for text columns
    # --------------------------------------------------
    text_columns = [col for col, coltype in dict_types.items() if coltype == 'TX']
    tfidf_data = {}

    for col in text_columns:
        # Replace NaN with empty string for vectorization
        corpus = df[col].fillna("").astype(str).values

        vectorizer = TfidfVectorizer(
            lowercase=True,
            analyzer="word",
            ngram_range=(1, 1)   # single words only
        )
        tfidf_matrix = vectorizer.fit_transform(corpus)

        tfidf_data[col] = {
            "vectorizer": vectorizer,
            "matrix": tfidf_matrix
        }

    def compute_dissimilarity(i : int, j : int ) -> float:
        dissimilarity = 0.0
        num_valid_elements = 0

        for col, coltype in dict_types.items():
            val_i = data[col][i]
            val_j = data[col][j]

            if coltype == 'TX':
                # For text, consider missing only if original value is NaN
                if pd.notna(val_i) and pd.notna(val_j):
                    tfidf_matrix = tfidf_data[col]["matrix"]
                    distance_func = distance_functions[coltype]
                    dissimilarity += distance_func(tfidf_matrix, i, j)
                    num_valid_elements += 1
            else:
                # Non-text columns
                if pd.notna(val_i) and pd.notna(val_j):
                    distance_func = distance_functions[coltype]
                    dissimilarity += distance_func([val_i], [val_j])

                    # For AB, ignore double-zero matches in denominator
                    if not (coltype == 'AB' and (val_i == 0 and val_j == 0)):
                        num_valid_elements += 1

            if coltype == 'TX':
                # For text, consider missing only if original value is NaN
                if pd.notna(val_i) and pd.notna(val_j):
                    tfidf_matrix = tfidf_data[col]["matrix"]
                    distance_func = distance_functions[coltype]
                    dissimilarity += distance_func(tfidf_matrix, i, j)
                    num_valid_elements += 1
            else:
                # Non-text columns
                if pd.notna(val_i) and pd.notna(val_j):
                    distance_func = distance_functions[coltype]
                    dissimilarity += distance_func([val_i], [val_j])

                    # For AB, ignore double-zero matches in denominator
                    if not (coltype == 'AB' and (val_i == 0 and val_j == 0)):
                        num_valid_elements += 1

        if num_valid_elements > 0:
            return dissimilarity / num_valid_elements
        return np.nan

    upper_tri_pairs = [
        (i, j)
        for i in range(num_records - 1)
        for j in range(i + 1, num_records)
    ]

    results = Parallel(n_jobs=-1)(
        delayed(compute_dissimilarity)(i, j) for (i, j) in upper_tri_pairs
    )

    for (i, j), val in zip(upper_tri_pairs, results):
        dissimilarity_matrix[i, j] = val
        dissimilarity_matrix[j, i] = val

    np.fill_diagonal(dissimilarity_matrix, 0.0)

    return pd.DataFrame(dissimilarity_matrix, index=df.index, columns=df.index)



