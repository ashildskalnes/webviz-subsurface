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


def ssdl_connect():
    TENANT = os.environ.get("TENANT")
    RESOURCE = os.environ.get("SSDL_RESOURCE")
    CLIENT_ID = os.environ.get("WEBVIZ_4D_ID")
    SUBSCRIPTION_KEY = os.environ.get("SSDL_SUBSCRIPTION_KEY")
    AUTHORITY = "https://login.microsoftonline.com/" + TENANT
    SCOPE = RESOURCE + "/user_impersonation"
    cache_filename = os.path.join(home, "SSDL_token_cache.bin")

    result = msal_get_token(CLIENT_ID, AUTHORITY, SCOPE, cache_filename)

    if result is not None:
        expires_in = result["expires_in"]
        # print(f"SMDA token Expires in {int(expires_in)/60} min")

    session = requests.session()

    if "access_token" in result:
        print("Created a new SSDL session \n")
        session.headers.update(
            {
                "Authorization": "Bearer " + result["access_token"],
                "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY,
            }
        )
    else:
        print("Could not connect to SSDL, Error:", result.get("error"))
        print(result.get("error_description"), "\n")

    return session


def extract_ssdl_data(session, wellbores, well_folder, polygon_folder, settings_folder):
    print("Extracting data from SSDL ...")

    api = "https://api.gateway.equinor.com/subsurfacedata/v3/api/v3.0/"
    print("Extracting model data ...")

    # Extract Outline and faultline data
    extract_faultline_data(session, api, wellbores, polygon_folder, settings_folder)

    extract_outline_data(session, api, wellbores, polygon_folder, settings_folder)

    # Extract completions and perforations
    print("Extracting completions and perforations...")
    extract_completion_data(session, api, wellbores, well_folder, settings_folder)

    extract_perforation_data(session, api, wellbores, well_folder, settings_folder)

    return print("Done extracting SSDL data \n")


def extract_outline_data(session, api, wellbores, polygon_folder, settings_folder):

    print("Extracting outline data")
    wellbore_field_uuid = wellbores["field_uuid"].to_numpy(dtype=str)

    field_uuid_list = list(dict.fromkeys(wellbore_field_uuid))
    OWC_outline = []
    GOC_outline = []

    for field_uuid in field_uuid_list:
        print(field_uuid)
        endpoint = api + "Field/" + field_uuid + "/model"
        models_df = extract_data(session, endpoint)

        for column in models_df.columns:
            model_dict = models_df[column][0]

            if model_dict.get("default_flag"):
                model_uuid = model_dict.get("model_uuid")

                endpoint = api + "Field/%s/outlines/OWC" % model_uuid
                OWC_outline_df = extract_data(session, endpoint)

                endpoint = api + "Field/%s/outlines/GOC" % model_uuid
                GOC_outline_df = extract_data(session, endpoint)

                if not OWC_outline_df.empty:
                    OWC_outline.append(OWC_outline_df)

                if not GOC_outline_df.empty:
                    GOC_outline.append(GOC_outline_df)

    if len(OWC_outline) > 0:
        OWC = pd.concat(OWC_outline)
        OWC["name"] = "owc_outline"
        outfile = os.path.join(settings_folder, polygon_folder, "owc_outline" + ".csv")
        OWC.to_csv(outfile, index=False)
    else:
        print("OWC outline not found")

    if len(GOC_outline) > 0:
        GOC = pd.concat(GOC_outline)
        GOC["name"] = "goc_outline"
        outfile = os.path.join(settings_folder, polygon_folder, "goc_outline" + ".csv")
        GOC.to_csv(outfile, index=False)
    else:
        print("GOC outline not found")

    return print("Done extracting outline data")


def extract_faultline_data(session, api, wellbores, polygon_folder, settings_folder):

    print("Extracting faultline data")
    wellbore_field_uuid = wellbores["field_uuid"].to_numpy(dtype=str)

    field_uuid_list = list(dict.fromkeys(wellbore_field_uuid))

    faultlines = pd.DataFrame()
    seg_id = []
    geometry = []
    coordinates = []

    for field_uuid in field_uuid_list:
        print(field_uuid)
        endpoint = api + "Field/" + field_uuid + "/model"
        models_df = extract_data(session, endpoint)

        for column in models_df.columns:
            model_dict = models_df[column][0]

            if model_dict.get("default_flag"):
                model_uuid = model_dict.get("model_uuid")

                if model_dict.get("has_polygon"):
                    endpoint = api + "Field/%s/faultlines" % model_uuid

                    faults_df = extract_data(session, endpoint)

                    if not faults_df.empty:
                        faults_df_t = faults_df.T

                        for _index, row in faults_df_t.iterrows():
                            seg_id.append(row[0].get("SEG I.D."))
                            geometry.append(row[0].get("geometry"))
                            coordinates.append(row[0].get("coordinates"))
                else:
                    print("No fault polygons found")

    if coordinates:
        name = "faults"
        faultlines["SEG I.D."] = seg_id
        faultlines["geometry"] = geometry
        faultlines["coordinates"] = coordinates
        faultlines["name"] = name

        outfile = os.path.join(settings_folder, polygon_folder, name + ".csv")
        faultlines.to_csv(outfile, index=False)

    return print("Done extracting faultline data")


def extract_completion_data(session, api, wellbores, well_folder, settings_folder):
    # Extract completions and perforations
    print("Extracting completions")

    for _index, row in wellbores.iterrows():
        wellbore_uuid = row["uuid"]
        wellbore_name = row["unique_wellbore_identifier"]
        rms_name = wellbore_name.replace("NO ", "").replace("/", "_").replace(" ", "_")

        endpoint = api + "Wellbores/%s/completion" % wellbore_uuid

        df_completion = pd.DataFrame()
        response = session.get(endpoint)

        if response.status_code == 200:
            try:
                results = response.json()["data"]["results"]
                df_completion = pd.DataFrame(results)
            except:
                try:
                    results = [
                        response.json(),
                    ]
                    df_completion = pd.DataFrame(results)
                except:
                    results = pd.DataFrame()
                    print("WARNING: No valid data extracted:")
                    print("         endpoint:", endpoint)
        elif response.status_code == 404:
            pass
            # print(f"Completion data for {well_data} either does not exist or can not be found \n")
        else:
            print(
                "[WARNING:] Can not fetch data for endpoint {endpoint} ("
                + str(response.status_code)
                + ")"
            )

        if df_completion is not None and not df_completion.empty:
            completion_t = df_completion.T[0]
            completion = pd.DataFrame(completion_t.to_list())

            file_name = rms_name + "_completion.csv"
            outfile = os.path.join(settings_folder, well_folder, file_name)
            completion.to_csv(outfile, index=False)

    print(f"Completions stored to {well_folder}")


def extract_perforation_data(session, api, wellbores, well_folder, settings_folder):
    # Extract perforations
    print("Extracting perforations data")

    for _index, row in wellbores.iterrows():
        wellbore_uuid = row["uuid"]
        wellbore_name = row["unique_wellbore_identifier"]
        rms_name = wellbore_name.replace("NO ", "").replace("/", "_").replace(" ", "_")

        endpoint = api + "Wellbores/%s/perforations" % wellbore_uuid

        df_perforation = pd.DataFrame()
        response = session.get(endpoint)

        if response.status_code == 200:
            try:
                results = response.json()["data"]["results"]
                df_perforation = pd.DataFrame(results)
            except:
                try:
                    results = [
                        response.json(),
                    ]
                    df_perforation = pd.DataFrame(results)
                except:
                    results = pd.DataFrame()
                    print("WARNING: No valid data extracted:")
                    print("         endpoint:", endpoint)
        elif response.status_code == 404:
            pass
            # print(
            # f"perforation data for well {well_data} either does not exist or can not be found \n")
        else:
            print(
                "[WARNING:] Can not fetch data for endpoint {endpoint} ("
                + str(response.status_code)
                + ")"
            )

        if df_perforation is not None and not df_perforation.empty:
            perforation_t = df_perforation.T[0]
            perforation = pd.DataFrame(perforation_t.to_list())

            file_name = rms_name + "_perforation.csv"
            outfile = os.path.join(settings_folder, well_folder, file_name)
            perforation.to_csv(outfile, index=False)

    print(f"Perforations stored to {well_folder}")


def extract_data(session, endpoint):
    extracted_df = pd.DataFrame()
    response = session.get(endpoint)

    if response.status_code == 200:
        try:
            results = response.json()["data"]["results"]
            extracted_df = pd.DataFrame(results)
        except:
            try:
                results = [
                    response.json(),
                ]
                extracted_df = pd.DataFrame(results)
            except:
                results = pd.DataFrame()
                print("WARNING: No valid data extracted:")
                print("         endpoint:", endpoint)
    elif response.status_code == 404:
        print(
            f"{str(response.status_code) } {endpoint} either does not exists or can not be found"
        )
    else:
        print(
            f"[WARNING:] Can not fetch data from endpont {endpoint}  ({ str(response.status_code)})-{response.reason} "
        )

    return extracted_df
