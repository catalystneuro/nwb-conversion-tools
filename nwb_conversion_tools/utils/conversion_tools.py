"""Authors: Cody Baker, Alessio Buccino."""
import re
import numpy as np
from pathlib import Path
from importlib import import_module
from itertools import chain
from collections import OrderedDict
from copy import deepcopy
from jsonschema import validate, RefResolver

from .json_schema import dict_deep_update, load_dict_from_file, FilePathType, OptionalFolderPathType
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


def run_conversion_from_yaml(
    specification_file_path: FilePathType,
    data_folder: OptionalFolderPathType = None,
    output_folder: OptionalFolderPathType = None,
    overwrite: bool = False,
):
    """
    Run conversion to NWB given a yaml specification file.

    Parameters
    ----------
    specification_file_path : FilePathType
        File path leading to .yml specification file for NWB conversion.
    data_folder : FolderPathType, optional
        Folder path leading to root location of the data files.
        The default is the parent directory of the specification_file_path.
    output_folder : FolderPathType, optional
        Folder path leading to the desired output location of the .nwb files.
        The default is the parent directory of the specification_file_path.
    overwrite : bool, optional
        If True, replaces any existing NWBFile at the nwbfile_path location, if save_to_file is True.
        If False, appends the existing NWBFile at the nwbfile_path location, if save_to_file is True.
        The default is False.
    """
    if data_folder is None:
        data_folder = Path(specification_file_path).parent
    if output_folder is None:
        output_folder = Path(specification_file_path).parent

    specification = load_dict_from_file(file_path=specification_file_path)
    schema_folder = Path(__file__).parent.parent / "schemas"
    specification_schema = load_dict_from_file(file_path=schema_folder / "yaml_specification_schema.json")
    validate(
        instance=specification,
        schema=specification_schema,
        resolver=RefResolver(base_uri="file://" + str(schema_folder) + "/", referrer=specification_schema),
    )

    global_metadata = specification.get("metadata", dict())
    global_data_interfaces = specification.get("data_interfaces")
    nwb_conversion_tools = import_module(
        name=".",
        package="nwb_conversion_tools",  # relative import, but named and referenced as if it were absolute
    )
    for experiment in specification["experiments"].values():
        experiment_metadata = experiment.get("metadata", dict())
        experiment_data_interfaces = experiment.get("data_interfaces")
        for session in experiment["sessions"]:
            session_data_interfaces = session.get("data_interfaces")
            data_interface_classes = dict()
            data_interfaces_names_chain = chain(
                *[
                    data_interfaces
                    for data_interfaces in [global_data_interfaces, experiment_data_interfaces, session_data_interfaces]
                    if data_interfaces is not None
                ]
            )
            for data_interface_name in data_interfaces_names_chain:
                data_interface_classes.update({data_interface_name: getattr(nwb_conversion_tools, data_interface_name)})

            CustomNWBConverter = type(
                "CustomNWBConverter", (NWBConverter,), dict(data_interface_classes=data_interface_classes)
            )

            source_data = session["source_data"]
            for interface_name, interface_source_data in session["source_data"].items():
                for key, value in interface_source_data.items():
                    source_data[interface_name].update({key: str(Path(data_folder) / value)})

            converter = CustomNWBConverter(source_data=source_data)
            metadata = converter.get_metadata()
            for metadata_source in [global_metadata, experiment_metadata, session.get("metadata", dict())]:
                metadata = dict_deep_update(metadata, metadata_source)
            converter.run_conversion(
                nwbfile_path=Path(output_folder) / f"{session['nwbfile_name']}.nwb",
                metadata=metadata,
                overwrite=overwrite,
                conversion_options=session.get("conversion_options", dict()),
            )
