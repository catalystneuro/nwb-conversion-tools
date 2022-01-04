from datetime import datetime, timedelta
from pynwb.icephys import ExperimentalConditionsTable, IntracellularRecordingsTable
import pytz

from neo import AxonIO

from ..base_interface_icephys_neo import BaseIcephysNeoInterface
from ....utils.neo import get_number_of_electrodes, get_number_of_segments


class AbfNeoDataInterface(BaseIcephysNeoInterface):
    """ABF DataInterface based on Neo AxonIO"""

    neo_class = AxonIO

    @classmethod
    def get_source_schema(cls):
        """Compile input schema for the Neo class"""
        source_schema = super().get_source_schema()
        source_schema["properties"]["files_paths"] = dict(
            type="array", minItems=1, items={"type": "string"}, description="Array of paths to ABF files."
        )
        return source_schema

    def get_metadata(self):
        """Auto-fill as much of the metadata as possible. Must comply with metadata schema."""
        metadata = super().get_metadata()

        # Extract start_time info
        first_reader = self.readers_list[0]
        startDate = str(first_reader._axon_info["uFileStartDate"])
        startTime = round(first_reader._axon_info["uFileStartTimeMS"] / 1000)
        startDate = datetime.strptime(startDate, "%Y%m%d")
        startTime = timedelta(seconds=startTime)
        first_session_time = startDate + startTime
        session_start_time = first_session_time.strftime("%Y-%m-%dT%H:%M:%S%z")

        metadata["NWBFile"] = dict(
            session_start_time=session_start_time,
        )
        metadata["Icephys"]["Recordings"] = list()

        # Extract useful metadata from each reader in the sequence
        i = 0
        ii = 0
        iii = 0
        for ir, reader in enumerate(self.readers_list):
            startDate = str(reader._axon_info["uFileStartDate"])
            startTime = round(reader._axon_info["uFileStartTimeMS"] / 1000)
            startDate = datetime.strptime(startDate, "%Y%m%d")
            startTime = timedelta(seconds=startTime)
            abfDateTime = startDate + startTime

            # Calculate session start time relative to first abf file (first session), in seconds
            relative_session_start_time = abfDateTime - first_session_time
            relative_session_start_time = float(relative_session_start_time.seconds)

            n_segments = get_number_of_segments(reader, block=0)
            n_electrodes = get_number_of_electrodes(reader)

            # Loop through segments (sequential recordings table)
            for sg in range(n_segments):
                # Loop through channels (simultaneous recordings table)
                for el in range(n_electrodes):
                    metadata["Icephys"]["Recordings"].append(
                        dict(
                            relative_session_start_time=relative_session_start_time,
                            stimulus_type="",
                            intracellular_recordings_table_id=i,
                            simultaneous_recordings_table_id=ii,
                            sequential_recordings_table_id=iii,
                            # repetitions_table_id=0,
                            # experimental_conditions_table_id=0
                        )
                    )
                    i += 1
                ii += 1
            iii += 1

        return metadata
