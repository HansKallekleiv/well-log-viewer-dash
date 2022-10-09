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

    def _lithostrat_codes(self) -> dict:
        return {
            label: code
            for code, label in enumerate(self._df["Lithostrat_unit"].unique())
        }

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
                "description": "",
                "quantity": "DISC",
                "unit": "DISC",
                "valueType": "integer",
                "dimensions": 1,
            },
            {
                "name": "Lithostrat_unit",
                "description": "",
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
                    self._lithostrat_codes()[row["Lithostrat_unit"]],
                ]
            )
        return data

    def _get_log_metadata_discrete(self) -> dict:
        metadata = {
            "Lithostrat_unit": {
                "attributes": ["color", "code"],
                "objects": {
                    label: [[0, 0, 0, 255], code]
                    for label, code in self._lithostrat_codes().items()
                },
            }
        }
        metadata.update(self.dep_environments.get_webviz_well_log_metadata())
        return metadata

    def get_webviz_well_log(self, well_name) -> dict:
        return {
            "header": self._get_log_header(well_name),
            "curves": self._get_log_curves(),
            "data": self._get_log_data(well_name),
            "metadata_discrete": self._get_log_metadata_discrete(),
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
            children=webviz_subsurface_components.SyncLogViewer(
                id="well-logs",
                welllogs=[
                    {
                        "header": {
                            "name": "BLOCKING",
                            "well": "NO 1/6-7 T2",
                            "startIndex": 3069.0,
                            "endIndex": 4879.0,
                            "step": None,
                        },
                        "curves": [
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
                        ],
                        "data": [[3069.0, 3100]],
                    }
                    for _ in lith.wells()[0:50]
                ],
                templates=[
                    {
                        "name": "Template",
                        "scale": {"primary": "MD"},
                        "tracks": [
                            {
                                "plots": [
                                    {
                                        "name": "DepositionalEnvironment",
                                        "type": "stacked",
                                    }
                                ]
                            },
                            {
                                "plots": [
                                    {
                                        "name": "Lithostrat_unit",
                                        "type": "stacked",
                                        "colorTable": "Stratigraphy",
                                    }
                                ]
                            },
                        ],
                    },
                ],
                readoutOptions={"allTracks": False, "grouping": ""},
                colorTables=COLORTABLES,
            ),
        ),
    ],
)


@callback(
    Output("well-logs", "welllogs"),
    Output("well-logs", "templates"),
    Output("well-logs", "spacers"),
    Output("well-logs", "wellDistances"),
    Input("well", "value"),
)
def _set_well(well_names: str) -> dict:
    print(well_names)
    logs = [lith.get_webviz_well_log(well_name) for well_name in well_names]
    templates = [
        {
            "name": "Template",
            "scale": {"primary": "MD"},
            "tracks": [
                {
                    "plots": [
                        {
                            "name": "DepositionalEnvironment",
                            "type": "stacked",
                        }
                    ]
                },
                {
                    "plots": [
                        {
                            "name": "Lithostrat_unit",
                            "type": "stacked",
                            "colorTable": "Stratigraphy",
                        }
                    ]
                },
            ],
        }
        for _ in well_names
    ]
    spacers = [200 for _ in well_names]
    return logs, templates, spacers, spacers


if __name__ == "__main__":
    app.run_server(debug=True)
