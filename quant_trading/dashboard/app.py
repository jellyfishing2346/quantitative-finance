import os
import dash
from .layout import create_layout
from . import callbacks  # importing registers the callbacks

app = dash.Dash(__name__, title="Quant Trading Framework")
app.layout = create_layout()

def main():
    port = int(os.environ.get("PORT", 8050))
    debug = os.environ.get("RENDER") is None  # False in production, True locally
    app.run(host="0.0.0.0", port=port, debug=debug)
