

## TAKEN FROM https://stats.stackexchange.com/questions/403652/two-sample-quantile-quantile-plot-in-python
## Solution provided by user: Artem Mavrin
def qqplot(
               x, y,                    # array-like One-dimensional numeric arrays
               quantiles  =None,        #  int or array-like, Quantiles to include in the plot. when none `min(len(x), len(y))`
               method='nearest',        # {‘linear’, ‘lower’, ‘higher’, ‘midpoint’, ‘nearest’}
               ax=None,                 # matplotlib.axes.Axes
               rug=False,               # bool ; draw a rug plot representing both horizontal and vertical axes
               rug_length=0.05,         # float ∈ [0, 1], fraction length of each the rug plot
               rug_kwargs=None,         # dict for matplotlib.axes.Axes.axvline() and matplotlib.axes.Axes.axhline()
               **kwargs                 # arguments to pass to matplotlib.axes.Axes.scatter()
          ):
    import numpy as np
    import matplotlib.pyplot as plt
    # Get current axes if none are provided
    if ax is None:
        ax = plt.gca()

    if quantiles is None:
        quantiles = min(len(x), len(y))
        
    import numbers
    # Compute quantiles of the two samples
    if isinstance(quantiles, numbers.Integral):
        quantiles = np.linspace(start=0, stop=1, num=int(quantiles))
    else:
        quantiles = np.atleast_1d(np.sort(quantiles))
    x_quantiles = np.quantile(x, quantiles, method=method)
    y_quantiles = np.quantile(y, quantiles, method=method)

    minimum=np.min([np.min(x),np.min(y)])
    maximum=np.max([np.max(x),np.max(y)])

    # Draw the rug plots if requested
    if rug:
        # Default rug plot settings
        rug_x_params = dict(ymin=0, ymax=rug_length, c='gray', alpha=0.5)
        rug_y_params = dict(xmin=0, xmax=rug_length, c='gray', alpha=0.5)

        # Override default setting by any user-specified settings
        if rug_kwargs is not None:
            rug_x_params.update(rug_kwargs)
            rug_y_params.update(rug_kwargs)

        # Draw the rug plots
        for point in x:
            ax.axvline(point, **rug_x_params)
        for point in y:
            ax.axhline(point, **rug_y_params)

    # Draw the q-q plot
    ax.scatter(x_quantiles, y_quantiles, **kwargs)
    ax.axline([minimum, minimum], [maximum, maximum], color='k')




def df_qqplot(df, reference=None, n_rows=1, n_cols=None, quantiles=100,
                     figsize=(10, 4),  **kwargs):
    import numpy as np
    import matplotlib.pyplot as plt
    if n_cols is None:
        n_cols = int(np.ceil(len(df.columns) / n_rows))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize, squeeze=False)

    for ax, col in zip(axes.flatten(), df.columns):
        x = df[col].dropna().values
        y = reference if reference is not None else np.random.normal(x.mean(), x.std(), len(x))

        qqplot(x=x, y=y, quantiles=quantiles, ax=ax, alpha=0.5, **kwargs)
        ax.set_title(f'{col} QQ-plot')
        ax.set_xlabel('')

    plt.tight_layout() ;



# refactor for the previous solution

def qqplot_easy(x, y, n=100, ax=None,method='nearest', **kwargs):
    import numpy as np
    import matplotlib.pyplot as plt
    """Simplest QQ plot: compare quantiles of x and y."""
    if ax is None:
        ax = plt.gca()
    
    qs = np.linspace(0, 1, n)
    xq = np.quantile(x, qs,method=method)
    yq = np.quantile(y, qs,method=method)
    
    # Plot on the specified axis
    ax.plot(xq, yq, 'o', markersize=3, **kwargs)
    
    # Reference line y = x
    lims = [min(xq.min(), yq.min()), max(xq.max(), yq.max())]
    ax.plot(lims, lims, 'r--')
    ax.set_xlabel('X quantiles')
    ax.set_ylabel('Y quantiles')
    ax.set_title('QQ plot')



def df_qqplot_easy(df, reference=None, n_rows=1, n_cols=None, quantiles=100,
                   figsize=(10, 4), **kwargs):
    import numpy as np
    import matplotlib.pyplot as plt
    """Create QQ plots for all columns in a DataFrame."""
    
    if n_cols is None:
        n_cols = int(np.ceil(len(df.columns) / n_rows))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize, squeeze=False)
    axes = axes.flatten()  # Flatten for easier iteration

    for i, col in enumerate(df.columns):
        if i >= len(axes):  # Avoid index error if more columns than subplots
            break
            
        x = df[col].dropna().values
        if x.size == 0:
            continue

        # Use reference if provided, otherwise generate normal distribution
        if reference is not None:
            if isinstance(reference, np.ndarray):
                y = reference
            else:
                y = reference
        else:
            y = np.random.normal(x.mean(), x.std(), len(x))
        
        # Call qqplot_easy with the current axis
        qqplot_easy(x, y, n=quantiles, ax=axes[i], **kwargs)
        
        # Customize the subplot
        axes[i].set_title(f'{col}')
        axes[i].set_xlabel('')
        axes[i].set_ylabel('')

    # Hide any unused subplots
    for j in range(i+1, len(axes)):
        axes[j].set_visible(False)

    plt.tight_layout()
    plt.show()



def df_hist_compare(df_1, df_2, label_1='df_1', label_2='df_2', n_rows=1, n_cols=None,
                    quantiles=100, figsize=(10, 4), **kwargs):
    import seaborn as sns
    import numpy as np
    import matplotlib.pyplot as plt
    """Compare distributions of two DataFrames column by column using overlapping histograms."""
  
    # test comparability
    if set(df_1.columns) != set(df_2.columns):
        print(f"Columns in df_1: {set(df_1.columns)}")
        print(f"Columns in df_2: {set(df_2.columns)}")  
        raise ValueError(f"Columns difference: {set(df_1.columns).symmetric_difference(set(df_2.columns))}")
    

    if n_cols is None:
        n_cols = int(np.ceil( len(df_1.columns) // n_rows))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize, squeeze=False, sharey=False)


    for ax, df1_col, df2_col in zip(axes.flatten(), (df_1.columns) ,  (df_2.columns) ):
        sns.histplot(data=df_1, x=df1_col, kde=True, ax=ax, fill=True, )
        sns.histplot(data=df_2, x=df2_col, kde=True, ax=ax, fill=True, )
        ax.set_title(f'{df1_col}')
        ax.set_xlabel('')
        ax.set_xticks([])
    plt.tight_layout() ;



def plot_numeric_grid(df, n_rows=1, n_cols=None, figsize=(10, 4), title:str =None):
    import seaborn as sns
    import numpy as np
    import matplotlib.pyplot as plt
    if n_cols is None:
        n_cols = int(np.ceil( len(df.columns) // n_rows))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize, squeeze=False, sharey=False)
    
    # Plot per ogni feature
    for ax, col in zip(axes.flatten(), (df.columns)):
        sns.histplot(data=df, x=col, kde=True, ax=ax, fill=True, )
        ax.set_title(f'{col}')
        ax.set_xlabel('')
        ax.set_xticks([])
    if title:
        fig.suptitle(title)
    plt.tight_layout() ;




def dataframe_into_numeric(df, normalize:bool=False):
    """
    Return unscaled numeric 
    """
    import pandas as pd
    from statlib.representative_sample import cast_int64
    df_numeric = df.copy()
    for col in df.columns:
        if df[col].dtype not in ['int64', 'float64']:
            try:
                df_numeric[col] = pd.to_numeric(df[col], errors='coerce')
            except:
                df_numeric[col] = df[col].apply(cast_int64)

    if normalize:
        from sklearn.preprocessing import MinMaxScaler, StandardScaler, RobustScaler
        scaler = StandardScaler()
        numerical_scaled = scaler.fit_transform(df_numeric)
        df_numeric = pd.DataFrame(numerical_scaled, columns=df_numeric.columns)

    return df_numeric


