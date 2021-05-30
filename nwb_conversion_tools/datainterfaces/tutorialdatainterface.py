"""Authors: Cody Baker and Ben Dichter."""
from pathlib import Path

import numpy as np
import spikeextractors as se

from ..utils.json_schema import get_schema_from_method_signature
from ..baserecordingextractorinterface import BaseRecordingExtractorInterface
from ..basesortingextractorinterface import BaseSortingExtractorInterface


class TutorialRecordingInterface(BaseRecordingExtractorInterface):
    """High-pass recording data interface for demonstrating NWB Conversion Tools usage in tutorials."""

    RX = se.NumpyRecordingExtractor

    @classmethod
    def get_source_schema(cls):
        source_schema = get_schema_from_method_signature(se.example_datasets.toy_example)
        source_schema['additionalProperties'] = True
        return source_schema

    def __init__(self, **source_data):
        self.recording_extractor = se.example_datasets.toy_example(**source_data)[0]
        self.subset_channels = None
        self.source_data = source_data

    def get_metadata(self):
        """Auto-populate extracellular electrophysiology metadata."""

        # Electrode data should be added as channel properties to the recording extractor object.
        # Optional descriptions of the properties can then be added to the metadata structure.
        custom_col = [x for x in range(self.recording_extractor.get_num_channels())]
        for channel_id, custom_data in zip(self.recording_extractor.get_channel_ids(), custom_col):
            self.recording_extractor.set_channel_property(
                channel_id=channel_id,
                property_name="group_name",
                value="ElectrodeGroup"
            )
            self.recording_extractor.set_channel_property(
                channel_id=channel_id,
                property_name="custom_electrode_column",
                value=custom_data
            )

        metadata = dict(
            Ecephys=dict(
                Device=[
                    dict(
                        description="Device for the NWB Conversion Tools tutorial."
                    )
                ],
                ElectrodeGroup=[
                    dict(
                        name="ElectrodeGroup",
                        description="Electrode group for the NWB Conversion Tools tutorial."
                    )
                ],
                Electrodes=[
                    dict(
                        name="group_name",
                        description="Custom ElectrodeGroup name for these electrodes."
                    ),
                    dict(
                        name="custom_electrodes_column",
                        description="Custom column in the electrodes table for the NWB Conversion Tools tutorial."
                    )
                ],
                ElectricalSeries=dict(
                    name="ElectricalSeries",
                    description="Raw acquisition traces for the NWB Conversion Tools tutorial."
                )
            )
        )
        return metadata


class TutorialSortingInterface(BaseSortingExtractorInterface):
    """Sorting data interface for demonstrating NWB Conversion Tools usage in tutorials."""

    SX = se.NumpySortingExtractor

    @classmethod
    def get_source_schema(cls):
        source_schema = get_schema_from_method_signature(se.example_datasets.toy_example)
        source_schema['additionalProperties'] = True
        return source_schema

    def __init__(self, **source_data):
        self.sorting_extractor = se.example_datasets.toy_example(**source_data)[1]
        self.source_data = source_data

    def get_metadata(self):
        """Auto-populate unit table metadata."""
        metadata = dict(
            UnitProperties=[
                dict(
                    name="custom_unit_column",
                    description="Custom column in the spiking unit table for the NWB Conversion Tools tutorial.",
                    data=[x for x in range(len(self.sorting_extractor.get_unit_ids()))]
                )
            ]
        )
        return metadata
