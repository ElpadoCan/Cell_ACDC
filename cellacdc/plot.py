import typing

import pandas as pd
import numpy as np
import scipy.stats

import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns


def _binned_mean_stats(x, y, bins, bins_min_count):
    bin_counts, _, _ = scipy.stats.binned_statistic(x, y, statistic='count', bins=bins)
    bin_means, bin_edges, _ = scipy.stats.binned_statistic(x, y, bins=bins)
    bin_std, _, _ = scipy.stats.binned_statistic(x, y, statistic='std', bins=bins)
    bin_width = (bin_edges[1] - bin_edges[0])
    bin_centers = bin_edges[1:] - bin_width/2
    if bins_min_count > 1:
        bin_centers = bin_centers[bin_counts > bins_min_count]
        bin_means = bin_means[bin_counts > bins_min_count]
        bin_std = bin_std[bin_counts > bins_min_count]
        bin_counts = bin_counts[bin_counts > bins_min_count]
    std_err = bin_std/np.sqrt(bin_counts)
    return bin_centers, bin_means, bin_std, std_err

def binned_means_plot(
        x: typing.Union[str, typing.Iterable] = None, 
        y: typing.Union[str, typing.Iterable] = None, 
        bins: typing.Union[int, typing.Iterable] = 10, 
        bins_min_count: int = 1,
        data: pd.DataFrame = None,
        scatter: bool = True,
        use_std_err: bool = True,
        color = None,
        label = None,
        scatter_kws = None,
        errorbar_kws = None,
        ax: matplotlib.axes.Axes = None,
        scatter_colors = None
    ):
    if ax is None:
        fig, ax = plt.subplots(1)

    if isinstance(x, str):
        if data is None:
            raise TypeError(
                "Passing strings to 'x' and 'y' also requires the 'data' "
                "variable as a pandas DataFrame"
            )
        ax.set_xlabel(x)
        ax.set_ylabel(y)
        x = data[x]
        y = data[y]

    if color is None:
        color = sns.color_palette(n_colors=1)[0]
    
    if scatter_kws is None:
        scatter_kws = {'alpha': 0.3}
    
    if 'alpha' not in scatter_kws:
        scatter_kws['alpha'] = 0.3
    
    if errorbar_kws is None:
        errorbar_kws = {'capsize': 3, 'lw': 2}
    
    if label is None:
        label = ''
    
    if scatter_colors is None:
        scatter_colors = color
    
    xe, ye, std, std_err = _binned_mean_stats(x, y, bins, bins_min_count)
    if scatter:
        ax.scatter(x, y, color=scatter_colors, **scatter_kws)
    yerr = std_err if use_std_err else std
    ax.errorbar(xe, ye, yerr=yerr, color=color, label=label, **errorbar_kws)

    return ax

if __name__ == '__main__':
    x = np.arange(0, 1000).astype(float)
    y = 2*x+10
    noise = np.random.normal(0, 100, size=1000)
    y += noise

    data = pd.DataFrame({'x': x, 'y': y})

    nbins = 10
    bins_min_count = 10

    binned_means_plot(
        x='x', y='y', data=data, nbins=nbins, bins_min_count=bins_min_count
    )
    
    plt.show()