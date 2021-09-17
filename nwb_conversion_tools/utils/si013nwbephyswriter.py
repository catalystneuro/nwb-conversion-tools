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
from .basesinwbephyswriter import BaseSINwbEphysWriter
from .common_writer_tools import ArrayType, PathType, set_dynamic_table_property, check_module, list_get

try:
    import spikeextractors as se

    HAVE_SI013 = True
except ImportError:
    HAVE_SI013 = False


class SI013NwbEphysWriter(BaseSINwbEphysWriter):
    """
    Class to write RecordingExtractor and SortingExtractor object from SI<=0.13 to NWB

    Parameters
    ----------
    object_to_write: se.RecordingExtractor or se.SortingExtractor
    nwb_file_path: Path type
    nwbfile: pynwb.NWBFile or None
    metadata: dict or None
    **kwargs: list kwargs and meaning
    """

    def __init__(
        self,
        object_to_write: Union[se.RecordingExtractor, se.SortingExtractor],
        nwbfile: pynwb.NWBFile = None,
        metadata: dict = None,
        **kwargs,
    ):
        assert HAVE_SI013, "spikeextractors 0.13 version not installed"
        BaseSINwbEphysWriter.__init__(self, object_to_write, nwbfile=nwbfile, metadata=metadata, **kwargs)
        if isinstance(self.object_to_write, se.RecordingExtractor):
            self.recording = self.object_to_write
        elif isinstance(self.object_to_write, se.SortingExtractor):
            self.sorting = self.object_to_write

    @staticmethod
    def supported_types():
        assert HAVE_SI013
        return (se.RecordingExtractor, se.SortingExtractor)

    def get_num_segments(self):
        return 1

    def _get_traces(self, channel_ids=None, start_frame=None, end_frame=None, return_scaled=True, segment_index=0):
        return self.recording.get_traces(channel_ids=None, start_frame=None, end_frame=None, return_scaled=True)

    def _get_channel_property_names(self):
        property_names = set()
        for chan_id in self._get_channel_ids():
            for i in self._get_channel_property_names(chan_id):
                property_names.add(i)
        return list(property_names)

    def _get_channel_property_values(self, prop):
        if prop == "location":
            return self.recording.get_channel_locations()
        elif prop == "gain":
            return self.recording.get_channel_gains()
        elif prop == "offset":
            return self.recording.get_channel_offsets()
        elif prop == "group":
            return self.recording.get_channel_groups()
        else:
            # infer channel properties and fill with defaults when not present for channel:
            channel_property_defaults = {list: [], np.ndarray: np.array(np.nan), str: "", Real: np.nan}
            found_property_types = Real
            # find the channel property dtype:
            for chan_id in self._get_channel_ids():
                try:
                    chan_data = self.recording.get_channel_property(channel_id=chan_id, property_name=prop)
                    proptype = [proptype for proptype in channel_property_defaults if isinstance(chan_data, proptype)]
                    if len(proptype)>0:
                        found_property_types = proptype[0] if len(proptype) > 1 else proptype
                        break
                    else: # if property not found in the supported channel_property_defaults, then return None
                        return
                except:
                    continue
            # build data array:
            data = []
            for chan_id in self._get_channel_ids():
                try:
                    chan_data = self.recording.get_channel_property(channel_id=chan_id, property_name=prop)
                except:
                    chan_data = channel_property_defaults[found_property_types]
                if found_property_types == Real:
                    data.append(np.float(chan_data))
                else:
                    data.append(chan_data)
            return np.array(data)

    def _get_num_frames(self, segment_index=0):
        if self.recording is not None:
            return self.recording.get_num_frames()

    def _get_recording_times(self, segment_index=0):
        if self.recording._times is None:
            return np.range(0, self._get_num_frames() * self._get_sampling_frequency(), self._get_sampling_frequency())
        return self.recording._times

    def _get_unit_feature_names(self, unit_id):
        return self.sorting.get_unit_spike_feature_names(unit_id)

    def _get_unit_feature_values(self, prop, unit_id):
        return self.sorting.get_unit_spike_features(unit_id, prop)

    def _get_unit_spike_train_ids(self, unit_id, start_frame=None, end_frame=None, segment_index=None):
        if self.sorting is not None:
            return self.sorting.get_unit_spike_train(unit_id, start_frame=start_frame, end_frame=end_frame)

    def _get_unit_spike_train_times(self, unit_id, segment_index=0):
        if self.sorting is not None:
            return self.sorting.frame_to_time(self.sorting.get_unit_spike_train(unit_id=unit_id))

    def _get_unit_property_names(self, unit_id):
        return self.sorting.get_unit_property_names(unit_id)

    def _get_unit_property_values(self, prop, unit_id):
        return self.sorting.get_unit_property(unit_id, prop)

    def _get_unit_waveforms_templates(self, unit_id, mode='mean'):
        return

    def add_epochs(self):
        """
        Auxiliary static method for nwbextractor.

        Adds epochs from recording object to nwbfile object.

        """
        if self.nwbfile is not None:
            assert isinstance(self.nwbfile, pynwb.NWBFile), "'nwbfile' should be of type pynwb.NWBFile"

        # add/update epochs
        for epoch_name in self.recording.get_epoch_names():
            epoch = self.recording.get_epoch_info(epoch_name)
            if self.nwbfile.epochs is None:
                self.nwbfile.add_epoch(
                    start_time=self.recording.frame_to_time(epoch["start_frame"]),
                    stop_time=self.recording.frame_to_time(epoch["end_frame"] - 1),
                    tags=epoch_name,
                )
            else:
                if [epoch_name] in self.nwbfile.epochs["tags"][:]:
                    ind = self.nwbfile.epochs["tags"][:].index([epoch_name])
                    self.nwbfile.epochs["start_time"].data[ind] = self.recording.frame_to_time(epoch["start_frame"])
                    self.nwbfile.epochs["stop_time"].data[ind] = self.recording.frame_to_time(epoch["end_frame"])
                else:
                    self.nwbfile.add_epoch(
                        start_time=self.recording.frame_to_time(epoch["start_frame"]),
                        stop_time=self.recording.frame_to_time(epoch["end_frame"]),
                        tags=epoch_name,
                    )

    def add_recording(self):
        super().add_recording()
        if self._conversion_ops["write_electrical_series"]:
            self.add_epochs()