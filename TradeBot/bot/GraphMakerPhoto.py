import pandas as pd
import mplfinance as mpf
import io


def make_graph(data, upside, buy):
    """Строим график"""
    data.columns = ['Date', 'High', 'Volume', 'Open', 'Low', 'Close', 'sa1_schedule', 'sd0_schedule', 'SA1']
    data.set_index('Date', inplace=True)

    data = data[::-1]
    sdata = pd.DataFrame(index=data.index)

    for index, row in data.iterrows():
        if row['SA1'] == 'Up':
            sdata.loc[index, 'up'] = row['Close']
        elif row['SA1'] == 'Down':
            sdata.loc[index, 'down'] = row['Close']

    plots = []
    try:
        sdp = mpf.make_addplot(sdata[['up']], type='scatter', color='cyan', markersize=25)
        plots.append(sdp)
    except KeyError:
        pass

    try:
        sdp = mpf.make_addplot(sdata[['down']], type='scatter', color='purple', markersize=25)
        plots.append(sdp)
    except KeyError:
        pass

    hlines = []
    colors = []
    if upside:
        hlines.append(upside)
        colors.append('r')
    if buy:
        hlines.append(buy)
        colors.append('b')

    graph = io.BytesIO()
    mpf.plot(data, type='candle', style='charles', addplot=plots, savefig=graph, hlines=dict(hlines=hlines,
                                                                                             colors=colors))
    graph.seek(0)
    return graph

