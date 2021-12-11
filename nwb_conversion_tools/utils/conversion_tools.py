"""Authors: Cody Baker, Alessio Buccino."""
import yaml
import re
import numpy as np
from pathlib import Path
from importlib import import_module
from itertools import chain
from collections import OrderedDict
from copy import deepcopy

from .json_schema import dict_deep_update, FilePathType
from ..nwbconverter import NWBConverter


def check_regular_timestamps(ts):
    """Check whether rate should be used instead of timestamps."""
    time_tol_decimals = 9
    uniq_diff_ts = np.unique(np.diff(ts).round(decimals=time_tol_decimals))
    return len(uniq_diff_ts) == 1


# TODO update this to handle with different types
# def estimate_recording_conversion_time(
#     recording: RecordingExtractor, mb_threshold: float = 100.0, write_kwargs: Optional[dict] = None
# ) -> (float, float):
#     """
#     Test the write speed of recording data to NWB on this system.
#
#     recording : RecordingExtractor
#         The recording object to be written.
#     mb_threshold : float
#         Maximum amount of data to test with. Defaults to 100, which is just over 2 seconds of standard SpikeGLX data.
#
#     Returns
#     -------
#     total_time : float
#         Estimate of total time (in minutes) to write all data based on speed estimate and known total data size.
#     speed : float
#         Speed of the conversion in MB/s.
#     """
#     if write_kwargs is None:
#         write_kwargs = dict()
#
#     temp_dir = Path(mkdtemp())
#     test_nwbfile_path = temp_dir / "recording_speed_test.nwb"
#
#     num_channels = recording.get_num_channels()
#     itemsize = recording.get_dtype().itemsize
#     total_mb = recording.get_num_frames() * num_channels * itemsize / 1e6
#     if total_mb > mb_threshold:
#         truncation = np.floor(mb_threshold * 1e6 / (num_channels * itemsize))
#         test_recording = SubRecordingExtractor(parent_recording=recording, end_frame=truncation)
#     else:
#         test_recording = recording
#
#     actual_test_mb = test_recording.get_num_frames() * num_channels * itemsize / 1e6
#     start = perf_counter()
#     write_recording(recording=test_recording, save_path=test_nwbfile_path, overwrite=True, **write_kwargs)
#     end = perf_counter()
#     delta = end - start
#     speed = actual_test_mb / delta
#     total_time = (total_mb / speed) / 60
#
#     rmtree(temp_dir)
#     return total_time, speed


def yaml_to_dict(file_path: FilePathType):
    """
    Conversion of yaml to dictionary.

    Parameters
    ----------
    file_path : FilePathType
      Path to .yml file.
    """
    with open(file=file_path, mode="r") as io:
        d = yaml.load(stream=io, Loader=yaml.SafeLoader)
    return d


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
    full_spec = yaml_to_dict(file_path=file_path)
    global_metadata = full_spec.get("metadata", dict())
    global_data_interfaces = full_spec.get("data_interfaces")
    nwb_conversion_tools = import_module(
        name=".",
        package="nwb_conversion_tools",  # relative import  # but named and referenced as it were absolute
    )
    for experiment in full_spec["experiments"].values():
        experiment_metadata = experiment.get("metadata", dict())
        experiment_data_interfaces = experiment.get("data_interfaces")
        for session in experiment["sessions"]:
            session_data_interfaces = experiment.get("data_interfaces")
            data_interface_classes = dict()
            for data_interface_name in chain(
                global_data_interfaces, experiment_data_interfaces, session_data_interfaces
            ):
                data_interface_classes.update(data_interface_name=getattr(nwb_conversion_tools, data_interface_name))

            class CustomNWBConverter(NWBConverter):
                data_interface_classes = data_interface_classes

            converter = CustomNWBConverter(source_data=session["source_data"])
            metadata = converter.get_metadata()
            for metadata_source in [global_metadata, experiment_metadata, session.get("metadata", dict())]:
                dict_deep_update(metadata, metadata_source)
            converter.run_conversion(
                nwbfile_path=source_dir / f"{session['nwbfile_name']}.nwb",
                overwrite=overwrite,
                conversion_options=session.get("conversion_options", dict()),
            )


def reverse_fstring_path(string: str):
    keys = set(re.findall(pattern="\\{(.*?)\\}", string=string))

    adjusted_idx = 0
    if string[0] != "/":
        adjusted_string = "/" + string
        adjusted_idx += 1
    else:
        adjusted_string = string
    if adjusted_string[-1] != "/":
        adjusted_string = adjusted_string + "/"

    sub_paths = adjusted_string.split("/")
    output = dict()
    for key in keys:
        sub_levels = []
        for j, sub_path in enumerate(sub_paths, start=-1):
            if key in sub_path:
                sub_levels.append(j)
        output[key] = sub_levels
    return output


def collect_reverse_fstring_files(string: str):
    adjusted_idx = 0
    if string[0] != "/":
        adjusted_string = "/" + string
        adjusted_idx += 1
    else:
        adjusted_string = string
    if adjusted_string[-1] != "/":
        adjusted_string = adjusted_string + "/"

    sub_paths = adjusted_string.split("/")

    output = reverse_fstring_path(string=string)
    min_level = min(min((values) for values in output.values()))

    # Assumes level to iterate is first occurence of each f-key
    iteration_levels = {key: values[0] for key, values in output.items()}
    inverted_iteration_levels = {value: key for key, value in iteration_levels.items()}
    sorted_iteration_levels = OrderedDict()
    for sorted_value in sorted(iteration_levels.values()):
        sorted_iteration_levels.update({sorted_value - min_level: inverted_iteration_levels[sorted_value]})

    def recur_sub_levels_2(
        folder_paths,
        n_levels,
        sorted_iteration_levels,
        path,
        level=0,
    ):
        if level < n_levels:
            next_paths = [x for x in path.iterdir()]
            if level == n_levels - 1:
                for next_path in next_paths:
                    path_split = str(next_path).split("/")
                    output = dict(path=next_path)
                    output.update(
                        {
                            fkey: path_split[-(n_levels - fkey_level)]
                            for fkey_level, fkey in sorted_iteration_levels.items()
                        }
                    )
                    folder_paths.append(output)
            else:
                for next_path in next_paths:
                    recur_sub_levels_2(
                        folder_paths=folder_paths,
                        level=level + 1,
                        n_levels=n_levels,
                        sorted_iteration_levels=sorted_iteration_levels,
                        path=next_path,
                    )

    folder_paths = []
    recur_sub_levels_2(
        folder_paths=folder_paths,
        n_levels=len(sorted_iteration_levels),
        sorted_iteration_levels=sorted_iteration_levels,
        path=Path("/".join(sub_paths[: min_level + 1])),
    )
    return folder_paths
