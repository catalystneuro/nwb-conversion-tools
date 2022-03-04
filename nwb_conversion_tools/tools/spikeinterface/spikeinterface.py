"""Author: Cody Baker."""
import uuid
import warnings
import numpy as np
import distutils.version
from pathlib import Path
from typing import Union, Optional, List
from warnings import warn
from collections import defaultdict
from numbers import Real

import pynwb
from spikeinterface import BaseRecording, BaseSorting
from spikeinterface.core.old_api_utils import OldToNewRecording, OldToNewSorting
from spikeextractors import RecordingExtractor, SortingExtractor
from hdmf.data_utils import DataChunkIterator
from hdmf.backends.hdf5.h5_utils import H5DataIO

from .spikeinterfacerecordingdatachunkiterator import SpikeInterfaceRecordingDataChunkIterator
from ..nwb_helpers import get_module, make_nwbfile_from_metadata
from ...utils import dict_deep_update, OptionalFilePathType

SpikeInterfaceRecording = Union[BaseRecording, RecordingExtractor]
SpikeInterfaceSorting = Union[BaseSorting, SortingExtractor]

DynamicTableSupportedDtypes = {list: [], np.ndarray: np.array(np.nan), str: "", Real: np.nan}


def reshape_dynamictable(dt, prop_dict, defaults):
    """
    Prepare an already existing dynamic table to take custom properties using the add_functions.
    Parameters
    ----------
    dt: DynamicTable
    prop_dict: dict
        dict(name=dict(description='',data='', index=bool)
    defaults: dict
        default row values for dt columns
    Returns
    -------
    default_updated: dict
    """
    defaults_updated = defaults
    if dt is None:
        return
    property_default_data = DynamicTableSupportedDtypes
    for colname in dt.colnames:
        if colname not in defaults:
            samp_data = dt[colname].data[0]
            default_datatype = [proptype for proptype in property_default_data if isinstance(samp_data, proptype)][0]
            defaults_updated.update({colname: property_default_data[default_datatype]})
    # for all columns that are new for the given RX, they will
    for name, des_dict in prop_dict.items():
        des_args = dict(des_dict)
        if name not in defaults_updated:
            # build default junk values for data and add that as column directly later:
            default_datatype_list = [
                proptype for proptype in property_default_data if isinstance(des_dict["data"][0], proptype)
            ][0]
            des_args["data"] = [property_default_data[default_datatype_list]] * len(dt.id)
            dt.add_column(name, **des_args)


def add_properties_to_dynamictable(nwbfile, dt_name, prop_dict, defaults, table=None):
    if dt_name == "electrodes":
        add_method = nwbfile.add_electrode_column
        if table is None:
            dt = nwbfile.electrodes
        else:
            dt = table
    else:
        add_method = nwbfile.add_unit_column
        if table is None:
            dt = nwbfile.units
        else:
            dt = table
    if dt is None:
        for prop_name, prop_args in prop_dict.items():
            if prop_name not in defaults:
                add_dict = dict(prop_args)
                _ = add_dict.pop("data")
                add_method(prop_name, **add_dict)
    else:
        reshape_dynamictable(dt, prop_dict, defaults)


def set_dynamic_table_property(
    dynamic_table,
    row_ids,
    property_name,
    values,
    index=False,
    default_value=np.nan,
    table=False,
    description="no description",
):
    if not isinstance(row_ids, list) or not all(isinstance(x, int) for x in row_ids):
        raise TypeError("'ids' must be a list of integers")
    ids = list(dynamic_table.id[:])
    if any([i not in ids for i in row_ids]):
        raise ValueError("'ids' contains values outside the range of existing ids")
    if not isinstance(property_name, str):
        raise TypeError("'property_name' must be a string")
    if len(row_ids) != len(values) and index is False:
        raise ValueError("'ids' and 'values' should be lists of same size")
    if index is False:
        if property_name in dynamic_table:
            for (row_id, value) in zip(row_ids, values):
                dynamic_table[property_name].data[ids.index(row_id)] = value
        else:
            col_data = [default_value] * len(ids)  # init with default val
            for (row_id, value) in zip(row_ids, values):
                col_data[ids.index(row_id)] = value
            dynamic_table.add_column(
                name=property_name, description=description, data=col_data, index=index, table=table
            )
    else:
        if property_name in dynamic_table:
            # TODO
            raise NotImplementedError
        else:
            dynamic_table.add_column(name=property_name, description=description, data=values, index=index, table=table)


def get_nwb_metadata(recording: SpikeInterfaceRecording, metadata: dict = None):
    """
    Return default metadata for all recording fields.

    Parameters
    ----------
    recording: SpikeInterfaceRecording
    metadata: dict
        metadata info for constructing the nwb file (optional).
    """
    if isinstance(recording, RecordingExtractor):
        checked_recording = OldToNewRecording(oldapi_recording_extractor=recording)
    else:
        checked_recording = recording
    metadata = dict(
        NWBFile=dict(
            session_description="Auto-generated by NwbRecordingExtractor without description.",
            identifier=str(uuid.uuid4()),
        ),
        Ecephys=dict(
            Device=[dict(name="Device", description="Ecephys probe. Automatically generated.")],
            ElectrodeGroup=[
                dict(name=str(gn), description="no description", location="unknown", device="Device")
                for gn in np.unique(checked_recording.get_channel_groups())
            ],
        ),
    )
    return metadata


def add_devices(nwbfile: pynwb.NWBFile, metadata: dict = None):
    """
    Add device information to nwbfile object.

    Will always ensure nwbfile has at least one device, but multiple
    devices within the metadata list will also be created.

    Parameters
    ----------
    nwbfile: NWBFile
        nwb file to which the recording information is to be added
    metadata: dict
        metadata info for constructing the nwb file (optional).
        Should be of the format
            metadata['Ecephys']['Device'] = [
                {
                    'name': my_name,
                    'description': my_description
                },
                ...
            ]
        Missing keys in an element of metadata['Ecephys']['Device'] will be auto-populated with defaults.
    """
    if nwbfile is not None:
        assert isinstance(nwbfile, pynwb.NWBFile), "'nwbfile' should be of type pynwb.NWBFile"
    # Default Device metadata
    defaults = dict(name="Device", description="Ecephys probe. Automatically generated.")

    if metadata is None:
        metadata = dict()
    if "Ecephys" not in metadata:
        metadata["Ecephys"] = dict()
    if "Device" not in metadata["Ecephys"]:
        metadata["Ecephys"]["Device"] = [defaults]
    for dev in metadata["Ecephys"]["Device"]:
        if dev.get("name", defaults["name"]) not in nwbfile.devices:
            nwbfile.create_device(**dict(defaults, **dev))


def add_electrode_groups(recording: SpikeInterfaceRecording, nwbfile: pynwb.NWBFile, metadata: dict = None):
    """
    Add electrode group information to nwbfile object.

    Will always ensure nwbfile has at least one electrode group.
    Will auto-generate a linked device if the specified name does not exist in the nwbfile.

    Parameters
    ----------
    recording: SpikeInterfaceRecording
    nwbfile: NWBFile
        nwb file to which the recording information is to be added
    metadata: dict
        metadata info for constructing the nwb file (optional).
        Should be of the format
            metadata['Ecephys']['ElectrodeGroup'] = [
                {
                    'name': my_name,
                    'description': my_description,
                    'location': electrode_location,
                    'device_name': my_device_name
                },
                ...
            ]
        Missing keys in an element of metadata['Ecephys']['ElectrodeGroup'] will be auto-populated with defaults.
        Group names set by RecordingExtractor channel properties will also be included with passed metadata,
        but will only use default description and location.
    """
    assert isinstance(nwbfile, pynwb.NWBFile), "'nwbfile' should be of type pynwb.NWBFile"
    if isinstance(recording, RecordingExtractor):
        checked_recording = OldToNewRecording(oldapi_recording_extractor=recording)
    else:
        checked_recording = recording
    if len(nwbfile.devices) == 0:
        warnings.warn("When adding ElectrodeGroup, no Devices were found on nwbfile. Creating a Device now...")
        add_devices(nwbfile=nwbfile, metadata=metadata)
    if metadata is None:
        metadata = dict()
    if "Ecephys" not in metadata:
        metadata["Ecephys"] = dict()
    defaults = [
        dict(
            name=str(group_id),
            description="no description",
            location="unknown",
            device=[i.name for i in nwbfile.devices.values()][0],
        )
        for group_id in np.unique(checked_recording.get_channel_groups())
    ]

    if "ElectrodeGroup" not in metadata["Ecephys"]:
        metadata["Ecephys"]["ElectrodeGroup"] = defaults
    assert all(
        [isinstance(x, dict) for x in metadata["Ecephys"]["ElectrodeGroup"]]
    ), "Expected metadata['Ecephys']['ElectrodeGroup'] to be a list of dictionaries!"

    for grp in metadata["Ecephys"]["ElectrodeGroup"]:
        if grp.get("name", defaults[0]["name"]) not in nwbfile.electrode_groups:
            device_name = grp.get("device", defaults[0]["device"])
            if device_name not in nwbfile.devices:
                new_device_metadata = dict(Ecephys=dict(Device=[dict(name=device_name)]))
                add_devices(nwbfile=nwbfile, metadata=new_device_metadata)
                warnings.warn(
                    f"Device '{device_name}' not detected in "
                    "attempted link to electrode group! Automatically generating."
                )
            electrode_group_kwargs = dict(defaults[0], **grp)
            electrode_group_kwargs.update(device=nwbfile.devices[device_name])
            nwbfile.create_electrode_group(**electrode_group_kwargs)
    if not nwbfile.electrode_groups:
        device_name = list(nwbfile.devices.keys())[0]
        device = nwbfile.devices[device_name]
        if len(nwbfile.devices) > 1:
            warnings.warn(
                "More than one device found when adding electrode group "
                f"via channel properties: using device '{device_name}'. To use a "
                "different device, indicate it the metadata argument."
            )
        electrode_group_kwargs = dict(defaults[0])
        electrode_group_kwargs.update(device=device)
        for grp_name in np.unique(checked_recording.get_channel_groups()).tolist():
            electrode_group_kwargs.update(name=str(grp_name))
            nwbfile.create_electrode_group(**electrode_group_kwargs)


def add_electrodes(
    recording: SpikeInterfaceRecording, nwbfile: pynwb.NWBFile, metadata: dict = None, exclude: tuple = ()
):
    """
    Add channels from recording object as electrodes to nwbfile object.

    Parameters
    ----------
    recording: SpikeInterfaceRecording
    nwbfile: NWBFile
        nwb file to which the recording information is to be added
    metadata: dict
        metadata info for constructing the nwb file (optional).
        Should be of the format
            metadata['Ecephys']['Electrodes'] = [
                {
                    'name': my_name,
                    'description': my_description
                },
                ...
            ]
        Note that data intended to be added to the electrodes table of the NWBFile should be set as channel
        properties in the RecordingExtractor object.
        Missing keys in an element of metadata['Ecephys']['ElectrodeGroup'] will be auto-populated with defaults
        whenever possible.
        If 'my_name' is set to one of the required fields for nwbfile
        electrodes (id, x, y, z, imp, location, filtering, group_name),
        then the metadata will override their default values.
        Setting 'my_name' to metadata field 'group' is not supported as the linking to
        nwbfile.electrode_groups is handled automatically; please specify the string 'group_name' in this case.
        If no group information is passed via metadata, automatic linking to existing electrode groups,
        possibly including the default, will occur.
    exclude: tuple
        An iterable containing the string names of channel properties in the RecordingExtractor
        object to ignore when writing to the NWBFile.
    """
    assert isinstance(nwbfile, pynwb.NWBFile), "'nwbfile' should be of type pynwb.NWBFile"
    if isinstance(recording, RecordingExtractor):
        checked_recording = OldToNewRecording(oldapi_recording_extractor=recording)
    else:
        checked_recording = recording
    if nwbfile.electrodes is not None:
        ids_already_in_electrode_table = [id in nwbfile.electrodes.id for id in checked_recording.get_channel_ids()]
        if all(ids_already_in_electrode_table):
            warnings.warn("cannot create electrodes for this recording as ids already exist")
            return
    if nwbfile.electrode_groups is None or len(nwbfile.electrode_groups) == 0:
        add_electrode_groups(checked_recording, nwbfile, metadata)
    # For older versions of pynwb, we need to manually add these columns
    if distutils.version.LooseVersion(pynwb.__version__) < "1.3.0":
        if nwbfile.electrodes is None or "rel_x" not in nwbfile.electrodes.colnames:
            nwbfile.add_electrode_column("rel_x", "x position of electrode in electrode group")
        if nwbfile.electrodes is None or "rel_y" not in nwbfile.electrodes.colnames:
            nwbfile.add_electrode_column("rel_y", "y position of electrode in electrode group")
    defaults = dict(
        x=np.nan,
        y=np.nan,
        z=np.nan,
        # There doesn't seem to be a canonical default for impedence, if missing.
        # The NwbRecordingExtractor follows the -1.0 convention, other scripts sometimes use np.nan
        imp=-1.0,
        location="unknown",
        filtering="none",
        group_name="0",
    )
    if metadata is None:
        metadata = dict(Ecephys=dict())
    if "Ecephys" not in metadata:
        metadata["Ecephys"] = dict()
    if "Electrodes" not in metadata["Ecephys"]:
        metadata["Ecephys"]["Electrodes"] = []
    assert all(
        [
            isinstance(x, dict) and set(x.keys()) == set(["name", "description"])
            for x in metadata["Ecephys"]["Electrodes"]
        ]
    ), (
        "Expected metadata['Ecephys']['Electrodes'] to be a list of dictionaries, "
        "containing the keys 'name' and 'description'"
    )
    assert all(
        [x["name"] != "group" for x in metadata["Ecephys"]["Electrodes"]]
    ), "Passing metadata field 'group' is deprecated; pass group_name instead!"

    if nwbfile.electrodes is None:
        nwb_elec_ids = []
    else:
        nwb_elec_ids = nwbfile.electrodes.id.data[:]
    # 1. Build column details from RX properties: dict(name: dict(description='',data=data, index=False))
    elec_columns = defaultdict(dict)
    property_names = checked_recording.get_property_keys()

    exclude_names = list(exclude) + ["contact_vector"]
    for prop in property_names:
        if prop not in exclude_names:
            data = checked_recording.get_property(prop)
            # store data after build and remap some properties to relevant nwb columns:
            if prop == "location":
                location_map = ["rel_x", "rel_y", "rel_z"]
                for prop_name_new, loc in zip(location_map, range(data.shape[1])):
                    elec_columns[prop_name_new].update(description=prop_name_new, data=data[:, loc], index=False)
            else:
                if prop == "brain_area":
                    prop = "location"
                elif prop == "group":
                    if "group_name" not in property_names:
                        prop = "group_name"
                    else:
                        continue
                index = isinstance(data[0], (list, np.ndarray))
                elec_columns[prop].update(description=prop, data=data, index=index)
    # 2. fill with provided custom descriptions
    for x in metadata["Ecephys"]["Electrodes"]:
        if x["name"] not in list(elec_columns):
            raise ValueError(f'"{x["name"]}" not a property of se object, set it first and rerun')
        elec_columns[x["name"]]["description"] = x["description"]
    # 3. For existing electrodes table, add the additional columns and fill with default data:
    add_properties_to_dynamictable(nwbfile, "electrodes", elec_columns, defaults)

    # 4. add info to electrodes table:
    for j, channel_id in enumerate(recording.get_channel_ids()):
        if channel_id not in nwb_elec_ids:
            electrode_kwargs = dict(defaults)
            electrode_kwargs.update(id=channel_id)

            for name, desc in elec_columns.items():
                if name == "group_name":
                    # this should always be present as an electrode column, electrode_groups with that group name
                    # also should be present and created on the call to create_electrode_groups()
                    group_name = str(desc["data"][j])
                    electrode_kwargs.update(dict(group=nwbfile.electrode_groups[group_name], group_name=group_name))
                else:
                    electrode_kwargs[name] = desc["data"][j]
            nwbfile.add_electrode(**electrode_kwargs)


def add_electrical_series(
    recording: SpikeInterfaceRecording,
    nwbfile=None,
    metadata: dict = None,
    segment_index: int = 0,
    starting_time: Optional[float] = None,
    use_times: bool = False,
    write_as: str = "raw",
    es_key: str = None,
    write_scaled: bool = False,
    compression: Optional[str] = "gzip",
    compression_opts: Optional[int] = None,
    iterator_type: Optional[str] = None,
    iterator_opts: Optional[dict] = None,
):
    """
    Auxiliary static method for nwbextractor.

    Adds traces from recording object as ElectricalSeries to nwbfile object.

    Parameters
    ----------
    recording: SpikeInterfaceRecording
    nwbfile: NWBFile
        nwb file to which the recording information is to be added
    metadata: dict
        metadata info for constructing the nwb file (optional).
        Should be of the format
            metadata['Ecephys']['ElectricalSeries'] = dict(
                name=my_name,
                description=my_description
            )
    segment_index : int
        The recording segment to add to the NWBFile.
    starting_time: float (optional)
        Sets the starting time of the ElectricalSeries to a manually set value.
        Increments timestamps if use_times is True.
    use_times: bool (optional, defaults to False)
        If True, the times are saved to the nwb file using recording.frame_to_time(). If False (defualut),
        the sampling rate is used.
    write_as: str (optional, defaults to 'raw')
        How to save the traces data in the nwb file. Options:
        - 'raw' will save it in acquisition
        - 'processed' will save it as FilteredEphys, in a processing module
        - 'lfp' will save it as LFP, in a processing module
    es_key: str (optional)
        Key in metadata dictionary containing metadata info for the specific electrical series
    write_scaled: bool (optional, defaults to True)
        If True, writes the scaled traces (return_scaled=True)
    compression: str (optional, defaults to "gzip")
        Type of compression to use. Valid types are "gzip" and "lzf".
        Set to None to disable all compression.
    compression_opts: int (optional, defaults to 4)
        Only applies to compression="gzip". Controls the level of the GZIP.
    iterator_type: str (optional, defaults to 'v2')
        The type of DataChunkIterator to use.
        'v1' is the original DataChunkIterator of the hdmf data_utils.
        'v2' is the locally developed RecordingExtractorDataChunkIterator, which offers full control over chunking.
    iterator_opts: dict (optional)
        Dictionary of options for the RecordingExtractorDataChunkIterator (iterator_type='v2').
        Valid options are
            buffer_gb: float (optional, defaults to 1 GB)
                Recommended to be as much free RAM as available. Automatically calculates suitable buffer shape.
            chunk_mb: float (optional, defaults to 1 MB)
                Should be below 1 MB. Automatically calculates suitable chunk shape.
        If manual specification of buffer_shape and chunk_shape are desired, these may be specified as well.
    Missing keys in an element of metadata['Ecephys']['ElectrodeGroup'] will be auto-populated with defaults
    whenever possible.
    """
    if isinstance(recording, RecordingExtractor):
        checked_recording = OldToNewRecording(oldapi_recording_extractor=recording)
    else:
        checked_recording = recording
    if nwbfile is not None:
        assert isinstance(nwbfile, pynwb.NWBFile), "'nwbfile' should be of type pynwb.NWBFile!"
    assert compression is None or compression in [
        "gzip",
        "lzf",
    ], "Invalid compression type ({compression})! Choose one of 'gzip', 'lzf', or None."

    if not nwbfile.electrodes:
        add_electrodes(recording, nwbfile, metadata)
    assert write_as in [
        "raw",
        "processed",
        "lfp",
    ], f"'write_as' should be 'raw', 'processed' or 'lfp', but instead received value {write_as}"

    if compression == "gzip":
        if compression_opts is None:
            compression_opts = 4
        else:
            assert compression_opts in range(
                10
            ), "compression type is 'gzip', but specified compression_opts is not an integer between 0 and 9!"
    elif compression == "lzf" and compression_opts is not None:
        warn(f"compression_opts ({compression_opts}) were passed, but compression type is 'lzf'! Ignoring options.")
        compression_opts = None
    if iterator_opts is None:
        iterator_opts = dict()
    if write_as == "raw":
        eseries_kwargs = dict(
            name="ElectricalSeries_raw",
            description="Raw acquired data",
            comments="Generated from SpikeInterface::NwbRecordingExtractor",
        )
    elif write_as == "processed":
        eseries_kwargs = dict(
            name="ElectricalSeries_processed",
            description="Processed data",
            comments="Generated from SpikeInterface::NwbRecordingExtractor",
        )
        ecephys_mod = get_module(
            nwbfile=nwbfile,
            name="ecephys",
            description="Intermediate data from extracellular electrophysiology recordings, e.g., LFP.",
        )
        if "Processed" not in ecephys_mod.data_interfaces:
            ecephys_mod.add(pynwb.ecephys.FilteredEphys(name="Processed"))
    elif write_as == "lfp":
        eseries_kwargs = dict(
            name="ElectricalSeries_lfp",
            description="Processed data - LFP",
            comments="Generated from SpikeInterface::NwbRecordingExtractor",
        )
        ecephys_mod = get_module(
            nwbfile=nwbfile,
            name="ecephys",
            description="Intermediate data from extracellular electrophysiology recordings, e.g., LFP.",
        )
        if "LFP" not in ecephys_mod.data_interfaces:
            ecephys_mod.add(pynwb.ecephys.LFP(name="LFP"))
    if metadata is not None and "Ecephys" in metadata and es_key is not None:
        assert es_key in metadata["Ecephys"], f"metadata['Ecephys'] dictionary does not contain key '{es_key}'"
        eseries_kwargs.update(metadata["Ecephys"][es_key])
    if write_as == "raw":
        assert (
            eseries_kwargs["name"] not in nwbfile.acquisition
        ), f"Raw ElectricalSeries '{eseries_kwargs['name']}' is already written in the NWBFile!"
    elif write_as == "processed":
        assert (
            eseries_kwargs["name"] not in nwbfile.processing["ecephys"].data_interfaces["Processed"].electrical_series
        ), f"Processed ElectricalSeries '{eseries_kwargs['name']}' is already written in the NWBFile!"
    elif write_as == "lfp":
        assert (
            eseries_kwargs["name"] not in nwbfile.processing["ecephys"].data_interfaces["LFP"].electrical_series
        ), f"LFP ElectricalSeries '{eseries_kwargs['name']}' is already written in the NWBFile!"
    channel_ids = checked_recording.get_channel_ids()
    table_ids = [list(nwbfile.electrodes.id[:]).index(id) for id in channel_ids]
    electrode_table_region = nwbfile.create_electrode_table_region(
        region=table_ids, description="electrode_table_region"
    )
    eseries_kwargs.update(electrodes=electrode_table_region)

    # channels gains - for RecordingExtractor, these are values to cast traces to uV.
    # For nwb, the conversions (gains) cast the data to Volts.
    # To get traces in Volts we take data*channel_conversion*conversion.
    channel_conversion = checked_recording.get_channel_gains()
    channel_offset = checked_recording.get_channel_offsets()
    if write_scaled or channel_conversion is None:
        eseries_kwargs.update(conversion=1e-6)
    else:
        if len(np.unique(channel_conversion)) == 1:  # if all gains are equal
            eseries_kwargs.update(conversion=channel_conversion[0] * 1e-6)
        else:
            eseries_kwargs.update(conversion=1e-6)
            eseries_kwargs.update(channel_conversion=channel_conversion)
    if iterator_type is None or iterator_type == "v2":
        ephys_data = SpikeInterfaceRecordingDataChunkIterator(
            recording=checked_recording,
            segment_index=segment_index,
            return_scaled=write_scaled,
            **iterator_opts,
        )
    elif iterator_type == "v1":
        if isinstance(checked_recording.get_traces(end_frame=5, return_scaled=write_scaled), np.memmap) and np.all(
            channel_offset == 0
        ):
            ephys_data = DataChunkIterator(
                data=checked_recording.get_traces(return_scaled=write_scaled), **iterator_opts
            )
        else:
            raise ValueError("iterator_type='v1' only supports memmapable trace types! Use iterator_type='v2' instead.")
    else:
        raise NotImplementedError(f"iterator_type ({iterator_type}) should be either 'v1' or 'v2' (recommended)!")
    eseries_kwargs.update(data=H5DataIO(data=ephys_data, compression=compression, compression_opts=compression_opts))

    if not use_times and starting_time is None:
        eseries_kwargs.update(starting_time=float(checked_recording.get_times(segment_index=segment_index)[0]))
    elif not use_times and starting_time is not None:
        eseries_kwargs.update(starting_time=starting_time)
    if not use_times:
        eseries_kwargs.update(rate=float(recording.get_sampling_frequency()))
    elif not use_times and starting_time is not None:
        eseries_kwargs.update(rate=float(checked_recording.get_sampling_frequency()))
    elif use_times and starting_time is not None:
        eseries_kwargs.update(
            timestamps=H5DataIO(
                data=starting_time
                + checked_recording.get_times()[
                    np.arange(checked_recording.get_num_samples(segment_index=segment_index))
                ],
                compression=compression,
                compression_opts=compression_opts,
            )
        )
    elif use_times and starting_time is None:
        eseries_kwargs.update(
            timestamps=H5DataIO(
                data=checked_recording.get_times()[
                    np.arange(checked_recording.get_num_samples(segment_index=segment_index))
                ],
                compression=compression,
                compression_opts=compression_opts,
            )
        )
    es = pynwb.ecephys.ElectricalSeries(**eseries_kwargs)
    if write_as == "raw":
        nwbfile.add_acquisition(es)
    elif write_as == "processed":
        ecephys_mod.data_interfaces["Processed"].add_electrical_series(es)
    elif write_as == "lfp":
        ecephys_mod.data_interfaces["LFP"].add_electrical_series(es)


def add_epochs(recording: RecordingExtractor, nwbfile: pynwb.NWBFile):
    """
    Auxiliary static method for nwbextractor.

    Adds epochs from recording object to nwbfile object.

    Parameters
    ----------
    recording: RecordingExtractor
        Epochs are supported only by spikeinterface/spikeextractors RecordingExtractor objects; does not support
        spikeinterface/spikeinterface BaseRecording objects.
    nwbfile: NWBFile
        nwb file to which the recording information is to be added
    """
    assert isinstance(
        recording, RecordingExtractor
    ), "'recording' should be a spikeinterface/spikeextractors RecordingExtractor object!"
    assert isinstance(nwbfile, pynwb.NWBFile), "'nwbfile' should be of type pynwb.NWBFile"

    for epoch_name in recording.get_epoch_names():
        epoch = recording.get_epoch_info(epoch_name)
        if nwbfile.epochs is None:
            nwbfile.add_epoch(
                start_time=recording.frame_to_time(epoch["start_frame"]),
                stop_time=recording.frame_to_time(epoch["end_frame"] - 1),
                tags=epoch_name,
            )
        else:
            if [epoch_name] in nwbfile.epochs["tags"][:]:
                ind = nwbfile.epochs["tags"][:].index([epoch_name])
                nwbfile.epochs["start_time"].data[ind] = recording.frame_to_time(epoch["start_frame"])
                nwbfile.epochs["stop_time"].data[ind] = recording.frame_to_time(epoch["end_frame"])
            else:
                nwbfile.add_epoch(
                    start_time=recording.frame_to_time(epoch["start_frame"]),
                    stop_time=recording.frame_to_time(epoch["end_frame"]),
                    tags=epoch_name,
                )


def add_electrodes_info(recording: RecordingExtractor, nwbfile: pynwb.NWBFile, metadata: dict = None):
    """
    Add device, electrode_groups, and electrodes info to the nwbfile.

    Parameters
    ----------
    recording: SpikeInterfaceRecording
    nwbfile: NWBFile
        nwb file to which the recording information is to be added
    metadata: dict
        metadata info for constructing the nwb file (optional).
        Should be of the format
            metadata['Ecephys']['Electrodes'] = [
                {
                    'name': my_name,
                    'description': my_description
                },
                ...
            ]
        Note that data intended to be added to the electrodes table of the NWBFile should be set as channel
        properties in the RecordingExtractor object.
        Missing keys in an element of metadata['Ecephys']['ElectrodeGroup'] will be auto-populated with defaults
        whenever possible.
        If 'my_name' is set to one of the required fields for nwbfile
        electrodes (id, x, y, z, imp, location, filtering, group_name),
        then the metadata will override their default values.
        Setting 'my_name' to metadata field 'group' is not supported as the linking to
        nwbfile.electrode_groups is handled automatically; please specify the string 'group_name' in this case.
        If no group information is passed via metadata, automatic linking to existing electrode groups,
        possibly including the default, will occur.
    """
    add_devices(nwbfile=nwbfile, metadata=metadata)
    add_electrode_groups(recording=recording, nwbfile=nwbfile, metadata=metadata)
    add_electrodes(recording=recording, nwbfile=nwbfile, metadata=metadata)


def add_all_to_nwbfile(
    recording: SpikeInterfaceRecording,
    nwbfile=None,
    starting_time: Optional[float] = None,
    use_times: bool = False,
    metadata: dict = None,
    write_as: str = "raw",
    es_key: str = None,
    write_electrical_series: bool = True,
    write_scaled: bool = False,
    compression: Optional[str] = "gzip",
    compression_opts: Optional[int] = None,
    iterator_type: Optional[str] = None,
    iterator_opts: Optional[dict] = None,
):
    """
    Auxiliary static method for nwbextractor.

    Adds all recording related information from recording object and metadata to the nwbfile object.

    Parameters
    ----------
    recording: SpikeInterfaceRecording
    nwbfile: NWBFile
        nwb file to which the recording information is to be added
    starting_time: float (optional)
        Sets the starting time of the ElectricalSeries to a manually set value.
        Increments timestamps if use_times is True.
    use_times: bool
        If True, the times are saved to the nwb file using recording.get_times(). If False (defualut),
        the sampling rate is used.
    metadata: dict
        metadata info for constructing the nwb file (optional).
        Check the auxiliary function docstrings for more information
        about metadata format.
    write_as: str (optional, defaults to 'raw')
        How to save the traces data in the nwb file. Options:
        - 'raw' will save it in acquisition
        - 'processed' will save it as FilteredEphys, in a processing module
        - 'lfp' will save it as LFP, in a processing module
    es_key: str (optional)
        Key in metadata dictionary containing metadata info for the specific electrical series
    write_electrical_series: bool (optional)
        If True (default), electrical series are written in acquisition. If False, only device, electrode_groups,
        and electrodes are written to NWB.
    write_scaled: bool (optional, defaults to True)
        If True, writes the scaled traces (return_scaled=True)
    compression: str (optional, defaults to "gzip")
        Type of compression to use. Valid types are "gzip" and "lzf".
        Set to None to disable all compression.
    compression_opts: int (optional, defaults to 4)
        Only applies to compression="gzip". Controls the level of the GZIP.
    iterator_type: str (optional, defaults to 'v2')
        The type of DataChunkIterator to use.
        'v1' is the original DataChunkIterator of the hdmf data_utils.
        'v2' is the locally developed RecordingExtractorDataChunkIterator, which offers full control over chunking.
    iterator_opts: dict (optional)
        Dictionary of options for the RecordingExtractorDataChunkIterator (iterator_type='v2')
        or DataChunkIterator (iterator_tpye='v1').
        Valid options are
            buffer_gb : float (optional, defaults to 1 GB, available for both 'v2' and 'v1')
                Recommended to be as much free RAM as available). Automatically calculates suitable buffer shape.
            chunk_mb : float (optional, defaults to 1 MB, only available for 'v2')
                Should be below 1 MB. Automatically calculates suitable chunk shape.
        If manual specification of buffer_shape and chunk_shape are desired, these may be specified as well.
    """
    if nwbfile is not None:
        assert isinstance(nwbfile, pynwb.NWBFile), "'nwbfile' should be of type pynwb.NWBFile"
    add_electrodes_info(recording=recording, nwbfile=nwbfile, metadata=metadata)

    if write_electrical_series:
        add_electrical_series(
            recording=recording,
            nwbfile=nwbfile,
            starting_time=starting_time,
            use_times=use_times,
            metadata=metadata,
            write_as=write_as,
            es_key=es_key,
            write_scaled=write_scaled,
            compression=compression,
            compression_opts=compression_opts,
            iterator_type=iterator_type,
            iterator_opts=iterator_opts,
        )
    if isinstance(recording, RecordingExtractor):
        add_epochs(recording=recording, nwbfile=nwbfile)


def write_recording(
    recording: SpikeInterfaceRecording,
    save_path: OptionalFilePathType = None,
    overwrite: bool = False,
    nwbfile: Optional[pynwb.NWBFile] = None,
    starting_time: Optional[float] = None,
    use_times: bool = False,
    metadata: dict = None,
    write_as: str = "raw",
    es_key: str = None,
    write_electrical_series: bool = True,
    write_scaled: bool = False,
    compression: Optional[str] = "gzip",
    compression_opts: Optional[int] = None,
    iterator_type: Optional[str] = None,
    iterator_opts: Optional[dict] = None,
):
    """
    Primary method for writing a RecordingExtractor object to an NWBFile.

    Parameters
    ----------
    recording: SpikeInterfaceRecording
    save_path: FilePathType, optional
        Required if an nwbfile is not passed. Must be the path to the nwbfile
        being appended, otherwise one is created and written.
    overwrite: bool
        If using save_path, whether or not to overwrite the NWBFile if it already exists.
    nwbfile: NWBFile, optional
        If passed, this function will fill the relevant fields within the NWBFile object.
        E.g., calling
            write_recording(recording=my_recording_extractor, nwbfile=my_nwbfile)
        will result in the appropriate changes to the my_nwbfile object.
        If neither 'save_path' nor 'nwbfile' are specified, an NWBFile object will be automatically generated
        and returned by the function.
    starting_time: float (optional)
        Sets the starting time of the ElectricalSeries to a manually set value.
        Increments timestamps if use_times is True.
    use_times: bool
        If True, the times are saved to the nwb file using recording.get_times(). If False (defualut),
        the sampling rate is used.
    metadata: dict
        metadata info for constructing the nwb file (optional). Should be
        of the format
            metadata['Ecephys'] = {}
        with keys of the forms
            metadata['Ecephys']['Device'] = [
                {
                    'name': my_name,
                    'description': my_description
                },
                ...
            ]
            metadata['Ecephys']['ElectrodeGroup'] = [
                {
                    'name': my_name,
                    'description': my_description,
                    'location': electrode_location,
                    'device': my_device_name
                },
                ...
            ]
            metadata['Ecephys']['Electrodes'] = [
                {
                    'name': my_name,
                    'description': my_description
                },
                ...
            ]
            metadata['Ecephys']['ElectricalSeries'] = {
                'name': my_name,
                'description': my_description
            }
        Note that data intended to be added to the electrodes table of the NWBFile should be set as channel
        properties in the RecordingExtractor object.
    write_as: str (optional, defaults to 'raw')
        How to save the traces data in the nwb file. Options:
        - 'raw' will save it in acquisition
        - 'processed' will save it as FilteredEphys, in a processing module
        - 'lfp' will save it as LFP, in a processing module
    es_key: str (optional)
        Key in metadata dictionary containing metadata info for the specific electrical series
    write_electrical_series: bool (optional)
        If True (default), electrical series are written in acquisition. If False, only device, electrode_groups,
        and electrodes are written to NWB.
    write_scaled: bool (optional, defaults to True)
        If True, writes the scaled traces (return_scaled=True)
    compression: str (optional, defaults to "gzip")
        Type of compression to use. Valid types are "gzip" and "lzf".
        Set to None to disable all compression.
    compression_opts: int (optional, defaults to 4)
        Only applies to compression="gzip". Controls the level of the GZIP.
    iterator_type: str (optional, defaults to 'v2')
        The type of DataChunkIterator to use.
        'v1' is the original DataChunkIterator of the hdmf data_utils.
        'v2' is the locally developed RecordingExtractorDataChunkIterator, which offers full control over chunking.
    iterator_opts: dict (optional)
        Dictionary of options for the RecordingExtractorDataChunkIterator (iterator_type='v2').
        Valid options are
            buffer_gb : float (optional, defaults to 1 GB)
                Recommended to be as much free RAM as available). Automatically calculates suitable buffer shape.
            chunk_mb : float (optional, defaults to 1 MB)
                Should be below 1 MB. Automatically calculates suitable chunk shape.
        If manual specification of buffer_shape and chunk_shape are desired, these may be specified as well.
    """
    if nwbfile is not None:
        assert isinstance(nwbfile, pynwb.NWBFile), "'nwbfile' should be of type pynwb.NWBFile"
    assert (
        distutils.version.LooseVersion(pynwb.__version__) >= "1.3.3"
    ), "'write_recording' not supported for version < 1.3.3. Run pip install --upgrade pynwb"

    assert save_path is None or nwbfile is None, "Either pass a save_path location, or nwbfile object, but not both!"

    if hasattr(recording, "nwb_metadata"):
        metadata = dict_deep_update(recording.nwb_metadata, metadata)
    elif metadata is None:
        metadata = get_nwb_metadata(recording=recording)
    if nwbfile is None:
        if Path(save_path).is_file() and not overwrite:
            read_mode = "r+"
        else:
            read_mode = "w"
        with pynwb.NWBHDF5IO(str(save_path), mode=read_mode) as io:
            if read_mode == "r+":
                nwbfile = io.read()
            else:
                nwbfile = make_nwbfile_from_metadata(metadata=metadata)
            add_all_to_nwbfile(
                recording=recording,
                nwbfile=nwbfile,
                metadata=metadata,
                starting_time=starting_time,
                use_times=use_times,
                write_as=write_as,
                es_key=es_key,
                write_scaled=write_scaled,
                compression=compression,
                compression_opts=compression_opts,
                iterator_type=iterator_type,
                iterator_opts=iterator_opts,
                write_electrical_series=write_electrical_series,
            )
            io.write(nwbfile)
    else:
        add_all_to_nwbfile(
            recording=recording,
            nwbfile=nwbfile,
            starting_time=starting_time,
            use_times=use_times,
            metadata=metadata,
            write_as=write_as,
            es_key=es_key,
            write_scaled=write_scaled,
            compression=compression,
            compression_opts=compression_opts,
            iterator_type=iterator_type,
            iterator_opts=iterator_opts,
            write_electrical_series=write_electrical_series,
        )
    return nwbfile


def get_nspikes(units_table: pynwb.misc.Units, unit_id: int):
    """Return the number of spikes for chosen unit."""
    ids = np.array(units_table.id[:])
    indexes = np.where(ids == unit_id)[0]
    if not len(indexes):
        raise ValueError(f"{unit_id} is an invalid unit_id. Valid ids: {ids}.")
    index = indexes[0]
    if index == 0:
        return units_table["spike_times_index"].data[index]
    else:
        return units_table["spike_times_index"].data[index] - units_table["spike_times_index"].data[index - 1]


def add_units(
    sorting: SpikeInterfaceSorting,
    nwbfile: pynwb.NWBFile,
    property_descriptions: Optional[dict] = None,
    skip_properties: Optional[List[str]] = None,
    skip_features: Optional[List[str]] = None,
    use_times: bool = True,
    write_as: str = "units",
    units_name: str = "units",
    units_description: str = "Autogenerated by nwb_conversion_tools.",
):
    """
    Primary method for writing a SortingExtractor object to an NWBFile.

    Parameters
    ----------
    sorting: SpikeInterfaceSorting
    save_path: PathType
        Required if an nwbfile is not passed. The location where the NWBFile either exists, or will be written.
    overwrite: bool
        If using save_path, whether or not to overwrite the NWBFile if it already exists.
    nwbfile: NWBFile
        Required if a save_path is not specified. If passed, this function
        will fill the relevant fields within the nwbfile. E.g., calling
        spikeextractors.NwbRecordingExtractor.write_recording(
            my_recording_extractor, my_nwbfile
        )
        will result in the appropriate changes to the my_nwbfile object.
    property_descriptions: dict
        For each key in this dictionary which matches the name of a unit
        property in sorting, adds the value as a description to that
        custom unit column.
    skip_properties: list of str
        Each string in this list that matches a unit property will not be written to the NWBFile.
    skip_features: list of str
        Each string in this list that matches a spike feature will not be written to the NWBFile.
    use_times: bool (optional, defaults to False)
        If True, the times are saved to the nwb file using sorting.frame_to_time(). If False (default),
        the sampling rate is used.
    write_as: str (optional, defaults to 'units')
        How to save the units table in the nwb file. Options:
        - 'units' will save it to the official NWBFile.Units position; recommended only for the final form of the data.
        - 'processing' will save it to the processing module to serve as a historical provenance for the official table.
    units_name : str (optional, defaults to 'units')
        The name of the units table. If write_as=='units', then units_name must also be 'units'.
    units_description : str (optional)
        Text description of the sorting table; recommended to included parameters of sorting method, curation, etc.
    """
    if isinstance(sorting, SortingExtractor):
        sampling_frequency = sorting.get_sampling_frequency()
        if sampling_frequency is None:
            raise ValueError("Writing a SortingExtractor to an NWBFile requires a known sampling frequency!")
        checked_sorting = OldToNewSorting(oldapi_sorting_extractor=sorting)
    else:
        checked_sorting = sorting
    unit_ids = checked_sorting.get_unit_ids()
    sampling_frequency = checked_sorting.get_sampling_frequency()
    if sampling_frequency is None:
        raise ValueError("Writing a SortingExtractor to an NWBFile requires a known sampling frequency!")
    assert write_as in [
        "units",
        "processing",
    ], f"Argument write_as ({write_as}) should be one of 'units' or 'processing'!"
    if write_as == "units":
        assert units_name == "units", "When writing to the nwbfile.units table, the name of the table must be 'units'!"
    default_descriptions = dict(
        isi_violation="Quality metric that measures the ISI violation ratio as a proxy for the purity of the unit.",
        firing_rate="Number of spikes per unit of time.",
        template="The extracellular average waveform.",
        max_channel="The recording channel id with the largest amplitude.",
        halfwidth="The full-width half maximum of the negative peak computed on the maximum channel.",
        peak_to_valley="The duration between the negative and the positive peaks computed on the maximum channel.",
        snr="The signal-to-noise ratio of the unit.",
        quality="Quality of the unit as defined by phy (good, mua, noise).",
        spike_amplitude="Average amplitude of peaks detected on the channel.",
        spike_rate="Average rate of peaks detected on the channel.",
    )
    if property_descriptions is None:
        property_descriptions = dict(default_descriptions)
    else:
        property_descriptions = dict(default_descriptions, **property_descriptions)
    if skip_properties is None:
        skip_properties = []
    units_table = pynwb.misc.Units(name=units_name, description=units_description)

    all_properties = checked_sorting.get_property_keys()
    write_properties = set(all_properties) - set(skip_properties)
    for property_name in write_properties:
        if property_name not in property_descriptions:
            warnings.warn(
                f"Description for property {property_name} not found in property_descriptions. "
                "Setting description to 'no description'"
            )
    aggregated_unit_properties = defaultdict()
    for property_name in write_properties:
        unit_col_args = dict(
            name=property_name, description=property_descriptions.get(property_name, "No description.")
        )
        if property_name in ["max_channel", "max_electrode"] and nwbfile.electrodes is not None:
            unit_col_args.update(table=nwbfile.electrodes)
        units_table.add_column(**unit_col_args)
        aggregated_unit_properties[property_name] = checked_sorting.get_property(key=property_name)
    for i, unit_id in enumerate(unit_ids):
        if use_times:
            spkt = checked_sorting.get_unit_spike_train(unit_id=unit_id, return_times=True)
        else:
            spkt = checked_sorting.get_unit_spike_train(unit_id=unit_id) / checked_sorting.get_sampling_frequency()
        kwargs = {key: val[i] for key, val in aggregated_unit_properties.items()}

        units_table.add_unit(id=int(unit_id), spike_times=spkt, **kwargs)
    if isinstance(sorting, SortingExtractor):
        all_features = set()
        for unit_id in unit_ids:
            all_features.update(sorting.get_unit_spike_feature_names(unit_id))
        if skip_features is None:
            skip_features = []
        # Check that multidimensional features have the same shape across units
        feature_shapes = dict()
        for feature_name in all_features:
            shapes = []
            for unit_id in unit_ids:
                if feature_name in sorting.get_unit_spike_feature_names(unit_id=unit_id):
                    feat_value = sorting.get_unit_spike_features(unit_id=unit_id, feature_name=feature_name)
                    if isinstance(feat_value[0], (int, np.integer, float, str, bool)):
                        break
                    elif isinstance(feat_value[0], (list, np.ndarray)):  # multidimensional features
                        if np.array(feat_value).ndim > 1:
                            shapes.append(np.array(feat_value).shape)
                            feature_shapes[feature_name] = shapes
                    elif isinstance(feat_value[0], dict):
                        print(f"Skipping feature '{feature_name}' because dictionaries are not supported.")
                        skip_features.append(feature_name)
                        break
                else:
                    print(f"Skipping feature '{feature_name}' because not share across all units.")
                    skip_features.append(feature_name)
                    break
        nspikes = {k: get_nspikes(units_table, int(k)) for k in unit_ids}
        for feature_name in feature_shapes.keys():
            # skip first dimension (num_spikes) when comparing feature shape
            if not np.all([elem[1:] == feature_shapes[feature_name][0][1:] for elem in feature_shapes[feature_name]]):
                print(f"Skipping feature '{feature_name}' because it has variable size across units.")
                skip_features.append(feature_name)
        for feature_name in set(all_features) - set(skip_features):
            values = []
            if not feature_name.endswith("_idxs"):
                for unit_id in sorting.get_unit_ids():
                    feat_vals = sorting.get_unit_spike_features(unit_id=unit_id, feature_name=feature_name)
                    if len(feat_vals) < nspikes[unit_id]:
                        skip_features.append(feature_name)
                        print(f"Skipping feature '{feature_name}' because it is not defined for all spikes.")
                        break
                    else:
                        all_feat_vals = feat_vals
                    values.append(all_feat_vals)
                flatten_vals = [item for sublist in values for item in sublist]
                nspks_list = [sp for sp in nspikes.values()]
                spikes_index = np.cumsum(nspks_list).astype("int64")
                if feature_name in units_table:  # If property already exists, skip it
                    warnings.warn(f"Feature {feature_name} already present in units table, skipping it")
                    continue
                set_dynamic_table_property(
                    dynamic_table=units_table,
                    row_ids=[int(k) for k in unit_ids],
                    property_name=feature_name,
                    values=flatten_vals,
                    index=spikes_index,
                )
    if write_as == "units":
        if nwbfile.units is None:
            nwbfile.units = units_table
        else:
            warnings.warn("The nwbfile already contains units. These units will not be over-written.")
    elif write_as == "processing":
        ecephys_mod = get_module(
            nwbfile=nwbfile,
            name="ecephys",
            description="Intermediate data from extracellular electrophysiology recordings, e.g., LFP.",
        )
        ecephys_mod.add(units_table)


def write_sorting(
    sorting: SortingExtractor,
    save_path: OptionalFilePathType = None,
    overwrite: bool = False,
    nwbfile: Optional[pynwb.NWBFile] = None,
    property_descriptions: Optional[dict] = None,
    skip_properties: Optional[List[str]] = None,
    skip_features: Optional[List[str]] = None,
    use_times: bool = True,
    metadata: Optional[dict] = None,
    write_as: str = "units",
    units_name: str = "units",
    units_description: str = "Autogenerated by nwb_conversion_tools.",
):
    """
    Primary method for writing a SortingExtractor object to an NWBFile.

    Parameters
    ----------
    sorting: SortingExtractor
    save_path: OptionalFilePathType
        Required if an nwbfile is not passed. The location where the NWBFile either exists, or will be written.
    overwrite: bool
        If using save_path, whether or not to overwrite the NWBFile if it already exists.
    nwbfile: NWBFile
        If passed, this function will fill the relevant fields within the NWBFile object.
        E.g., calling
            write_sorting(recording=my_recording_extractor, nwbfile=my_nwbfile)
        will result in the appropriate changes to the my_nwbfile object.
        If neither 'save_path' nor 'nwbfile' are specified, an NWBFile object will be automatically generated
        and returned by the function.
    property_descriptions: dict
        For each key in this dictionary which matches the name of a unit
        property in sorting, adds the value as a description to that
        custom unit column.
    skip_properties: list of str
        Each string in this list that matches a unit property will not be written to the NWBFile.
    skip_features: list of str
        Each string in this list that matches a spike feature will not be written to the NWBFile.
    use_times: bool (optional, defaults to False)
        If True, the times are saved to the nwb file using sorting.frame_to_time(). If False (default),
        the sampling rate is used.
    metadata: dict
        Information for constructing the nwb file (optional).
        Only used if no nwbfile exists at the save_path, and no nwbfile was directly passed.
    write_as: str (optional, defaults to 'units')
        How to save the units table in the nwb file. Options:
        - 'units' will save it to the official NWBFile.Units position; recommended only for the final form of the data.
        - 'processing' will save it to the processing module to serve as a historical provenance for the official table.
    units_name : str (optional, defaults to 'units')
        The name of the units table. If write_as=='units', then units_name must also be 'units'.
    units_description : str (optional)
        Text description of the sorting table; recommended to included parameters of sorting method, curation, etc.
    """
    assert save_path is None or nwbfile is None, "Either pass a save_path location, or nwbfile object, but not both!"
    if nwbfile is not None:
        assert isinstance(nwbfile, pynwb.NWBFile), "'nwbfile' should be a pynwb.NWBFile object!"
    assert write_as in [
        "units",
        "processing",
    ], f"Argument write_as ({write_as}) should be one of 'units' or 'processing'!"
    if write_as == "units":
        assert units_name == "units", "When writing to the nwbfile.units table, the name of the table must be 'units'!"
    if metadata is None:
        metadata = dict()
    if nwbfile is None:
        if Path(save_path).is_file() and not overwrite:
            read_mode = "r+"
        else:
            read_mode = "w"
        with pynwb.NWBHDF5IO(str(save_path), mode=read_mode) as io:
            if read_mode == "r+":
                nwbfile = io.read()
            else:
                nwbfile = make_nwbfile_from_metadata(metadata=metadata)
            add_units(
                sorting=sorting,
                nwbfile=nwbfile,
                property_descriptions=property_descriptions,
                skip_properties=skip_properties,
                skip_features=skip_features,
                use_times=use_times,
                write_as=write_as,
                units_name=units_name,
                units_description=units_description,
            )
            io.write(nwbfile)
    else:
        add_units(
            sorting=sorting,
            nwbfile=nwbfile,
            property_descriptions=property_descriptions,
            skip_properties=skip_properties,
            skip_features=skip_features,
            use_times=use_times,
            write_as=write_as,
            units_name=units_name,
            units_description=units_description,
        )
    return nwbfile
