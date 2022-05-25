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


def pdm_connect():
    TENANT = os.environ.get("TENANT")
    RESOURCE = os.environ.get("PDM_RESOURCE")
    CLIENT_ID = os.environ.get("WEBVIZ_4D_ID")
    SUBSCRIPTION_KEY = os.environ.get("PDM_SUBSCRIPTION_KEY")
    AUTHORITY = "https://login.microsoftonline.com/" + TENANT
    SCOPE = RESOURCE + "/user_impersonation"
    cache_filename = os.path.join(home, "PDM_token_cache.bin")

    result = msal_get_token(CLIENT_ID, AUTHORITY, SCOPE, cache_filename)

    if result is not None:
        expires_in = result["expires_in"]
        # print(f"SMDA token Expires in {int(expires_in)/60} min")

    session = requests.session()

    if "access_token" in result:
        print("Created a new PDM session \n")
        session.headers.update(
            {
                "Authorization": "Bearer " + result["access_token"],
                "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY,
            }
        )
    else:
        print("Could not connect to PDM, Error:", result.get("error"))
        print(result.get("error_description"), "\n")

    return session


def extract_pdm_data(session, field, production_folder, settings_folder):
    api = "https://api.gateway.equinor.com/pdm-internal-api/v3/api"
    print("Extracting production/injection wellbores from PDM ... ")

    print("Get PDM wells")
    selected_wellbores = set_selected_wellbores(session, api, field)

    if len(selected_wellbores) > 0:
        print("Extracting production volumes ... ")
        prod_status = extract_production_volume(
            session, api, selected_wellbores, production_folder
        )

        print("Extracting injection volumes ...")
        inj_status = extract_injection_volume(
            session, api, selected_wellbores, production_folder
        )

        print("Updating production data")
        update_production_data(
            prod_status, inj_status, production_folder, settings_folder
        )
    else:
        print("WARNING: No production/injection wells found")

    return print("Done extracting data from PDM \n")


def update_production_data(prod_status, inj_status, production_folder, settings_folder):
    daily_filenames = {
        "prod": "daily_production_volumes.csv",
        "inj": "daily_injection_volumes.csv",
    }

    frames = []
    now = datetime.datetime.now()
    now_txt = now.strftime("%Y-%m-%d %H:%M:%S")[:10]
    start_date = "1900-01-01"
    last_date = now_txt

    if prod_status and inj_status:
        for key, value in daily_filenames.items():
            well_prod_files = glob.glob(
                os.path.join(production_folder, "tmp", key + "*.csv")
            )

            frames = []
            for well_prod_file in well_prod_files:
                well_prod_data = pd.read_csv(well_prod_file)
                frames.append(well_prod_data)
                os.remove(well_prod_file)

            df_all = pd.concat(frames)
            df_all.sort_values(["WB_UWBI", "PROD_DAY"], inplace=True)
            file_name = value
            outfile = os.path.join(settings_folder, production_folder, file_name)
            df_all.to_csv(outfile, index=False)
            print(key + " data stored in file " + outfile)

            min_date = df_all["PROD_DAY"].min()
            start_date = max(start_date, min_date)[0:10]

            max_date = df_all["PROD_DAY"].max()
            last_date = min(last_date, max_date)[0:10]

        os.rmdir(os.path.join(production_folder, "tmp"))

        outfile = os.path.join(
            settings_folder, production_folder, ".production_update.yaml"
        )
        file_object = open(outfile, "w")
        file_object.write("- production:\n")
        file_object.write("   start_date: " + start_date + "\n")
        file_object.write("   last_date: " + last_date + "\n")
        file_object.write("   update_time: " + now_txt + "\n")
        file_object.close()

        print("Update date saved to file", outfile)

    print("Done updating production data")


def set_selected_wellbores(session, api, fields):

    selected_wellbores = []
    for field in fields:
        endpoint = api + "/WellBoreMaster?GOV_FIELD_NAME=" + field
        response = session.get(endpoint)

        if response.status_code != 200:
            print(f"{str(response.status_code) } {endpoint}")
            print("ERROR: Execution aborted")
            print("  - No production data loaded, re-start is needed")
            exit()

        results = response.json()
        wellbores = pd.json_normalize(results)
        if not wellbores.empty:
            selected_wellbores.extend(wellbores["WB_UWBI"].tolist())

    print("Production/injection wellbores:", len(selected_wellbores))

    return selected_wellbores


def extract_injection_volume(session, api, selected_wellbores, production_folder):
    inj_status = False
    i = 0
    for j in range(0, len(selected_wellbores)):
        wb_name = selected_wellbores[j]
        rms_name = wb_name.replace("/", "_").replace(" ", "_")
        well_prod_file = os.path.join(
            production_folder, "tmp", "inj_" + rms_name + ".csv"
        )

        if not os.path.isfile(well_prod_file):
            endpoint = api + "/WellBoreInjDay?top=20000&" + "WB_UWBI=" + wb_name
            response = session.get(endpoint)

            if response.status_code != 200:
                print(f"{str(response.status_code) } {endpoint}")
                print("ERROR: Execution aborted")
                print("  - Not all production data loaded, re-start is needed")
                exit()

            results = response.json()
            df_inject = pd.json_normalize(results)

            if df_inject is not None and not df_inject.empty:
                df_selected = df_inject[
                    [
                        "WB_UWBI",
                        "PROD_DAY",
                        "GOV_FIELD_NAME",
                        "GOV_WB_NAME",
                        "WELL_UWI",
                        "INJ_TYPE",
                        "WB_INJ_VOL",
                    ]
                ]
                df_unique = df_selected.drop_duplicates()
                df_unique.to_csv(well_prod_file, index=False)
                print("Injection data stored in", well_prod_file)

        i = i + 1

    if i == len(selected_wellbores):
        inj_status = True

    return inj_status


def extract_production_volume(session, api, selected_wellbores, production_folder):
    prod_status = False
    i = 0
    for j in range(0, len(selected_wellbores)):
        wb_name = selected_wellbores[j]
        rms_name = wb_name.replace("/", "_").replace(" ", "_")
        well_prod_file = os.path.join(
            production_folder, "tmp", "prod_" + rms_name + ".csv"
        )
        if not os.path.isfile(well_prod_file):
            endpoint = api + "/WellBoreProdDay?top=200000&" + "WB_UWBI=" + wb_name
            response = session.get(endpoint)

            if response.status_code != 200:
                print(f"{str(response.status_code) } {endpoint}")
                print("ERROR: Execution aborted")
                print("  - Not all production data loaded, re-start is needed")
                exit()

            results = response.json()
            df_prod = pd.json_normalize(results)

            if df_prod is not None and not df_prod.empty:
                df_selected = df_prod[
                    [
                        "WB_UWBI",
                        "GOV_WB_NAME",
                        "WELL_UWI",
                        "PROD_DAY",
                        "WB_OIL_VOL_SM3",
                        "WB_GAS_VOL_SM3",
                        "WB_WATER_VOL_M3",
                        "GOV_FIELD_NAME",
                    ]
                ]
                df_unique = df_selected.drop_duplicates()
                df_unique.to_csv(well_prod_file, index=False)
                print("Production data stored in", well_prod_file)

        i = i + 1

    if i == len(selected_wellbores):
        prod_status = True

    return prod_status
