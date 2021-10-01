import numpy as np
import pynwb
from typing import Union
from pathlib import Path
from .json_schema import get_base_schema
from numbers import Real

PathType = Union[str, Path, None]
ArrayType = Union[list, np.ndarray]
DynamicTableSupportedDtypes = {list: [], np.ndarray: np.array(np.nan), str: "", Real: np.nan}


def list_get(li: list, idx: int, default):
    """Safe index retrieval from list."""
    try:
        return li[idx]
    except IndexError:
        return default


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


def default_return(value):
    def return_dec(func):
        def wrapper(*args, **kwargs):
            try:
                out = func(*args, **kwargs)
                if out is None:
                    return value
                else:
                    return out
            except Exception as e:
                if "NoneType" in str(e):
                    return value
                else:
                    return e

        return wrapper

    return return_dec


def check_module(nwbfile, name: str, description: str = None):
    """
    Check if processing module exists. If not, create it. Then return module.

    Parameters
    ----------
    nwbfile: pynwb.NWBFile
    name: str
    description: str | None (optional)

    Returns
    -------
    pynwb.module
    """
    assert isinstance(nwbfile, pynwb.NWBFile), "'nwbfile' should be of type pynwb.NWBFile"
    if name in nwbfile.modules:
        return nwbfile.modules[name]
    else:
        if description is None:
            description = name
        return nwbfile.create_processing_module(name, description)


def default_export_ops():
    return dict(
        use_times=False,
        write_as="raw",
        es_key="ElectricalSeries_raw",
        buffer_gb=None,
        buffer_shape=None,
        chunk_mb=None,
        iterator_type="v2",
        chunk_shape=None,
        write_scaled=False,
        compression="gzip",
        compression_opts=4,
        iterate=True,
        skip_unit_properties=[],
        skip_unit_features=[],
        skip_electrode_properties=[],
        unit_property_descriptions=dict(),
        write_electrical_series=True,
        stub=False,
        overwrite=True,
        stub_channels=[],
    )


def default_export_ops_schema():
    schema = get_base_schema()
    schema["required"] = []
    schema["properties"] = dict(
        use_times=dict(type="boolean"),
        write_as=dict(type="string", enum=["raw", "lfp", "processed"]),
        es_key=dict(type="string"),
        buffer_gb=dict(type=["null", "number"]),
        buffer_shape=dict(type=["null", "array"]),
        chunk_mb=dict(type=["null", "number"]),
        iterator_type=dict(type="string", enum=["v2", "v1"]),
        chunk_shape=dict(type=["null", "array"]),
        write_scaled=dict(type="boolean"),
        compression=dict(type="string", enum=["gzip", "lzf"]),
        compression_opts=dict(type="number", minimun=0, maximum=9),
        iterate=dict(type="boolean"),
        skip_unit_properties=dict(type="array", items=dict(type="string")),
        skip_unit_features=dict(type="array", items=dict(type="string")),
        skip_electrode_properties=dict(type="array", items=dict(type="string")),
        unit_property_descriptions=dict(type="object"),
        write_electrical_series=dict(type="boolean"),
        stub=dict(type="boolean"),
        overwrite=dict(type="boolean"),
        stub_channels=dict(type="array", items=dict(type="integer")),
    )
    return schema


_default_sorting_property_descriptions = dict(
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
