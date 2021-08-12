import pynwb
import numpy as np
import uuid
from datetime import datetime
from copy import deepcopy


class BaseNwbEphysWriter:
    def __init__(self, object_to_write, nwbfile, metadata=None, **kwargs):
        self.object_to_write = object_to_write
        self.metadata = metadata
        self.nwbfile = nwbfile
        assert isinstance(self.nwbfile, pynwb.NWBFile), "'nwbfile' should be of type pynwb.NWBFile"
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

    def get_nwb_metadata(self):
        raise NotImplementedError

    def add_devices(self, metadata=None):
        """
        Auxiliary static method for nwbextractor.

        Adds device information to nwbfile object.
        Will always ensure nwbfile has at least one device, but multiple
        devices within the metadata list will also be created.

        Missing keys in an element of metadata['Ecephys']['Device'] will be auto-populated with defaults.
        """
        # Default Device metadata
        defaults = dict(name="Device", description="Ecephys probe. Automatically generated.")

        if self.metadata is None:
            self.metadata = dict()

        if metadata is None:
            metadata = deepcopy(self.metadata)

        if "Ecephys" not in metadata:
            metadata["Ecephys"] = dict()

        if "Device" not in metadata["Ecephys"]:
            metadata["Ecephys"]["Device"] = [defaults]

        for dev in metadata["Ecephys"]["Device"]:
            if dev.get("name", defaults["name"]) not in self.nwbfile.devices:
                self.nwbfile.create_device(**dict(defaults, **dev))

    def add_electrodes(self):
        raise NotImplementedError

    def add_electrode_groups(self):
        raise NotImplementedError

    def add_electrical_series(self):
        raise NotImplementedError

    def add_units(self):
        raise NotImplementedError

    def add_epochs(self):
        raise NotImplementedError
