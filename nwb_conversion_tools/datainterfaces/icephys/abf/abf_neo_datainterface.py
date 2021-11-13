from datetime import datetime, timedelta
import pytz

from neo import AxonIO

from ..base_interface_icephys_neo import BaseIcephysNeoInterface


class AbfNeoDataInterface(BaseIcephysNeoInterface):
    """ABF DataInterface based on Neo AxonIO"""

    neo_class = AxonIO

    @classmethod
    def get_source_schema(cls):
        """Compile input schema for the Neo class"""
        source_schema = super().get_source_schema()
        source_schema["properties"]["file_path"].update(format="file", description="Path to ABF file.")
        return source_schema

    def __init__(self, file_path: str):
        super().__init__(filename=file_path)

    def get_metadata(self):
        """Auto-fill as much of the metadata as possible. Must comply with metadata schema."""
        metadata = super().get_metadata()

        # Extract start_time info
        startDate = str(self.reader._axon_info["uFileStartDate"])
        startTime = round(self.reader._axon_info["uFileStartTimeMS"] / 1000)
        startDate = datetime.strptime(startDate, "%Y%m%d")
        startTime = timedelta(seconds=startTime)
        abfDateTime = startDate + startTime
        session_start_time = abfDateTime.strftime("%Y-%m-%dT%H:%M:%S%z")

        metadata["NWBFile"] = dict(
            session_start_time=session_start_time,
        )

        return metadata
