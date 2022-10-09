# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (C) 2020 - Equinor ASA.

import re
import json
from pathlib import Path

from dash import Dash, callback, Input, Output, html

import webviz_core_components as wcc
import webviz_subsurface_components

import pandas as pd


class DepositionalEnvironmentSMDAStandard:
    def __init__(self, depenv_color_standard: pd.DataFrame) -> None:
        self._df = depenv_color_standard

    def get_dep_environment_for_smda_code(self, smda_code: int) -> str:
        return self._df[self._df["SMDA code"] == smda_code][
            "DEPOSITIONAL ENVIRONMENT"
        ].values[0]

    def get_smda_code_for_dep_environment(self, dep_env: str) -> int:
        print(dep_env)
        return self._df[
            self._df["DEPOSITIONAL ENVIRONMENT"].str.contains(
                dep_env, flags=re.IGNORECASE
            )
        ]["SMDA code"].values[0]

    def get_webviz_well_log_metadata(self) -> dict:
        return {
            "DepositionalEnvironment": {
                "attributes": ["color", "code"],
                "objects": {
                    row["DEPOSITIONAL ENVIRONMENT"]: [
                        [row["R"], row["G"], row["B"], 255],
                        row["SMDA code"],
                    ]
                    for _, row in self._df.iterrows()
                },
            }
        }


class DepositionalEnvironmentsWebviz:
    def __init__(
        self,
        lithostrat: pd.DataFrame,
        dep_environments: DepositionalEnvironmentSMDAStandard,
    ) -> None:
        self._df = lithostrat
        self.dep_environments = dep_environments

    def wells(self) -> list:
        return self._df["unique_wellbore_identifier"].unique().tolist()

    def _get_log_curves(self) -> list:
        return [
            {
                "name": "MD",
                "description": "continuous",
                "quantity": "m",
                "unit": "m",
                "valueType": "float",
                "dimensions": 1,
            },
            {
                "name": "DepositionalEnvironment",
                "description": "discrete",
                "quantity": "DISC",
                "unit": "DISC",
                "valueType": "integer",
                "dimensions": 1,
            },
        ]

    def _get_log_header(self, well_name) -> dict:
        df = self._df[self._df["unique_wellbore_identifier"] == well_name]
        return {
            "name": "BLOCKING",
            "well": well_name,
            "startIndex": df["Depth_top"].min(),
            "endIndex": df["Depth_base"].max(),
            "step": None,
        }

    def _get_log_data(self, well_name) -> list:
        df = self._df[self._df["unique_wellbore_identifier"] == well_name]
        data = []

        for _, row in df.iterrows():
            data.append(
                [
                    row["Depth_top"],
                    # row["Lithostrat_unit"],
                    self.dep_environments.get_smda_code_for_dep_environment(
                        row["Depositional Environment"]
                    )
                    if isinstance(row["Depositional Environment"], str)
                    else None,
                ]
            )
        return data

    def _get_log_metadata_discrete(self) -> dict:
        return self.dep_environments.get_webviz_well_log_metadata()

    def get_webviz_well_log(self, well_name) -> dict:
        return {
            "header": self._get_log_header(well_name),
            "curves": self._get_log_curves(),
            "data": self._get_log_data(well_name),
            "metadata_discrete": self._get_log_metadata_discrete(),
        }

    def _get_pick_header(self, well_name) -> dict:
        return {"name": well_name, "well": well_name}

    def _get_pick_curves(self) -> list:
        return [
            {
                "name": "MD",
                "quantity": "m",
                "unit": "m",
                "valueType": "float",
                "dimensions": 1,
            },
            {
                "name": "HORIZON",
                "valueType": "string",
                "dimensions": 1,
            },
        ]

    def _get_pick_data(self, well_name) -> list:
        df = self._df[self._df["unique_wellbore_identifier"] == well_name]
        data = []

        for _, row in df.iterrows():
            data.append([row["Depth_top"], row["Lithostrat_unit"]])
        return data

    def get_webviz_well_picks(self, well_name) -> dict:
        return {
            "header": self._get_pick_header(well_name),
            "curves": self._get_pick_curves(),
            "data": self._get_pick_data(well_name),
        }


dep_env_color_df = pd.read_csv("./data/DEPENV_colour_standard.csv")
lithstrat = pd.read_csv("./data/lithstr_and_depenv_cleaned.csv")
COLORTABLES = json.loads(Path("./color-tables.json").read_text())


dep = DepositionalEnvironmentSMDAStandard(dep_env_color_df)
lith = DepositionalEnvironmentsWebviz(lithstrat, dep)


app = Dash(__name__)

app.layout = html.Div(
    style={"display": "flex", "height": "95vh"},
    children=[
        html.Div(
            style={"flex": 1},
            children=[
                wcc.Select(
                    id="well",
                    options=[{"label": well, "value": well} for well in lith.wells()],
                    value=[lith.wells()[0]],
                    size=60,
                )
            ],
        ),
        html.Div(
            style={"flex": 5},
            children=webviz_subsurface_components.WellLogViewer(
                id="well-logs",
                welllog=lith.get_webviz_well_log(lith.wells()[0]),
                wellpick={"wellpick": lith.get_webviz_well_picks(lith.wells()[0])},
                template={
                    "name": "Template",
                    "scale": {"primary": "MD"},
                    "tracks": [
                        {
                            "plots": [
                                {"name": "DepositionalEnvironment", "type": "stacked"}
                            ]
                        },
                    ],
                },
                colorTables=COLORTABLES,
            ),
        ),
    ],
)


@callback(
    Output("well-logs", "welllog"),
    Output("well-logs", "wellpick"),
    Input("well", "value"),
)
def _set_well(well_names: str) -> dict:
    return (
        lith.get_webviz_well_log(well_names[0]),
        {
            "wellpick": lith.get_webviz_well_picks(lith.wells()[0]),
            "name": "HORIZON",
            "color": "Stratigraphy",
            "colorTables": [
                {
                    "name": "Physics",
                    "discrete": False,
                    "description": "Full options color table",
                    "colorNaN": [255, 255, 255],
                    "colorBelow": [255, 0, 0],
                    "colorAbove": [0, 0, 255],
                    "colors": [
                        [0, 255, 0, 0],
                        [0.25, 182, 182, 0],
                        [0.5, 0, 255, 0],
                        [0.75, 0, 182, 182],
                        [1, 0, 0, 255],
                    ],
                },
                {
                    "name": "Physics reverse",
                    "discrete": False,
                    "colors": [
                        [0, 0, 0, 255],
                        [0.25, 0, 182, 182],
                        [0.5, 0, 255, 0],
                        [0.75, 182, 182, 0],
                        [1, 255, 0, 0],
                    ],
                },
                {
                    "name": "Rainbow",
                    "discrete": False,
                    "colors": [
                        [0, 255, 0, 0],
                        [0.2, 182, 182, 0],
                        [0.4, 0, 255, 0],
                        [0.6, 0, 182, 182],
                        [0.8, 0, 0, 255],
                        [1, 182, 0, 182],
                    ],
                },
                {
                    "name": "Rainbow reverse",
                    "discrete": False,
                    "colors": [
                        [0, 182, 0, 182],
                        [0.2, 0, 0, 255],
                        [0.4, 0, 182, 182],
                        [0.6, 0, 255, 0],
                        [0.8, 182, 182, 0],
                        [1, 255, 0, 0],
                    ],
                },
                {
                    "name": "Colors_set_1",
                    "discrete": "true",
                    "colors": [
                        [0, 255, 13, 186],
                        [1, 255, 64, 53],
                        [2, 247, 255, 164],
                        [3, 112, 255, 97],
                        [4, 9, 254, 133],
                        [5, 254, 4, 135],
                        [6, 255, 5, 94],
                        [7, 32, 50, 255],
                        [8, 109, 255, 32],
                        [9, 254, 146, 92],
                        [10, 185, 116, 255],
                        [11, 255, 144, 1],
                        [12, 157, 32, 255],
                        [13, 255, 26, 202],
                        [14, 73, 255, 35],
                    ],
                },
                {
                    "name": "Stratigraphy",
                    "discrete": True,
                    "colorNaN": [255, 64, 64],
                    "colors": [
                        [0, 255, 193, 0],
                        [1, 255, 120, 61],
                        [2, 255, 155, 76],
                        [3, 255, 223, 161],
                        [4, 226, 44, 118],
                        [5, 255, 243, 53],
                        [6, 255, 212, 179],
                        [7, 255, 155, 23],
                        [8, 255, 246, 117],
                        [9, 255, 241, 0],
                        [10, 255, 211, 178],
                        [11, 255, 173, 128],
                        [12, 248, 152, 0],
                        [13, 154, 89, 24],
                        [14, 0, 138, 185],
                        [15, 82, 161, 40],
                        [16, 219, 228, 163],
                        [17, 0, 119, 64],
                        [18, 0, 110, 172],
                        [19, 116, 190, 230],
                        [20, 0, 155, 212],
                        [21, 0, 117, 190],
                        [22, 143, 40, 112],
                        [23, 220, 153, 190],
                        [24, 226, 44, 118],
                        [25, 126, 40, 111],
                        [26, 73, 69, 43],
                        [27, 203, 63, 42],
                        [28, 255, 198, 190],
                        [29, 135, 49, 45],
                        [30, 150, 136, 120],
                        [31, 198, 182, 175],
                        [32, 166, 154, 145],
                        [33, 191, 88, 22],
                        [34, 255, 212, 179],
                        [35, 251, 139, 105],
                        [36, 154, 89, 24],
                        [37, 186, 222, 200],
                        [38, 0, 124, 140],
                        [39, 87, 84, 83],
                    ],
                },
                {
                    "name": "Colors_set_3",
                    "discrete": "true",
                    "colors": [
                        [0, 120, 181, 255],
                        [1, 255, 29, 102],
                        [2, 247, 255, 173],
                        [3, 239, 157, 255],
                        [4, 186, 255, 236],
                        [5, 46, 255, 121],
                        [6, 212, 255, 144],
                        [7, 165, 255, 143],
                        [8, 122, 255, 89],
                        [9, 255, 212, 213],
                    ],
                },
                {
                    "name": "Porosity",
                    "discrete": False,
                    "colors": [
                        [0, 255, 246, 117],
                        [0.11, 255, 243, 53],
                        [0.18, 255, 241, 0],
                        [0.25, 155, 193, 0],
                        [0.32, 255, 155, 23],
                        [0.39, 255, 162, 61],
                        [0.46, 255, 126, 45],
                        [0.53, 227, 112, 24],
                        [0.6, 246, 96, 31],
                        [0.67, 229, 39, 48],
                        [0.74, 252, 177, 170],
                        [0.81, 236, 103, 146],
                        [0.88, 226, 44, 118],
                        [1, 126, 40, 111],
                    ],
                },
            ],
        },
    )


if __name__ == "__main__":
    app.run_server(debug=True)
