# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (C) 2020 - Equinor ASA.

import json
from pathlib import Path

import dash
import dash_html_components as html

import webviz_subsurface_components

COLORTABLES = json.loads(Path("./color-tables.json").read_text())
LOGS = json.loads(Path("./volve_logs.json").read_text())[0]
TEMPLATE = json.loads(Path("./welllog_template_2.json").read_text())

app = dash.Dash(__name__)

app.layout = html.Div(
    style={"height": "800px"},
    children=[
        webviz_subsurface_components.WellLogViewer(
            id="well-logs",
            welllog=LOGS,
            template=TEMPLATE,
            colorTables=COLORTABLES,
        ),
    ],
)
print(json.dumps(LOGS, indent=4))

if __name__ == "__main__":
    app.run_server(debug=True)
