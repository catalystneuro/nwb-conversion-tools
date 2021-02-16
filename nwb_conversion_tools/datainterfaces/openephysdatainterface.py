"""Authors: Luiz Tauffer"""
import random
import string
import pytz
import uuid
from typing import Union, Optional
from pathlib import Path
import spikeextractors as se
from pynwb import NWBFile

from ..baserecordingextractorinterface import BaseRecordingExtractorInterface
from ..basesortingextractorinterface import BaseSortingExtractorInterface
from ..json_schema_utils import get_schema_from_method_signature
from .interface_utils.brpylib import NsxFile

PathType = Union[str, Path, None]


class OpenEphysRecordingExtractorInterface(BaseRecordingExtractorInterface):
    """Primary data interface class for converting a OpenEphysRecordingExtractor."""

    RX = se.OpenEphysRecordingExtractor

    @classmethod
    def get_source_schema(cls):
        """Compile input schema for the RecordingExtractor."""
        metadata_schema = get_schema_from_method_signature(
            class_method=cls.__init__,
            exclude=['recording_id', 'experiment_id']
        )
        metadata_schema['additionalProperties'] = True
        return metadata_schema
    
    def __init__(self, folder_path: PathType, experiment_id: Optional[int] = 0, 
                 recording_id: Optional[int] = 0):
        super().__init__(folder_path=str(folder_path), experiment_id=experiment_id, 
                         recording_id=recording_id)

    def get_metadata(self):
        """Auto-fill as much of the metadata as possible. Must comply with metadata schema."""
        metadata = super().get_metadata()

        # Open file and extract info
        session_start_time = self.recording_extractor._file_obj.experiments[0].datetime
        session_start_time_tzaware = pytz.timezone('EST').localize(session_start_time)

        metadata['NWBFile'] = dict(
            session_start_time=session_start_time_tzaware,
            identifier=str(uuid.uuid1())
        )

        # Ecephys metadata
        device_name = self.recording_extractor._file_obj.experiments[0].acquisition_system
        metadata['Ecephys'] = dict(
            Device=[dict(
                name=device_name,
                description='no description'
            )],
            ElectrodeGroup=[],
        )

        return metadata

    def run_conversion(self, nwbfile: NWBFile, metadata: dict = None, use_timestamps: bool = False, 
                       write_as_lfp: bool = False, save_path: PathType = None, overwrite: bool = False, 
                       stub_test: bool = False):
        """
        Primary function for converting recording extractor data to nwb.

        Parameters
        ----------
        nwbfile: NWBFile
            nwb file to which the recording information is to be added
        metadata: dict
            metadata info for constructing the nwb file (optional).
            Should be of the format
                metadata['Ecephys']['ElectricalSeries'] = {'name': my_name,
                                                           'description': my_description}
        use_timestamps: bool
            If True, the timestamps are saved to the nwb file using recording.frame_to_time(). If False (defualut),
            the sampling rate is used.
        write_as_lfp: bool (optional, defaults to False)
            If True, writes the traces under a processing LFP module in the NWBFile instead of acquisition.
        save_path: PathType
            Required if an nwbfile is not passed. Must be the path to the nwbfile
            being appended, otherwise one is created and written.
        overwrite: bool
            If using save_path, whether or not to overwrite the NWBFile if it already exists.
        stub_test: bool, optional (default False)
            If True, will truncate the data to run the conversion faster and take up less memory.
        """

        super().run_conversion(
            nwbfile=nwbfile, 
            metadata=metadata, 
            use_timestamps=use_timestamps, 
            write_as_lfp=write_as_lfp,
            save_path=save_path, 
            overwrite=overwrite,
            stub_test=stub_test
        )


class OpenEphysSortingExtractorInterface(BaseSortingExtractorInterface):
    """Primary data interface class for converting OpenEphys spiking data."""

    SX = se.OpenEphysSortingExtractor

    def __init__(self, filename: PathType, nsx_to_load: Optional[int] = None):
        super().__init__(filename=filename, nsx_to_load=nsx_to_load)

    # def get_metadata(self):
    #     """Auto-populates spiking unit metadata."""
    #     metadata = super().get_metadata()
    #     return metadata