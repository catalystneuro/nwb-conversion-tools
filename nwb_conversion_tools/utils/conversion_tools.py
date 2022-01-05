"""Authors: Cody Baker, Alessio Buccino."""
import numpy as np
import uuid
from datetime import datetime
from warnings import warn
from numbers import Real

from pynwb import NWBFile
from pynwb.file import Subject

from .json_schema import dict_deep_update

DynamicTableSupportedDtypes = {
    list: [], np.ndarray: np.array(np.nan), str: "", Real: np.nan}


def get_module(nwbfile: NWBFile, name: str, description: str = None):
    """Check if processing module exists. If not, create it. Then return module."""
    if name in nwbfile.processing:
        if description is not None and nwbfile.modules[name].description != description:
            warn(
                "Custom description given to get_module does not match existing module description! "
                "Ignoring custom description."
            )
        return nwbfile.processing[name]
    else:
        if description is None:
            description = "No description."
        return nwbfile.create_processing_module(name=name, description=description)


def get_default_nwbfile_metadata():
    """
    Return structure with defaulted metadata values required for a NWBFile.

    These standard defaults are
        metadata["NWBFile"]["session_description"] = "no description"
        metadata["NWBFile"]["session_description"] = datetime(1970, 1, 1)

    Proper conversions should override these fields prior to calling NWBConverter.run_conversion()
    """
    metadata = dict(
        NWBFile=dict(
            session_description="no description",
            session_start_time=datetime(1970, 1, 1).isoformat(),
            identifier=str(uuid.uuid4()),
        )
    )
    return metadata


def make_nwbfile_from_metadata(metadata: dict):
    """Make NWBFile from available metadata."""
    metadata = dict_deep_update(get_default_nwbfile_metadata(), metadata)
    nwbfile_kwargs = metadata["NWBFile"]
    if "Subject" in metadata:
        # convert ISO 8601 string to datetime
        if "date_of_birth" in metadata["Subject"] and isinstance(metadata["Subject"]["date_of_birth"], str):
            metadata["Subject"]["date_of_birth"] = datetime.fromisoformat(metadata["Subject"]["date_of_birth"])
        nwbfile_kwargs.update(subject=Subject(**metadata["Subject"]))
    # convert ISO 8601 string to datetime
    if isinstance(nwbfile_kwargs.get("session_start_time", None), str):
        nwbfile_kwargs["session_start_time"] = datetime.fromisoformat(metadata["NWBFile"]["session_start_time"])
    return NWBFile(**nwbfile_kwargs)


def check_regular_timestamps(ts):
    """Check whether rate should be used instead of timestamps."""
    time_tol_decimals = 9
    uniq_diff_ts = np.unique(np.diff(ts).round(decimals=time_tol_decimals))
    return len(uniq_diff_ts) == 1


def add_properties_to_dynamictable(nwbfile, dt_name, prop_dict, defaults):
    if dt_name == "electrodes":
        add_method = nwbfile.add_electrode_column
        dt = nwbfile.electrodes
    else:
        add_method = nwbfile.add_unit_column
        dt = nwbfile.units

    if dt is None:
        for prop_name, prop_args in prop_dict.items():
            if prop_name not in defaults:
                add_dict = dict(prop_args)
                _ = add_dict.pop("data")
                add_method(prop_name, **add_dict)
    else:
        reshape_dynamictable(dt, prop_dict, defaults)


def reshape_dynamictable(dt, prop_dict, defaults):
    """
    Prepares an already existing dynamic table to take custom properties using the add_functions.
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
            default_datatype = [proptype for proptype in property_default_data if isinstance(
                samp_data, proptype)][0]
            defaults_updated.update(
                {colname: property_default_data[default_datatype]})
    # for all columns that are new for the given RX, they will
    for name, des_dict in prop_dict.items():
        des_args = dict(des_dict)
        if name not in defaults_updated:
            # build default junk values for data and add that as column directly later:
            default_datatype_list = [
                proptype for proptype in property_default_data if isinstance(des_dict["data"][0], proptype)
            ][0]
            des_args["data"] = [
                property_default_data[default_datatype_list]] * len(dt.id)
            dt.add_column(name, **des_args)
