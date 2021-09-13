from ..base_interface_icephys_neo import BaseIcephysNeoInterface
from ....utils.json_schema import get_schema_from_method_signature
from neo import AxonIO

from datetime import datetime, timedelta
import pytz


class AbfNeoDataInterface(BaseIcephysNeoInterface):
    """ABF DataInterface based on Neo AxonIO"""

    neo_class = AxonIO

    @classmethod
    def get_source_schema(cls):
        """Compile input schema for the Neo class"""
        source_schema = get_schema_from_method_signature(class_method=cls.__init__, exclude=[])
        source_schema["properties"]["file_path"]["format"] = "file"
        source_schema["properties"]["file_path"]["description"] = "Path to ABF file."
        return source_schema

    def __init__(self, file_path: str):
        super().__init__(filename=file_path)

    def get_metadata(self):
        """Auto-fill as much of the metadata as possible. Must comply with metadata schema."""
        metadata = super().get_metadata()

        # Extract start_time info
        startDate = str(self.reader._axon_info["uFileStartDate"])
        startTime = round(self.reader._axon_info["uFileStartTimeMS"] / 1000)
        startDate = datetime.strptime(startDate, "%Y%M%d")
        startTime = timedelta(seconds=startTime)
        abfDateTime = startDate + startTime
        # Time Zone
        session_start_time_tzaware = pytz.timezone("UTC").localize(abfDateTime)
        session_start_time_tzaware = session_start_time_tzaware.strftime("%Y-%m-%dT%H:%M:%S%z")
        # Add a colon separator to the TZ offset segment
        session_start_time_tzaware = "{0}:{1}".format(session_start_time_tzaware[:-2], session_start_time_tzaware[-2:])

        metadata["NWBFile"] = dict(
            session_start_time=session_start_time_tzaware,
        )

        return metadata
