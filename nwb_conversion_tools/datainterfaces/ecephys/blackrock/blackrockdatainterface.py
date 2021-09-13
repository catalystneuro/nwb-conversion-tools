"""Authors: Luiz Tauffer"""
import pytz
from typing import Optional

import spikeextractors as se
from pynwb import NWBFile
from pynwb.ecephys import ElectricalSeries

from .brpylib import NsxFile
from ..baserecordingextractorinterface import BaseRecordingExtractorInterface
from ..basesortingextractorinterface import BaseSortingExtractorInterface
from ....utils.json_schema import (
    get_schema_from_hdmf_class,
    get_schema_from_method_signature,
    FilePathType,
    OptionalFilePathType,
)


class BlackrockRecordingExtractorInterface(BaseRecordingExtractorInterface):
    """Primary data interface class for converting a BlackrockRecordingExtractor."""

    RX = se.BlackrockRecordingExtractor

    @classmethod
    def get_source_schema(cls):
        """Compile input schema for the RecordingExtractor."""
        source_schema = get_schema_from_method_signature(
            class_method=cls.__init__, exclude=["block_index", "seg_index"]
        )
        source_schema["properties"]["file_path"]["description"] = "Path to Blackrock file."
        return source_schema

    def __init__(
        self, file_path: FilePathType, nsx_override: OptionalFilePathType = None, nsx_to_load: Optional[int] = None
    ):
        super().__init__(filename=file_path, nsx_override=nsx_override, nsx_to_load=nsx_to_load)

    def get_metadata_schema(self):
        """Compile metadata schema for the RecordingExtractor."""
        metadata_schema = super().get_metadata_schema()
        metadata_schema["properties"]["Ecephys"]["properties"].update(
            ElectricalSeries_raw=get_schema_from_hdmf_class(ElectricalSeries),
            ElectricalSeries_processed=get_schema_from_hdmf_class(ElectricalSeries),
        )
        return metadata_schema

    def get_metadata(self):
        """Auto-fill as much of the metadata as possible. Must comply with metadata schema."""
        metadata = super().get_metadata()

        # Open file and extract headers
        nsx_file = NsxFile(datafile=self.source_data["filename"])
        session_start_time = nsx_file.basic_header["TimeOrigin"]
        session_start_time_tzaware = pytz.timezone("EST").localize(session_start_time)
        comment = nsx_file.basic_header["Comment"]

        # Updates basic metadata from files
        metadata["NWBFile"] = dict(
            session_start_time=session_start_time_tzaware.strftime("%Y-%m-%dT%H:%M:%S"),
            session_description=comment,
        )

        # Checks if data is raw or processed
        if max(self.recording_extractor.neo_reader.nsx_to_load) >= 5:
            metadata["Ecephys"]["ElectricalSeries_raw"] = dict(name="ElectricalSeries_raw")
        else:
            metadata["Ecephys"]["ElectricalSeries_processed"] = dict(name="ElectricalSeries_processed")

        return metadata

    def run_conversion(
        self,
        nwbfile: NWBFile,
        metadata: dict = None,
        stub_test: bool = False,
        use_times: bool = False,
        save_path: OptionalFilePathType = None,
        overwrite: bool = False,
        write_as: str = "raw",
        es_key: str = None,
    ):
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
        use_times: bool
            If True, the timestamps are saved to the nwb file using recording.frame_to_time(). If False (default),
            the sampling rate is used.
        write_as_lfp: bool (optional, defaults to False)
            If True, writes the traces under a processing LFP module in the NWBFile instead of acquisition.
        save_path: OptionalFilePathType
            Required if an nwbfile is not passed. Must be the path to the nwbfile
            being appended, otherwise one is created and written.
        overwrite: bool
            If using save_path, whether or not to overwrite the NWBFile if it already exists.
        stub_test: bool, optional (default False)
            If True, will truncate the data to run the conversion faster and take up less memory.
        """
        if max(self.recording_extractor.neo_reader.nsx_to_load) >= 5:
            write_as = "raw"
        elif write_as not in ["processed", "lfp"]:
            write_as = "processed"

        print(f"Converting Blackrock {write_as} traces...")

        super().run_conversion(
            nwbfile=nwbfile,
            metadata=metadata,
            use_times=use_times,
            write_as=write_as,
            es_key=es_key,
            save_path=save_path,
            overwrite=overwrite,
            stub_test=stub_test,
        )


class BlackrockSortingExtractorInterface(BaseSortingExtractorInterface):
    """Primary data interface class for converting Blackrock spiking data."""

    SX = se.BlackrockSortingExtractor

    @classmethod
    def get_source_schema(cls):
        metadata_schema = get_schema_from_method_signature(
            class_method=cls.__init__, exclude=["block_index", "seg_index"]
        )
        metadata_schema["additionalProperties"] = True
        metadata_schema["properties"]["file_path"].update(description="Path to Blackrock file.")
        return metadata_schema

    def __init__(
        self, file_path: FilePathType, nsx_to_load: Optional[int] = None, nev_override: OptionalFilePathType = None
    ):
        super().__init__(filename=file_path, nsx_to_load=nsx_to_load, nev_override=nev_override)
