"""Authors: Cody Baker."""
import numpy as np
from typing import Optional
from pathlib import Path
from tempfile import mkdtemp
from shutil import rmtree
from time import perf_counter

from spikeextractors import RecordingExtractor, SubRecordingExtractor
from pynwb import NWBHDF5IO

from .spike_interface import write_recording


class WriteRecordingProfiler():
    """Class for use in testing IO properties of raw ecephys recording data in NWB format."""

    def __init__(
            self, recording: RecordingExtractor, mb_threshold: float = 100.0, write_kwargs: Optional[dict] = None
    ):
        """
        Test the write speed of recording data to NWB on this system.

        Parameters
        ----------
        recording : RecordingExtractor
            The recording object to be written.
        mb_threshold : float
            Maximum amount of data to test with.
            Defaults to 100, which is just over 2 seconds of standard 384-channel SpikeGLX data.
        """
        if write_kwargs is None:
            write_kwargs = dict()
        self.num_channels = recording.get_num_channels()
        self.itemsize = recording.get_dtype().itemsize
        self.total_mb = recording.get_num_frames() * self.num_channels * self.itemsize / 1e6
        if self.total_mb > mb_threshold:
            truncation = (mb_threshold * 1e6) // (self.num_channels * self.itemsize)
            test_recording = SubRecordingExtractor(parent_recording=recording, end_frame=truncation)
        else:
            test_recording = recording
        self.test_mb = test_recording.get_num_frames() * self.num_channels * self.itemsize / 1e6
        self.test_recording = test_recording
        self.write_kwargs = write_kwargs
        self.temp_dir = Path(mkdtemp())
        self.test_nwbfile_path = self.temp_dir / "recording_test.nwb"

    def __del__(self):
        rmtree(self.temp_dir)

    def estimate_conversion_time(self) -> (float, float):
        """
        Test the write speed of recording data to NWB on this system.

        Returns
        -------
        total_time_estimate : float
            Estimate of total time (in minutes) to write all data based on speed estimate and known total data size.
        speed : float
            Speed of the conversion in MB/s.
        """
        start = perf_counter()
        write_recording(
            recording=self.test_recording, save_path=self.test_nwbfile_path, overwrite=True, **self.write_kwargs
        )
        end = perf_counter()
        delta = end - start
        speed = self.test_mb / (end - start)
        total_time_estimate = (self.total_mb / speed) / 60
        return total_time_estimate, speed

    def estimate_compression_ratio(self) -> float:
        """Test the compression ratio from writing the recording data to NWB on this system."""
        if not self.test_nwbfile_path.exists()
            write_recording(recording=self.test_recording, save_path=self.test_nwbfile_path, **self.write_kwargs)

        with NWBHDF5IO(path=test_nwbfile_path, mode="r") as io:
            nwbfile = io.read()
            acquisition = nwbfile.acquisition[list(nwbfile.acquisition.keys())[0]].data
            uncompressed_size = acquisition.size * np.dtype(acquisition.dtype).itemsize
            compressed_size = acquisition.id.get_storage_size()
            ratio = uncompressed_size / compressed_size
        return ratio

    def profile(self) -> dict:
        total_time_estimate, speed = self.estimate_conversion_time()
        compression_ratio = self.estimate_compression_ratio()
        return dict(
            speed=dict(
                total_time_estimate=total_time_estimate,
                speed=speed
            )
            compression=dict(
                compression_ratio=compression_ratio
            )
        )
