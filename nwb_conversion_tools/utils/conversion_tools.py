"""Authors: Cody Baker, Alessio Buccino."""
import yaml
import numpy as np
from pathlib import Path
from tempfile import mkdtemp
from shutil import rmtree
from time import perf_counter
from typing import Optional
from importlib import import_module

from spikeextractors import RecordingExtractor, SubRecordingExtractor

from .json_schema import dict_deep_update, FilePathType
from .spike_interface import write_recording
from ..nwbconverter import NWBConverter


def check_regular_timestamps(ts):
    """Check whether rate should be used instead of timestamps."""
    time_tol_decimals = 9
    uniq_diff_ts = np.unique(np.diff(ts).round(decimals=time_tol_decimals))
    return len(uniq_diff_ts) == 1


def estimate_recording_conversion_time(
    recording: RecordingExtractor, mb_threshold: float = 100.0, write_kwargs: Optional[dict] = None
) -> (float, float):
    """
    Test the write speed of recording data to NWB on this system.

    recording : RecordingExtractor
        The recording object to be written.
    mb_threshold : float
        Maximum amount of data to test with. Defaults to 100, which is just over 2 seconds of standard SpikeGLX data.

    Returns
    -------
    total_time : float
        Estimate of total time (in minutes) to write all data based on speed estimate and known total data size.
    speed : float
        Speed of the conversion in MB/s.
    """
    if write_kwargs is None:
        write_kwargs = dict()

    temp_dir = Path(mkdtemp())
    test_nwbfile_path = temp_dir / "recording_speed_test.nwb"

    num_channels = recording.get_num_channels()
    itemsize = recording.get_dtype().itemsize
    total_mb = recording.get_num_frames() * num_channels * itemsize / 1e6
    if total_mb > mb_threshold:
        truncation = (mb_threshold * 1e6) // (num_channels * itemsize)
        test_recording = SubRecordingExtractor(parent_recording=recording, end_frame=truncation)
    else:
        test_recording = recording

    actual_test_mb = test_recording.get_num_frames() * num_channels * itemsize / 1e6
    start = perf_counter()
    write_recording(recording=test_recording, save_path=test_nwbfile_path, overwrite=True, **write_kwargs)
    end = perf_counter()
    delta = end - start
    speed = actual_test_mb / delta
    total_time = (total_mb / speed) / 60

    rmtree(temp_dir)
    return total_time, speed


def run_conversion_from_yaml(file_path: FilePathType, overwrite: bool = False):
    """
    Run conversion to NWB given a yaml specification file.

    Parameters
    ----------
    file_path : FilePathType
        File path leading to .yml specification file for NWB conversion.
    overwrite : bool, optional
        If True, replaces any existing NWBFile at the nwbfile_path location, if save_to_file is True.
        If False, appends the existing NWBFile at the nwbfile_path location, if save_to_file is True.
        The default is False.

    """
    source_dir = Path(file_path).parent.absolute()
    with open(file=file_path, mode="r") as io:
        full_spec = yaml.load(stream=io, Loader=yaml.SafeLoader)
    global_metadata = full_spec["global_metadata"]
    nwb_conversion_tools = import_module(
        name=".", package="nwb_conversion_tools",  # relative import  # but named and referenced as it were absolute
    )
    for experiment in full_spec["experiments"].values():
        experiment_metadata = experiment["experiment_metadata"]
        for session in experiment["sessions"]:
            data_interface_classes = dict()
            for data_interface_name in experiment["data_interfaces"]:
                data_interface_class = getattr(nwb_conversion_tools, data_interface_name)
                data_interface_classes.update(data_interface_name=data_interface_class)

            class CustomNWBConverter(NWBConverter):
                data_interface_classes = data_interface_classes

            converter = CustomNWBConverter(source_data=session["source_data"])
            metadata = converter.get_metadata()
            for metadata_source in [global_metadata, experiment_metadata, session["session_metadata"]]:
                dict_deep_update(metadata, metadata_source)
            converter.run_conversion(nwbfile_path=source_dir / f"{session['nwbfile_name']}.nwb", overwrite=overwrite)
