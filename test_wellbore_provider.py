import os
from pathlib import Path

from dotenv import load_dotenv

from webviz_subsurface._providers.wellbore_provider._provider_impl_api import (
    ProviderImplApi,
)

from webviz_subsurface._providers.wellbore_provider.extract_smda_data import (
    smda_opus_connect,
)

SMDA_API = "https://api.gateway.equinor.com/smda/v2.0/smda-api/"
POZO_API = "https://wfmwellapiprod.azurewebsites.net/"
SSDL_API = "https://api.gateway.equinor.com/subsurfacedata/v3/api/v3.0/"
PDM_API = "https://api.gateway.equinor.com/pdm-internal-api/v3/api"


def main():
    provider_id = "test"
    provider_dir = Path("dummy")
    field = "GRANE"

    md_min = 0
    md_max = None

    home = os.path.expanduser("~")
    env_path = os.path.expanduser(os.path.join(home, ".omniaapi"))
    load_dotenv(dotenv_path=env_path)

    tenant = os.environ.get("TENANT")
    authority = "https://login.microsoftonline.com/" + tenant
    client_id = os.environ.get("WEBVIZ_4D_ID")
    subscription_key = os.environ.get("SMDA_SUBSCRIPTION_KEY")
    cache_filename = os.path.join(home, "SMDA_token_cache.bin")
    resource = os.environ.get("SMDA_RESOURCE")
    scope = resource + "/user_impersonation"

    smda_session = smda_opus_connect(
        client_id, subscription_key, authority, scope, cache_filename
    )

    smda = (SMDA_API, smda_session)
    provider = ProviderImplApi(provider_id, provider_dir, smda)
    smda_address = provider.smda_address

    # Get drilled wellbore names
    wellbore_names = provider.drilled_wellbore_names(
        smda_address=smda_address, field=field, license=None
    )
    drilled_wellbore_names = wellbore_names
    print(drilled_wellbore_names)

    # Get drilled wellbore metadata
    drilled_wellbore_metadata = provider.drilled_wellbore_metadata(
        smda_address=smda_address, field=field, license=None
    )

    # Get trajectories for all wellbores
    drilled_wells = []
    not_drilled_wells = []
    for wellbore in drilled_wellbore_metadata.unique_wellbore_identifier:
        print(wellbore)

        trajectory = provider.drilled_wellbore_trajectory(
            smda_address=smda_address,
            wellbore_name=wellbore,
            md_min=md_min,
            md_max=md_max,
        )

        if trajectory is not None:
            drilled_wells.append(wellbore)
            print("  ", trajectory.coordinate_system)
            print(
                "  ",
                trajectory.x_arr[0],
                trajectory.y_arr[0],
                trajectory.z_arr[0],
                trajectory.md_arr[0],
            )
            print("   ...")
            print(
                "  ",
                trajectory.x_arr[-1],
                trajectory.y_arr[-1],
                trajectory.z_arr[-1],
                trajectory.md_arr[-1],
            )
            print("")
        else:
            print("   - trajectory not found")
            not_drilled_wells.append(wellbore)

    print("Number of drilled wellbore names", len(drilled_wellbore_names))
    print("Number of wellbores with trajectory", len(drilled_wells))
    print("Number of wellbores without trajectory", len(not_drilled_wells))


if __name__ == "__main__":
    main()
