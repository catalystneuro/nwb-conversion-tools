import pynwb
import numpy as np
import uuid
from datetime import datetime
from copy import deepcopy
import warnings
from .json_schema import dict_deep_update
from collections import Iterable


class BaseNwbEphysWriter:
    def __init__(self, object_to_write, nwbfile=None, metadata=None, **kwargs):
        self.object_to_write = object_to_write
        assert (nwbfile is not None and isinstance(nwbfile, pynwb.NWBFile)),\
                "Instantiate an NWBFile and pass as argument"
        self.metadata = metadata if metadata is not None else dict()
        self.nwbfile = nwbfile
        self._kwargs = kwargs

    @staticmethod
    def get_kwargs_description(self):
        raise NotImplementedError

    def add_to_nwb(self):
        raise NotImplementedError

    def add_recording(self):
        raise NotImplementedError

    def add_sorting(self):
        raise NotImplementedError

    def add_epochs(self):
        raise NotImplementedError

    def add_waveforms(self):
        raise NotImplementedError

    def add_devices(self):
        """
        Auxiliary static method for nwbextractor.

        Adds device information to nwbfile object.
        Will always ensure nwbfile has at least one device, but multiple
        devices within the metadata list will also be created.

        Missing keys in an element of metadata['Ecephys']['Device'] will be auto-populated with defaults.
        """
        if self.nwbfile is not None:
            assert isinstance(self.nwbfile, pynwb.NWBFile), "'nwbfile' should be of type pynwb.NWBFile"

        # Default Device metadata
        defaults = dict(name="Device", description="Ecephys probe. Automatically generated.")

        if "Ecephys" not in self.metadata:
            self.metadata["Ecephys"] = dict()

        if "Device" not in self.metadata["Ecephys"]:
            self.metadata["Ecephys"]["Device"] = [defaults]

        for dev in self.metadata["Ecephys"]["Device"]:
            if dev.get("name", defaults["name"]) not in self.nwbfile.devices:
                self.nwbfile.create_device(**dict(defaults, **dev))

        print(self.nwbfile.devices)

    def add_electrodes(self):
        raise NotImplementedError

    def add_electrode_groups(self, channel_groups_unique:Iterable=None):
        """
        Auxiliary method to write electrode groups.

        Adds electrode group information to nwbfile object.
        Will always ensure nwbfile has at least one electrode group.
        Will auto-generate a linked device if the specified name does not exist in the nwbfile.

        Missing keys in an element of metadata['Ecephys']['ElectrodeGroup'] will be auto-populated with defaults.

        Group names set by RecordingExtractor channel properties will also be included with passed metadata,
        but will only use default description and location.
        """
        if len(self.nwbfile.devices) == 0:
            warnings.warn("When adding ElectrodeGroup, no Devices were found on nwbfile. Creating a Device now...")
            self.add_devices()

        if "Ecephys" not in self.metadata:
            self.metadata["Ecephys"] = dict()

        if channel_groups_unique is None:
            channel_groups_unique = np.array([0], dtype="int")

        defaults = [
            dict(
                name=str(group_id),
                description="no description",
                location="unknown",
                device=[i.name for i in self.nwbfile.devices.values()][0],
            )
            for group_id in channel_groups_unique
        ]

        if "ElectrodeGroup" not in self.metadata["Ecephys"]:
            self.metadata["Ecephys"]["ElectrodeGroup"] = defaults

        assert all(
            [isinstance(x, dict) for x in self.metadata["Ecephys"]["ElectrodeGroup"]]
        ), "Expected metadata['Ecephys']['ElectrodeGroup'] to be a list of dictionaries!"

        for grp in self.metadata["Ecephys"]["ElectrodeGroup"]:
            if grp.get("name", defaults[0]["name"]) not in self.nwbfile.electrode_groups:
                device_name = grp.get("device", defaults[0]["device"])
                if device_name not in self.nwbfile.devices:
                    self.metadata["Ecephys"]["Device"].append(dict(name=device_name))
                    self.add_devices()
                    warnings.warn(
                        f"Device '{device_name}' not detected in "
                        "attempted link to electrode group! Automatically generating."
                    )
                electrode_group_kwargs = dict(defaults[0], **grp)
                electrode_group_kwargs.update(device=self.nwbfile.devices[device_name])
                self.nwbfile.create_electrode_group(**electrode_group_kwargs)

    def add_electrical_series(self):
        raise NotImplementedError

    def add_units(self):
        raise NotImplementedError

    def add_epochs(self):
        raise NotImplementedError


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
