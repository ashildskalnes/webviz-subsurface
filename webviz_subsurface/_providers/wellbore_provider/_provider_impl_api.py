import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from unittest.mock import NonCallableMock
from attr import field
from pandas import DataFrame

import xtgeo

from webviz_subsurface._providers.wellbore_provider.extract_smda_data import (
    extract_smda_data,
)

# from extract_smda_data import smda_opus_connect
# from extract_plannedwell_data import extract_plannedWell_data, plannedWell_connect
# from extract_ssdl_data import extract_ssdl_data, ssdl_connect
# from extract_pdm_data import extract_pdm_data, pdm_connect

from webviz_subsurface._providers.wellbore_provider.wellbore_provider import (
    SmdaAddress,
    WellboreProvider,
    DrilledWellboreMetadata,
    Trajectory,
)

# import wellbore_provider

LOGGER = logging.getLogger(__name__)
MAX_ITEMS = 2000


class ProviderImplApi(WellboreProvider):
    def __init__(self, provider_id: str, provider_dir: Path, smda: Tuple) -> None:
        self.provider_id = provider_id
        self.provider_dir = provider_dir
        smda_api = smda[0]
        smda_session = smda[1]

        self.smda_address = SmdaAddress(api=smda_api, session=smda_session)

        # print("Connect to POZO")
        # self.pozohandle = plannedWell_connect()

        # print("Connect to SSDL")
        # self.ssdlhandle = ssdl_connect()

        # print("Connect to PDM")
        # self.pdmhandle = pdm_connect()

    @property
    def smda_adress(self):
        return self.smda_address

    def provider_id(self) -> str:
        return self._provider_id

    def drilled_wellbore_names(
        self, smda_address: SmdaAddress, field: str, license: str
    ) -> List[str]:

        metadata = self.drilled_wellbore_metadata(
            smda_address=smda_address,
            field=field,
            license=license,
        )

        wellbore_names = metadata.unique_wellbore_identifier

        return wellbore_names

    def drilled_wellbore_metadata(
        self,
        smda_address: SmdaAddress,
        field: str,
        license: str,
    ) -> DrilledWellboreMetadata:

        if field is not None:
            endpoint = (
                smda_address.api
                + "wellbores?_items=MAX_ITEMS&_order=asc&_page=1&field_identifier="
                + field
            )
        elif license is not None:
            endpoint = (
                smda_address.api
                + "wellbores?_items=MAX_ITEMS&_order=asc&_page=1&license_identifier="
                + license
            )
        else:
            raise ValueError("At least one identifier must be specified")

        wellbores_df = extract_smda_data(smda_address.session, endpoint)

        if not wellbores_df.empty:
            metadata = DrilledWellboreMetadata(
                uuid=wellbores_df["uuid"].to_list(),
                unique_wellbore_identifier=wellbores_df[
                    "unique_wellbore_identifier"
                ].to_list(),
                unique_well_identifier=wellbores_df["unique_well_identifier"].to_list(),
                purpose=wellbores_df["purpose"].to_list(),
                status=wellbores_df["status"].to_list(),
                content=wellbores_df["content"].to_list(),
                field_identifier=wellbores_df["field_identifier"].to_list(),
                field_uuid=wellbores_df["field_uuid"].to_list(),
                completion_date=wellbores_df["completion_date"].to_list(),
                license_identifier=wellbores_df["license_identifier"].to_list(),
            )
        else:
            metadata = None

        return metadata

    def drilled_wellbore_trajectory(
        self,
        smda_address: SmdaAddress,
        wellbore_name: str,
        md_min: Optional[float] = 0,
        md_max: Optional[float] = None,
    ) -> Trajectory:

        trajectory_df = DataFrame()
        crs = None
        trajectory = None

        if wellbore_name is not None:
            endpoint = (
                smda_address.api
                + "wellbore-survey-samples?"
                + "_items=MAX_ITEMS&_order=asc&_page=1&unique_wellbore_identifier="
                + wellbore_name
            )
            trajectory_df = extract_smda_data(smda_address.session, endpoint)

            if not trajectory_df.empty:
                endpoint = (
                    smda_address.api
                    + "wellbore-survey-headers?"
                    + "_items=MAX_ITEMS&_order=asc&_page=1&unique_wellbore_identifier="
                    + wellbore_name
                )
                survey_df = extract_smda_data(smda_address.session, endpoint)

                if not survey_df.empty:
                    crs = survey_df["projected_coordinate_system"][0]
        else:
            raise ValueError("Wellbore name must be specified")

        if not trajectory_df.empty:
            trajectory_df.sort_values(by=["md"], inplace=True)

            if md_min > 0:
                if md_max:
                    selected_trajectory_df = trajectory_df[
                        (trajectory_df["md"] >= md_min)
                        & (trajectory_df["md"] <= md_max)
                    ]
                else:
                    selected_trajectory_df = trajectory_df[
                        trajectory_df["md"] >= md_min
                    ]
            else:
                selected_trajectory_df = trajectory_df

            if not selected_trajectory_df.empty:
                trajectory = Trajectory(
                    coordinate_system=crs,
                    x_arr=selected_trajectory_df["easting"].to_numpy(),
                    y_arr=selected_trajectory_df["northing"].to_numpy(),
                    z_arr=selected_trajectory_df["tvd_msl"].to_numpy(),
                    md_arr=selected_trajectory_df["md"].to_numpy(),
                )

        return trajectory
