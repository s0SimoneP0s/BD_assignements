

def compute_statistical_tests(df,missing_mask):
    import pandas as pd
    import numpy as np
    from scipy.stats import chi2_contingency
    from scipy.stats import chi2
    from scipy.stats import ttest_ind,fisher_exact,skewtest,mannwhitneyu

    missing_feats=missing_mask.columns
    
    MCAR_results={}

    for feat in missing_feats: 
        results={}
        df_missing = df.loc[missing_mask[feat]]
        df_not_missing = df.loc[~missing_mask[feat]]
        other_feats= list(set(df.columns)-set([feat]))
        if len(df_missing)>20:
            for col in other_feats:
                results[col]=[]
                if len(df[col].value_counts())>=10: ### if the feature is numerical (not categorical)
                    q50=df_missing[col].quantile(0.5)
                    q25=df_missing[col].quantile(0.25)
                    q75=df_missing[col].quantile(0.75)
                    total_nr = df_missing[col].notna().sum()
                    results[col].append(f'{round(q50,1)} [{round(q25,1)}-{round(q75,1)}] - {total_nr}')

                    q50=df_not_missing[col].quantile(0.5)
                    q25=df_not_missing[col].quantile(0.25)
                    q75=df_not_missing[col].quantile(0.75)
                    total_nr = df_not_missing[col].notna().sum()
                    results[col].append(f'{round(q50,1)} [{round(q25,1)}-{round(q75,1)}] - {total_nr}')

                    try:
                        skt1,p1=skewtest(df_not_missing[[col]].dropna())
                        skt2,p2=skewtest(df_missing[[col]].dropna())
                        if p1[0]<=0.05 and p2[0]<=0.05:
                            res=mannwhitneyu(df_not_missing[[col]].dropna(), df_missing[[col]].dropna())
                            p_value = round(res.pvalue[0],3)
                        elif (~np.isnan(p1[0])) and (~np.isnan(p2[0])):
                            stat, p_value = ttest_ind(df_not_missing[[col]].dropna(), df_missing[[col]].dropna())
                            p_value=round(p_value[0],3)
                        else: 
                            p_value = np.nan
                    except: 
                        p_value = np.nan
                    
                    results[col].append(p_value)

                else: ## if the feature is categorical 
                    unique_values = df_missing[col].value_counts().index
                    unique_abs_frequencies = df_missing[col].value_counts().values
                    unique_rel_frequencies = (df_missing[col].value_counts()/df_missing[col].value_counts().sum()).values
                    total_nr = df_missing[col].notna().sum()
                    results[col].append(f'{tuple(unique_values)} {tuple(unique_abs_frequencies)} {tuple(np.round(unique_rel_frequencies,2).tolist())} - {total_nr}')
            
                    unique_values = df_not_missing[col].value_counts().index
                    unique_abs_frequencies = df_not_missing[col].value_counts().values
                    unique_rel_frequencies = (df_not_missing[col].value_counts()/df_not_missing[col].value_counts().sum()).values
                    total_nr = df_not_missing[col].notna().sum()
                    results[col].append(f'{tuple(unique_values)} {tuple(unique_abs_frequencies)} {tuple(np.round(unique_rel_frequencies,2).tolist())} - {total_nr}')

                    contingency=pd.crosstab(index=df[col] , columns=df[feat])
                    table=contingency.to_numpy()
            
                    if table.shape==(2,2) and (table<5).sum()>0:
                        p_value=fisher_exact(table).pvalue
                        p_value=round(p_value,3)
                    else:
                        stat, p_value, dof, expected = chi2_contingency(table)
                        p_value=round(p_value,4)
                    results[col].append(p_value)
            
            df_results=pd.DataFrame(results).T
            df_results.columns = [f'Missing {feat}', f'Non-missing {feat}', 'p-value']
            MCAR_results[feat]=df_results
        else:
            print(f'Only {len(df_missing)} missing observations for {feat}. \nCannot perform hypothesis testing with too few examples. \n\n')

    return MCAR_results
