from dash import html, dcc

STRATEGIES = ["DualMAMomentum", "BollingerMeanReversion"]

def create_layout():
    sidebar = html.Div([
        html.H4("Settings"),
        html.Label("Ticker"),
        dcc.Input(id="ticker", value="AAPL", type="text"),

        html.Label("Start Date"),
        dcc.DatePickerSingle(id="start-date", date="2020-01-01"),

        html.Label("End Date"),
        dcc.DatePickerSingle(id="end-date", date="2023-12-31"),

        html.Label("Strategy"),
        dcc.Dropdown(id="strategy", options=STRATEGIES, value="DualMAMomentum"),

        html.Label("Fast Period"),
        dcc.Slider(id="fast-period", min=5, max=50, step=5, value=20,
                   marks={i: str(i) for i in range(5, 55, 10)}),

        html.Label("Slow Period"),
        dcc.Slider(id="slow-period", min=20, max=200, step=10, value=50,
                   marks={i: str(i) for i in range(20, 210, 40)}),

        html.Button("Run Backtest", id="run-btn", n_clicks=0),
        html.Div(id="status-msg"),
    ], style={"width": "20%", "padding": "20px", "float": "left"})

    main_panel = html.Div([
        dcc.Graph(id="price-chart"),
        dcc.Graph(id="equity-chart"),
        html.Div(id="metrics-table"),
    ], style={"width": "78%", "float": "right"})

    return html.Div([sidebar, main_panel])
