import dash
from .layout import create_layout
from . import callbacks  # importing registers the callbacks

app = dash.Dash(__name__, title="Quant Trading Framework")
app.layout = create_layout()

def main():
    app.run(debug=True, port=8050)
