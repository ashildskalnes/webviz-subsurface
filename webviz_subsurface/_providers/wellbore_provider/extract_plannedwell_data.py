import argparse
import datetime
import glob
import numpy as np
import json
from dotenv import load_dotenv
from shutil import copyfile
import webviz_4d_input.common as common
import os
import sys
import requests
import pandas as pd
from MSALAuthorization import msal_get_token

home = os.path.expanduser("~")
env_path = os.path.expanduser(os.path.join(home, ".omniaapi"))
load_dotenv(dotenv_path=env_path)


def plannedWell_connect():
    print("Connect to planned wells api")
    TENANT = os.environ.get("TENANT")
    RESOURCE = "c3781abc-b5a1-4189-9875-4ed92e5297aa"
    CLIENT_ID = os.environ.get("WEBVIZ_4D_ID")
    SUBSCRIPTION_KEY = os.environ.get("_SUBSCRIPTION_KEY")
    AUTHORITY = "https://login.microsoftonline.com/" + TENANT
    SCOPE = RESOURCE + "/user_impersonation"
    cache_filename = os.path.join(home, "PlannedWell_token_cache.bin")

    result = msal_get_token(CLIENT_ID, AUTHORITY, SCOPE, cache_filename)

    if result is not None:
        expires_in = result["expires_in"]
        # print(f"PlannedWell token Expires in {int(expires_in)/60} min")

    session = requests.session()

    if "access_token" in result:
        print("Create a new PlannedWell session \n")
        session.headers.update(
            {
                "Authorization": "Bearer " + result["access_token"],
            }
        )
    else:
        print("Could not connect to PlannedWell API, Error:", result.get("error"))
        print(result.get("error_description"), "\n")

    return session


def extract_plannedWell_data(session, well_folder, fields):

    # Create Planned_wells folder if not existing, delete all existing trajectory files if existing
    planned_wells_dir = os.path.join(well_folder, "Planned_wells")
    if os.path.isdir(planned_wells_dir):
        for f in os.listdir(planned_wells_dir):
            os.remove(os.path.join(planned_wells_dir, f))
    else:
        os.mkdir(planned_wells_dir)

    # Extract data from endpoint
    api = "https://wfmwellapiprod.azurewebsites.net/"
    phase = "1"
    endpoint = api + "api/v3/RepWellDesign?FieldId=" + "" + "&phase=" + phase
    plannedwells_df = extract_data(session, endpoint)

    planned_well_data = []
    for field in fields:
        if not plannedwells_df.empty:
            # Replace any underscore in field name with space and compare with wanted field in uppercase
            plannedwells_df["fieldName"] = plannedwells_df["fieldName"].str.replace(
                "_", " "
            )
            plannedwells_df["fieldName"] = plannedwells_df["fieldName"].str.upper()
            selected_wells_df = plannedwells_df.loc[
                plannedwells_df["fieldName"] == field
            ]

            if not selected_wells_df.empty:

                planned_well_data.append(
                    selected_wells_df[
                        ["name", "templateName", "fieldName", "wellTypeName"]
                    ]
                )
                print("Extract well position")
                extract_plannedWell_position(selected_wells_df, planned_wells_dir)
            else:
                print(f"No planned wells found for {field} ")

    if len(planned_well_data) > 0:
        finaldf = pd.concat(planned_well_data)
        planned_wells_file = "planned_wells_overview.csv"
        outfile = os.path.join(well_folder, planned_wells_file)
        finaldf.to_csv(outfile, index=False)
        print(f" Planned wells overview saved as {planned_wells_file}")
    else:
        print("No planned wells found")

    return print(f"Done extracting planned well data \n")


def extract_data(session, endpoint):
    response = session.get(endpoint, verify=False)

    plannedwells_df = pd.DataFrame()

    if response.status_code == 200:
        results = response.json()
        plannedwells_df = pd.DataFrame(results)
    else:
        print(
            f"Exception: connecting to {endpoint} {response.status_code} {response.reason}"
        )
    return plannedwells_df


def extract_plannedWell_position(selected_wells_df, planned_wells_dir):
    selected_planned_wells = []
    for _i, planned_well in selected_wells_df.iterrows():
        well_name = planned_well["name"]
        selected_planned_wells.append(planned_well)
        well_points_file = well_name + "_trajectory" + ".csv"
        well_trajectory_file = well_points_file.replace(" ", "_")
        well_trajectory_file = well_trajectory_file.replace("/", "_")
        well_points = planned_well["wellPoints"]
        well_points = pd.DataFrame(well_points)

        if not well_points.empty:
            md = well_points["measuredDepth"].to_numpy()

            position = pd.json_normalize(well_points[["position"][0]])

            df = pd.DataFrame()
            df["EASTING"] = position["x"].to_numpy()
            df["NORTHING"] = position["y"].to_numpy()
            df["TVDMSL"] = -position["z"].to_numpy()
            df["MD"] = md

            outfile = os.path.join(planned_wells_dir, well_trajectory_file)
            df.to_csv(outfile, index=False)
            print(f"Planned well trajectory file to {outfile}")
        else:
            print(f"Planned well {well_name} does not contain well points")
    return print("Done extracting planned well points")
