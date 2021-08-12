import uuid
from datetime import datetime
import warnings
import numpy as np
import distutils.version
from pathlib import Path
from typing import Union, Optional, List
from warnings import warn
import psutil
from collections import defaultdict
from copy import deepcopy

import pynwb
from numbers import Real
from hdmf.data_utils import DataChunkIterator
from hdmf.backends.hdf5.h5_utils import H5DataIO
from .json_schema import dict_deep_update
from .basenwbephyswriter import BaseNwbEphysWriter
from .common_writer_tools import ArrayType, PathType, set_dynamic_table_property, check_module, list_get


class BaseSINwbEphysWriter(BaseNwbEphysWriter):
    def __init__(
        self,
        object_to_write,
        nwb_file_path: PathType = None,
        nwbfile: pynwb.NWBFile = None,
        metadata: dict = None,
        **kwargs,
    ):
        # exclude properties
        if "exclude_properties" in kwargs:
            self._exclude_properties = kwargs["exclude_properties"]
        else:
            self._exclude_properties = []
        if "exclude_features" in kwargs:
            self._exclude_features = kwargs["exclude_features"]
        else:
            self._exclude_features = []

        self.recording, self.sorting, self.waveforms, self.event = None, None, None, None
        BaseNwbEphysWriter.__init__(
            self, object_to_write, nwb_file_path=nwb_file_path, nwbfile=nwbfile, metadata=metadata, **kwargs
        )

    def get_nwb_metadata(self):
        metadata = super(BaseNwbEphysWriter).get_nwb_metadata()
        self.metadata["Ecephys"].update(
            ElectrodeGroup=[
                dict(name=str(gn), description="no description", location="unknown", device="Device")
                for gn in np.unique(self.recording.get_channel_groups())
            ]
        )

    def add_electrode_groups(self, metadata=None):
        """
        Auxiliary method to write electrode groups.

        Adds electrode group information to nwbfile object.
        Will always ensure nwbfile has at least one electrode group.
        Will auto-generate a linked device if the specified name does not exist in the nwbfile.

        Missing keys in an element of metadata['Ecephys']['ElectrodeGroup'] will be auto-populated with defaults.

        Group names set by RecordingExtractor channel properties will also be included with passed metadata,
        but will only use default description and location.
        """
        if self.nwbfile is not None:
            assert isinstance(self.nwbfile, pynwb.NWBFile), "'nwbfile' should be of type pynwb.NWBFile"

        if len(self.nwbfile.devices) == 0:
            warnings.warn("When adding ElectrodeGroup, no Devices were found on nwbfile. Creating a Device now...")
            self.add_devices()

        if self.metadata is None:
            self.metadata = dict()

        if metadata is None:
            metadata = deepcopy(self.metadata)

        if "Ecephys" not in metadata:
            metadata["Ecephys"] = dict()

        channel_groups = self.recording.get_channel_groups()
        if channel_groups is None:
            channel_groups_unique = np.array([0], dtype="int")
        else:
            channel_groups_unique = np.unique(channel_groups)

        defaults = [
            dict(
                name=str(group_id),
                description="no description",
                location="unknown",
                device=[i.name for i in self.nwbfile.devices.values()][0],
            )
            for group_id in channel_groups_unique
        ]

        if "ElectrodeGroup" not in metadata["Ecephys"]:
            metadata["Ecephys"]["ElectrodeGroup"] = defaults

        assert all(
            [isinstance(x, dict) for x in metadata["Ecephys"]["ElectrodeGroup"]]
        ), "Expected metadata['Ecephys']['ElectrodeGroup'] to be a list of dictionaries!"

        for grp in metadata["Ecephys"]["ElectrodeGroup"]:
            if grp.get("name", defaults[0]["name"]) not in self.nwbfile.electrode_groups:
                device_name = grp.get("device", defaults[0]["device"])
                if device_name not in self.nwbfile.devices:
                    metadata = dict(Ecephys=dict(Device=[dict(name=device_name)]))
                    self.add_devices(metadata)
                    warnings.warn(
                        f"Device '{device_name}' not detected in "
                        "attempted link to electrode group! Automatically generating."
                    )
                electrode_group_kwargs = dict(defaults[0], **grp)
                electrode_group_kwargs.update(device=self.nwbfile.devices[device_name])
                self.nwbfile.create_electrode_group(**electrode_group_kwargs)

        if not self.nwbfile.electrode_groups:
            device_name = list(self.nwbfile.devices.keys())[0]
            device = self.nwbfile.devices[device_name]
            if len(self.nwbfile.devices) > 1:
                warnings.warn(
                    "More than one device found when adding electrode group "
                    f"via channel properties: using device '{device_name}'. To use a "
                    "different device, indicate it the metadata argument."
                )

            electrode_group_kwargs = dict(defaults[0])
            electrode_group_kwargs.update(device=device)
            for grp_name in channel_groups_unique.tolist():
                electrode_group_kwargs.update(name=str(grp_name))
                self.nwbfile.create_electrode_group(**electrode_group_kwargs)
