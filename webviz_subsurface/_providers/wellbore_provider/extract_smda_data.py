import os
import requests
import pandas as pd

from webviz_subsurface._providers.wellbore_provider.msal_authorization import (
    msal_get_token,
)


def smda_opus_connect(client_id, subscription_key, authority, scope, cache_filename):
    result = msal_get_token(client_id, authority, scope, cache_filename)

    if result is not None:
        expires_in = result["expires_in"]
        # print(f"SMDA token Expires in {int(expires_in)/60} min")

    session = requests.session()

    if "access_token" in result:
        print("Create a new SMDA session \n")
        session.headers.update(
            {
                "Authorization": "Bearer " + result["access_token"],
                "Ocp-Apim-Subscription-Key": subscription_key,
            }
        )
    else:
        print("Could not connect to SMDA, Error:", result.get("error"))
        print(result.get("error_description"), "\n")

    return session


def extract_smda_data(session, endpoint):
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
