import pandas as pd
from bokeh.io.export import get_layout_html
from bokeh.plotting import figure, column
from bokeh.models import CustomJS, ColumnDataSource, HoverTool, DateRangeSlider, Span

from io import StringIO


def candlestick_plot(df, title, plot_type=1):
    df.columns = ['Date', 'High', 'Volume', 'Open', 'Low', 'Close', 'sa1_schedule', 'sd0_schedule', 'SA1']
    df = df[::-1]

    fig = figure(sizing_mode='stretch_both',
                 tools="xpan,xwheel_zoom,box_zoom,undo,redo,reset,crosshair,save,",
                 active_drag='xpan',
                 active_scroll='xwheel_zoom',
                 x_axis_type='datetime',
                 y_axis_location='right',
                 toolbar_location='left',
                 title=title)

    inc = df['Close'] > df['Open']
    dec = ~inc
    source = ColumnDataSource({'date': df['Date'], 'high': df['High'], 'low': df['Low'],
                                   'close': df['Close'],  'open': df['Open']})
    source_inc = ColumnDataSource({'date': df['Date'][inc], 'high': df['High'][inc], 'low': df['Low'][inc],
                                   'close': df['Close'][inc],  'open': df['Open'][inc], 'volume': df['Volume'][inc],
                                   'color': ['#008000' for i in range(len(df['Date'][inc]))]})
    source_dec = ColumnDataSource({'date': df['Date'][dec], 'high': df['High'][dec], 'low': df['Low'][dec],
                                   'close': df['Close'][dec],  'open': df['Open'][dec], 'volume': df['Volume'][dec],
                                   'color': ['#ff0000' for i in range(len(df['Date'][dec]))]})

    if df.shape[0] >= 365:
        slider = DateRangeSlider(title='Период', start=df['Date'][df.shape[0] - 1], end=df['Date'][0],
                                 value=(df['Date'][364], df['Date'][0]), step=1)
    else:
        slider = DateRangeSlider(title='Период', start=df['Date'][df.shape[0] - 1], end=df['Date'][0],
                                 value=(df['Date'][df.shape[0] - 1], df['Date'][0]), step=1)
    slider.js_link("value", fig.x_range, "start", attr_selector=0)
    slider.js_link("value", fig.x_range, "end", attr_selector=1)

    callback = CustomJS(args={'y_range': fig.y_range, 'source': source}, code='''
            clearTimeout(window._autoscale_timeout)

            let date = source.data.date,
                low = source.data.low,
                high = source.data.high,
                start = cb_obj.start,
                end = cb_obj.end,
                min = Infinity,
                max = -Infinity

            for (var i=0; i < date.length; ++i) {
                if (start <= date[i] && date[i] <= end) {
                    max = Math.max(high[i], max)
                    min = Math.min(low[i], min)
                }
            }
            let pad = (max - min) * .05

            window._autoscale_timeout = setTimeout(function() {
                y_range.start = min - pad
                y_range.end = max + pad
            })
        ''')

    fig.x_range.js_on_change('start', callback)

    hover_tool = HoverTool(tooltips="""
    <div>
        <div>
            <span style="font-size: 11px; font-weight: bold;">Open: </span>
            <span style="font-size: 11px; color: @color;">@open{0.00}</span>
        </div>
        <div>
            <span style="font-size: 11px; font-weight: bold;">High: </span>
            <span style="font-size: 11px; color: @color;">@high{0.00}</span>
        </div>
        <div>
            <span style="font-size: 11px; font-weight: bold;">Low: </span>
            <span style="font-size: 11px; color: @color;">@low{0.00}</span>
        </div>
        <div>
            <span style="font-size: 11px; font-weight: bold;">Close: </span>
            <span style="font-size: 11px; color: @color;">@close{0.00}</span>
        </div>
        <div>
            <span style="font-size: 11px; font-weight: bold;">Volume: </span>
            <span style="font-size: 11px; color: @color;">@volume{0.00 a}</span>
        </div>
    </div>
    """, mode='vline', names=['bar'])

    fig.add_tools(hover_tool)

    fig.segment(x0='date', y0='high', x1='date', y1='low', color="green", source=source_inc)
    fig.segment(x0='date', y0='high', x1='date', y1='low', color="red", source=source_dec)

    width = 12 * 60 * 60 * 1000
    fig.vbar(x='date', width=width, top='open', bottom='close', color="green", source=source_inc, name='bar')
    fig.vbar(x='date', width=width, top='open', bottom='close', color="red", source=source_dec, name='bar')

    ddf = pd.DataFrame()
    udf = pd.DataFrame()
    for index, row_ in df.iterrows():
        if row_['SA1'] == 'Up':
            index = udf.shape[0]
            udf.loc[index, 'close'] = row_['Close']
            udf.loc[index, 'date'] = row_['Date']
        elif row_['SA1'] == 'Down':
            index = ddf.shape[0]
            ddf.loc[index, 'close'] = row_['Close']
            ddf.loc[index, 'date'] = row_['Date']

    dsource = ColumnDataSource(data=dict(
        date=ddf['date'],
        close=ddf['close'],
    ))
    usource = ColumnDataSource(data=dict(
        date=udf['date'],
        close=udf['close'],
    ))

    fig.circle(x='date', y='close', size=9, line_color='cyan', fill_color='cyan', source=usource)
    fig.circle(x='date', y='close', size=9, line_color='purple', fill_color='purple', source=dsource)

    if plot_type == 2:
        for index, row in df.iterrows():
            if row['SA1'] == 'Up':
                fig.add_layout(Span(location=row['sa1_schedule'], dimension='width', line_color='cyan', line_width=1, line_alpha=0.5))
            elif row['SA1'] == 'Down':
                fig.add_layout(Span(location=row['sa1_schedule'], dimension='width', line_color='purple', line_width=1, line_alpha=0.5))

    return StringIO(get_layout_html(column(fig, slider, sizing_mode='scale_width')))
