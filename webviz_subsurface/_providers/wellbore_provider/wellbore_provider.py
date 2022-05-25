import abc
from typing import Optional
from dataclasses import dataclass
from typing import List
from requests import Session

import numpy as np

# import xtgeo


@dataclass(frozen=True)
class SmdaAddress:
    api: str
    session: Session


@dataclass(frozen=True)
class PozoAddress:
    api: str
    session: Session
    field_identifier: str


@dataclass(frozen=True)
class PdmAddress:
    api: str
    session: Session
    field_identifier: str


@dataclass(frozen=True)
class SsdlAddress:
    api: str
    session: Session
    field_identifier: str


@dataclass
class Trajectory:
    coordinate_system: str
    x_arr: np.ndarray
    y_arr: np.ndarray
    z_arr: np.ndarray
    md_arr: np.ndarray


@dataclass
class WellborePick:
    pick_identifier: str
    interpreter: str
    obs_no: list()
    md: np.ndarray


@dataclass
class DrilledWellboreMetadata:
    uuid: List[str]
    unique_wellbore_identifier: List[str]
    unique_well_identifier: List[str]
    purpose: List[str]
    status: List[str]
    content: List[str]
    field_identifier: List[str]
    field_uuid: List[str]
    completion_date: List[str]
    license_identifier: List[str]


@dataclass
class PlannedWellboreMetadata:
    name: List[str]
    templateName: List[str]
    fieldName: List[str]
    wellTypeName: List[str]
    updateDate: List[str]


@dataclass
class Completion:
    well_completion_id: List[str]
    symbol_name: List[str]
    description: List[str]
    md_top: np.ndarray
    md_bottom: np.ndarray


@dataclass
class Perforation:
    well_completion_id: List[str]
    gun_type: List[str]
    md_top: np.ndarray
    md_bottom: np.ndarray


@dataclass
class ProductionVolumes:
    oil: List[float]
    oil_unit: List[str]
    gas: List[float]
    gas_unit: List[str]
    water: List[float]
    water_unit: List[str]
    condensate: List[float]
    condensate_unit: List[str]


@dataclass
class InjectionVolumes:
    gas: List[float]
    gas_unit: List[str]
    water: List[float]
    water_unit: List[str]
    co2: List[float]
    co2_unit: List[str]


@dataclass
class PdmDates:
    start_date: str
    end_date: str


# Class provides data for wellbores
class WellboreProvider(abc.ABC):
    @abc.abstractmethod
    def provider_id(self) -> str:
        """Returns string ID of the provider."""

    @abc.abstractmethod
    def drilled_wellbore_names(
        self, smda_address: SmdaAddress, field: str, license: str
    ) -> List[str]:
        """Returns list of all drilled wellbore names."""

    @abc.abstractmethod
    def drilled_wellbore_metadata(
        self, smda_address: SmdaAddress, field: str, license: str
    ) -> DrilledWellboreMetadata:
        """Returns metadata for all drilled wellbores."""

    @abc.abstractmethod
    def drilled_wellbore_trajectory(
        self,
        smda_address: SmdaAddress,
        wellbore_name: str,
        md_min: Optional[float] = 0,
        md_max: Optional[float] = None,
    ) -> Trajectory:
        """Returns a wellbore trajectory (optionally between md_min and md_max)."""

    # @abc.abstractmethod
    # def planned_wellbore_names(self, PozoAddress) -> List[str]:
    #     """Returns list of all planned wellbore names."""

    # @abc.abstractmethod
    # def planned_wellbore_metadata(self, PozoAddress) -> PlannededWellboreMetadata:
    #     """Returns metadata for all planned wellbores."""

    # @abc.abstractmethod
    # def planned_wellbore_trajectory(
    #     self, PozoAddress, wellbore_name, md_min, md_max
    # ) -> Trajectory:
    #     """Returns a planned wellbore trajectory (optionally between md_min and md_max)."""

    # @abc.abstractmethod
    # def producers_in_time_interval(
    #     self, PdmAddress, first_date, second_date
    # ) -> List[str]:
    #     """Returns list of all available PDM well names with fluids > 0 in selected time interval."""

    # @abc.abstractmethod
    # def injectors_in_time_interval(
    #     self, PdmAddress, first_date, second_date
    # ) -> List[str]:
    #     """Returns list of all available PDM well names."""

    # @abc.abstractmethod
    # def trajectory_after_crossing(
    #     self, SmdaAddress, wellbore_trajectory, depth_surface
    # ) -> Trajectory:
    #     """Returns the part of a wellbore trajectory after crossing a depth surface"""

    # @abc.abstractmethod
    # def wellbore_pick(self, SmdaAddress, wellbore_name, pick_name) -> WellborePick:
    #     """Returns wellbore pick information for the selected wellbore and pick name."""

    # @abc.abstractmethod
    # def wellbore_completion_info(self, SsdlAddress, wellbore_name) -> Completion:
    #     """Returns the wellbore completion information."""

    # @abc.abstractmethod
    # def wellbore_perforation_info(self, SsdlAddress, wellbore_name) -> Perforation:
    #     """Returns a wellbore perforation information."""

    # @abc.abstractmethod
    # def produced_volumes(
    #     self, PdmAddress, pdm_well_name, first_date, second_date
    # ) -> ProductionVolumes:
    #     """Returns produced volumes (all fuids) for the selected PDM well, time interval"""

    # @abc.abstractmethod
    # def injected_volumes(
    #     self, PdmAddress, pdm_well_name, first_date, second_date
    # ) -> InjectionVolumes:
    #     """Returns injected volumes (all fluids) for the selected PDM well ."""

    # @abc.abstractmethod
    # def active_dates(self, PdmAddress, pdm_well_name) -> PdmDates:
    #     """Returns start and last dates (all fluids) for the selected PDM well ."""
