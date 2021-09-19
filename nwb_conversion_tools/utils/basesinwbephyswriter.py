import distutils.version
from abc import ABC

import numpy as np
import pynwb

from .basenwbephyswriter import BaseNwbEphysWriter


class BaseSINwbEphysWriter(BaseNwbEphysWriter, ABC):
    def __init__(
            self,
            object_to_write,
            nwbfile: pynwb.NWBFile = None,
            metadata: dict = None,
            **kwargs,
    ):
        self.recording, self.sorting, self.waveforms, self.event = None, None, None, None
        BaseNwbEphysWriter.__init__(self, object_to_write, nwbfile=nwbfile, metadata=metadata, **kwargs)

    def add_electrode_groups(self):
        channel_groups = self.recording.get_channel_groups()
        if channel_groups is None:
            channel_groups_unique = np.array([0], dtype="int")
        else:
            channel_groups_unique = np.unique(channel_groups)
        super(BaseNwbEphysWriter)._add_electrode_groups(channel_groups_unique=channel_groups_unique)

    def _get_sampling_frequency(self):
        if self.recording is not None:
            return self.recording.get_sampling_frequency()

    def _get_channel_ids(self):
        if self.recording is not None:
            return self.recording.get_channel_ids()

    def _get_unit_sampling_frequency(self):
        if self.sorting is not None:
            return self.sorting.get_sampling_frequency()

    def _get_unit_ids(self):
        if self.sorting is not None:
            return self.sorting.get_unit_ids()

    def _check_valid_property(self, prop_values):
        if not isinstance(prop_values[0], tuple(self.dt_column_defaults)):
            return
        if isinstance(prop_values[0], np.ndarray):
            shapes = [value.shape[1:] for value in prop_values]
            if np.all([shape == shape[0] for shape in shapes]):
                return prop_values

    def add_recording(self):
        assert (
                distutils.version.LooseVersion(pynwb.__version__) >= "1.3.3"
        ), "'write_recording' not supported for version < 1.3.3. Run pip install --upgrade pynwb"

        self.add_devices()
        self.add_electrode_groups()
        self.add_electrodes()
        if self._conversion_ops["write_electrical_series"]:
            self.add_electrical_series()

    def add_sorting(self):
        self.add_units()

    def add_waveforms(self):
        if self.waveforms is not None:
            self.add_units_waveforms()

    def add_to_nwb(self):
        if self.waveforms is not None:
            self.add_recording()
            self.add_sorting()
            self.add_waveforms()
            return
        if self.recording is not None:
            self.add_recording()
            return
        if self.sorting is not None:
            self.add_sorting()
            return
        if self.event is not None:
            self.add_epochs()
            return
