import distutils.version
from abc import ABC, abstractmethod

import numpy as np
import pynwb

from .basenwbephyswriter import BaseNwbEphysWriter


class BaseSINwbEphysWriter(BaseNwbEphysWriter, ABC):
    def __init__(self, object_to_write, stub, stub_channels):
        self.recording, self.sorting, self.waveforms, self.event = None, None, None, None
        BaseNwbEphysWriter.__init__(self, object_to_write, stub=stub, stub_channels=stub_channels)

    def _get_sampling_frequency(self):
        return self.recording.get_sampling_frequency()

    def _get_channel_ids(self):
        ids = self.recording.get_channel_ids()
        if isinstance(ids[0], str) and not ids[0].isdigit():
            return np.arange(len(ids))
        else:
            return np.array(ids, dtype="int")

    def _get_gains(self):
        return self.recording.get_channel_gains()

    def _get_offsets(self):
        return self.recording.get_channel_offsets()

    def _get_unit_sampling_frequency(self):
        return self.sorting.get_sampling_frequency()

    def _get_unit_ids(self):
        return np.array(self.sorting.get_unit_ids(), dtype="int")

    def _check_valid_property(self, prop_values):
        if not isinstance(prop_values[0], tuple(self.dt_column_defaults)):
            return
        if isinstance(prop_values[0], np.ndarray):
            shapes = [value.shape[1:] if len(value.shape) > 1 else 1 for value in prop_values]
            if np.all([shape == shapes[0] for shape in shapes]):
                return prop_values
        else:
            return prop_values

    def add_recording(self, segment_index=0):
        assert (
            distutils.version.LooseVersion(pynwb.__version__) >= "1.3.3"
        ), "'write_recording' not supported for version < 1.3.3. Run pip install --upgrade pynwb"

        self.add_devices()
        self.add_electrode_groups()
        self.add_electrodes()
        if self._conversion_ops["write_electrical_series"]:
            self.add_electrical_series(segment_index=segment_index)

    def add_sorting(self):
        self.add_units()

    def add_waveforms(self):
        if self.waveforms is not None:
            self.add_unit_waveforms()

    def add_to_nwb(self, nwbfile: pynwb.NWBFile, metadata=None, **kwargs):
        assert nwbfile is not None and isinstance(nwbfile, pynwb.NWBFile), "Instantiate an NWBFile and pass as argument"
        self.metadata = metadata if metadata is not None else dict()
        self.nwbfile = nwbfile
        self._conversion_ops = kwargs
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
