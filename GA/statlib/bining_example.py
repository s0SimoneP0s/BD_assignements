import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# dati di esempio
rng = np.random.default_rng(42)
data = pd.DataFrame({
    "valore": np.concatenate([
        rng.normal(loc=10, scale=2, size=500),
        rng.normal(loc=20, scale=3, size=300),
        rng.normal(loc=35, scale=5, size=200),
    ])
})

# 1) Equal-width binning with pd.cut
n_bins = 6
bins_equal_width = np.linspace(data['valore'].min(), data['valore'].max(), n_bins + 1)
labels_ew = [f"EW{i+1}" for i in range(n_bins)]
data['bin_equal_width'] = pd.cut(data['valore'], bins=bins_equal_width, labels=labels_ew, include_lowest=True)

# 2) Equal-frequency binning (quantile) with pd.qcut
n_qbins = 6
labels_qf = [f"QF{i+1}" for i in range(n_qbins)]
data['bin_equal_freq'] = pd.qcut(data['valore'], q=n_qbins, labels=labels_qf, precision=3, duplicates='drop')

# 3) Knowledge-driven binning (maual)
cut_points = [0, 12, 18, 25, 30, 50]  # esempio di soglie basate su dominio
labels_kd = ["Very Low", "Low", "Medium", "High", "Very High"]
data['bin_knowledge'] = pd.cut(data['valore'], bins=cut_points, labels=labels_kd, include_lowest=True)
