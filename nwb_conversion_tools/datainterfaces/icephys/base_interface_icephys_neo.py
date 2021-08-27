from abc import ABC
from typing import Union, Optional
from pathlib import Path
import numpy as np

import spikeextractors as se
from pynwb import NWBFile
from pynwb.device import Device
from pynwb.icephys import IntracellularElectrode

from ...basedatainterface import BaseDataInterface
from ...utils.json_schema import (
    get_schema_from_hdmf_class,
    get_schema_from_method_signature,
    fill_defaults,
    get_base_schema
)
from ...utils.spike_interface import write_recording

OptionalPathType = Optional[Union[str, Path]]


# TODO - get number of electrodes
def get_number_of_electrodes(neo_reader, block: int=0) -> int:
    """
    Get number of electrodes from Neo reader

    Args:
        neo_reader ([type]): Neo reader
        block (int, optional): [description]. Defaults to 0.

    Returns:
        int: number of electrodes
    """
    return 0

# TODO - get electrodes metadata
def get_electrodes_metadata(neo_reader, electrodes_ids: list, block: int=0) -> list:
    """
    Get electrodes metadata from Neo reader. The typical information we look for is the information
    accepted by pynwb.icephys.IntracellularElectrode:
    - name – the name of this electrode
    - device – the device that was used to record from this electrode
    - description – Recording description, description of electrode (e.g., whole-cell, sharp, etc) COMMENT: Free-form text (can be from Methods)
    - slice – Information about slice used for recording.
    - seal – Information about seal used for recording.
    - location – Area, layer, comments on estimation, stereotaxis coordinates (if in vivo, etc).
    - resistance – Electrode resistance COMMENT: unit: Ohm.
    - filtering – Electrode specific filtering.
    - initial_access_resistance – Initial access resistance.

    Args:
        neo_reader ([type]): Neo reader
        electrodes_ids (list): List of electrodes ids.
        block (int, optional): Block id. Defaults to 0.

    Returns:
        list: List of dictionaries containing electrodes metadata
    """
    return []


class BaseIcephysNeoInterface(BaseDataInterface, ABC):
    """Primary class for all NeoInterfaces."""

    neo_class = None

    @classmethod
    def get_source_schema(cls):
        """Compile input schema for the Neo class"""
        return get_schema_from_method_signature(cls.neo_class.__init__)

    def __init__(self, **source_data):
        super().__init__(**source_data)
        self.reader = self.neo_class(**source_data)
        self.subset_channels = None
        self.source_data = source_data

    def get_metadata_schema(self):
        """Compile metadata schema for the Neo interface"""
        metadata_schema = super().get_metadata_schema()

        # Initiate Ecephys metadata
        metadata_schema['properties']['Icephys'] = get_base_schema(tag='Icephys')
        metadata_schema['properties']['Icephys']['required'] = ['Device', 'IntracellularElectrode']
        metadata_schema['properties']['Icephys']['properties'] = dict(
            Device=dict(
                type="array",
                minItems=1,
                items={"$ref": "#/properties/Ecephys/properties/definitions/Device"}
            ),
            IntracellularElectrode=dict(
                type="array",
                minItems=1,
                items={"$ref": "#/properties/Ecephys/properties/definitions/IntracellularElectrode"}
            ),
        )
        # Schema definition for arrays
        metadata_schema['properties']['Ecephys']['properties']["definitions"] = dict(
            Device=get_schema_from_hdmf_class(Device),
            IntracellularElectrode=get_schema_from_hdmf_class(IntracellularElectrode),
        )
        return metadata_schema

    def get_metadata(self):
        metadata = super().get_metadata()
        metadata['Ecephys'] = dict(
            Device=[
                dict(
                    name='Device_icephys',
                    description='no description'
                )
            ],
            IntracellularElectrode=[
                dict(
                    name=f'electrode-{i}',
                    description="no description",
                    device='Device_icephys'
                )
                for i in range(get_number_of_electrodes(self.reader))
            ],
        )
        return metadata

    def run_conversion(
        self,
        nwbfile: NWBFile,
        metadata: dict = None,
        stub_test: bool = False,
        use_times: bool = False,
        save_path: OptionalPathType = None,
        overwrite: bool = False,
        buffer_mb: int = 500,
        write_as: str = 'raw',
        es_key: str = None,
    ):
        """
        Primary function for converting raw (unprocessed) RecordingExtractor data to the NWB standard.

        Parameters
        ----------
        nwbfile: NWBFile
            nwb file to which the recording information is to be added
        metadata: dict
            metadata info for constructing the nwb file (optional).
            Should be of the format
                metadata['Ecephys']['ElectricalSeries'] = dict(name=my_name, description=my_description)
        use_times: bool
            If True, the times are saved to the nwb file using recording.frame_to_time(). If False (default),
            the sampling rate is used.
        save_path: PathType
            Required if an nwbfile is not passed. Must be the path to the nwbfile
            being appended, otherwise one is created and written.
        overwrite: bool
            If using save_path, whether or not to overwrite the NWBFile if it already exists.
        stub_test: bool, optional (default False)
            If True, will truncate the data to run the conversion faster and take up less memory.
        buffer_mb: int (optional, defaults to 500MB)
            Maximum amount of memory (in MB) to use per iteration of the internal DataChunkIterator.
            Requires trace data in the RecordingExtractor to be a memmap object.
        write_as: str (optional, defaults to 'raw')
            Options: 'raw', 'lfp' or 'processed'
        es_key: str (optional)
            Key in metadata dictionary containing metadata info for the specific electrical series
        """
        if stub_test or self.subset_channels is not None:
            recording = self.subset_recording(stub_test=stub_test)
        else:
            recording = self.recording_extractor

        write_recording(
            recording=recording,
            nwbfile=nwbfile,
            metadata=metadata,
            use_times=use_times,
            write_as=write_as,
            es_key=es_key,
            save_path=save_path,
            overwrite=overwrite,
            buffer_mb=buffer_mb
        )
