import natsort
import pandas as pd
import seaborn as sns
from scipy import stats

# quick script, if __name__ == '__main__' stuff is not needed

# Not sure if I love a ton of pandas manipulations in production code (code is brittle, hard to read, &c.)
# but for a quick first pass it's ideal.
# read in the cell count data, and grab the numeric count columns
cell_df = pd.read_csv('/dev/stdin').set_index('sample')
counts = cell_df[cell_df.columns[-5:]]
total = counts.sum(axis=1).rename('total_count')
percent = (counts.div(total, axis=0) * 100).round(2)

# melt to long format. I like the multi-indexes here because it helps catch mistakes
# that would go unnoticed otherwise at the concat step.
long_percent = percent.melt(ignore_index=False, var_name='population', value_name='percentage')
long_percent = long_percent.reset_index().set_index(['sample', 'population'])
long_count = counts.melt(ignore_index=False, var_name='population', value_name='count')
long_count = long_count.reset_index().set_index(['sample', 'population'])

# put together the requested output, merging in the total count (which gets repeated)
out = pd.concat([long_count, long_percent], axis=1).merge(total, left_index=True, right_index=True)
# use natsort so that the sample IDs go `s1`, `s2`, `s3`, &c. instead of `s1`, `s10`, `s11`...
out = out.reset_index().sort_values(['sample', 'population'], key=natsort.natsort_key)
out[['sample', 'total_count', 'population', 'count', 'percentage']].to_csv('cell-count-percentage.csv', index=False)

# now get the data for the boxplots
response = cell_df.query('condition == "melanoma" and treatment == "tr1" and sample_type == "PBMC"').response
response_percent = long_percent.merge(response, left_index=True, right_index=True, how='inner').sort_index().reset_index()

# make a boxplot with the data points overlaid
g = sns.catplot(data=response_percent, x='response', hue='response', y='percentage', col='population', kind='box', boxprops=dict(alpha=.3))
g.set_titles('{col_name}')
g.map(sns.stripplot, 'response', 'percentage', color='black', order=['y', 'n'], size=5)
g.savefig('cell-count-response.png', dpi=200)

# apply some statistics to the y vs n response groups
def yn_test(group):
    y = group.query('response == "y"').percentage
    n = group.query('response == "n"').percentage

    # Welch's t-test for the difference between means
    _t, p = stats.ttest_ind(y, n, equal_var=False)

    # now CIs for the means 
    ybar = y.mean()
    nbar = n.mean()
    yse = stats.sem(y)
    nse = stats.sem(n)
    y_ci_low, y_ci_high = stats.t.interval(0.95, len(y) - 1, loc=ybar, scale=yse)
    n_ci_low, n_ci_high = stats.t.interval(0.95, len(n) - 1, loc=nbar, scale=nse)
    y_ci_formatted = f'{y_ci_low:.1f}, {y_ci_high:.1f}'
    n_ci_formatted = f'{n_ci_low:.1f}, {n_ci_high:.1f}'
    
    # now CI for the difference between means
    se_of_diff = ((yse**2) + (nse**2))**0.5
    mean_diff = ybar - nbar
    mean_diff_ci_low, mean_diff_ci_high = stats.t.interval(0.95, len(y) + len(n) - 2, loc=mean_diff, scale=se_of_diff)
    mean_diff_ci_formatted = f'{mean_diff_ci_low:.1f}, {mean_diff_ci_high:.1f}'

    return pd.Series(dict(p=round(p, 3), 
                          y_n=len(y), 
                          y_mean=round(ybar, 1), 
                          y_ci=y_ci_formatted, 
                          n_n=len(n),
                          n_mean=round(nbar, 1),
                          n_ci=n_ci_formatted,
                          mean_diff=round(mean_diff, 1), 
                          mean_diff_ci=mean_diff_ci_formatted))

# and print the results
with pd.option_context('display.width', 150, 'display.max_columns', None):
    print(response_percent.groupby('population').apply(yn_test, include_groups=False))
