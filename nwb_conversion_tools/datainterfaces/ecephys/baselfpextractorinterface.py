"""Authors: Cody Baker, Saksham Sharda, Ben Dichter."""
from typing import Optional, Union
from pathlib import Path
from pynwb.ecephys import ElectricalSeries

from .baserecordingextractorinterface import BaseRecordingExtractorInterface
from ...utils.json_schema import get_schema_from_hdmf_class

OptionalPathType = Optional[Union[str, Path]]


class BaseLFPExtractorInterface(BaseRecordingExtractorInterface):
    """Primary class for all LFP data interfaces."""

    def get_metadata_schema(self):
        metadata_schema = super().get_metadata_schema()
        metadata_schema["properties"]["Ecephys"]["properties"].update(
            ElectricalSeries_lfp=get_schema_from_hdmf_class(ElectricalSeries)
        )
        return metadata_schema

    def get_metadata(self):
        metadata = super().get_metadata()
        metadata["Ecephys"].update(
            ElectricalSeries_lfp=dict(name="ElectricalSeries_lfp", description="Local field potential signal.")
        )
        return metadata
