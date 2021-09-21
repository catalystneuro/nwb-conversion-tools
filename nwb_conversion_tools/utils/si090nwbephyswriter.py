from distutils.version import StrictVersion
from typing import Union

import numpy as np
import pynwb

from .basesinwbephyswriter import BaseSINwbEphysWriter
from .common_writer_tools import PathType, default_return

try:
    import spikeinterface as si

    if StrictVersion(si.__version__[:4]) >= StrictVersion("0.90"):
        HAVE_SI_090 = True
    else:
        HAVE_SI_090 = False
except ImportError:
    HAVE_SI_090 = False


class SI090NwbEphysWriter(BaseSINwbEphysWriter):
    """
    Class to write a Recording, Sorting, Event, or WaveformExtractor object from SI>=0.90 to NWB

    Parameters
    ----------
    object_to_write: si.BaseRecording, si.BaseSorting, si.BaseEvent, si.WaveformExtractor
    nwb_file_path: Path type
    nwbfile: pynwb.NWBFile or None
    metadata: dict or None
    **kwargs: list kwargs and meaning
    """

    def __init__(
            self,
            object_to_write: Union[si.BaseRecording, si.BaseSorting, si.BaseEvent, si.WaveformExtractor],
            nwb_file_path: PathType = None,
            nwbfile: pynwb.NWBFile = None,
            metadata: dict = None,
            **kwargs,
    ):
        assert HAVE_SI_090
        BaseSINwbEphysWriter.__init__(
            self, object_to_write, nwb_file_path=nwb_file_path, nwbfile=nwbfile, metadata=metadata, **kwargs
        )
        if isinstance(self.object_to_write, si.BaseRecording):
            self.recording = self.object_to_write
        elif isinstance(self.object_to_write, si.BaseRecording):
            self.sorting = self.object_to_write
        elif isinstance(self.object_to_write, si.BaseEvent):
            self.event = self.object_to_write
        elif isinstance(self.object_to_write, si.WaveformExtractor):
            self.recording = self.object_to_write.recording
            self.sorting = self.object_to_write.sorting
            self.waveforms = self.object_to_write

    @staticmethod
    def supported_types():
        assert HAVE_SI_090
        return (si.BaseRecording, si.BaseSorting, si.BaseEvent, si.WaveformExtractor)

    def get_num_segments(self):
        return self.object_to_write.get_num_segments()

    @default_return(None)
    def _get_num_frames(self, segment_index=0):
        return self.recording.get_num_frames(segment_index=segment_index)

    @default_return([])
    def _get_traces(self, channel_ids=None, start_frame=None, end_frame=None, return_scaled=True, segment_index=0):
        return self.recording.get_traces(channel_ids=channel_ids,
                                         start_frame=start_frame,
                                         end_frame=end_frame,
                                         return_scaled=return_scaled,
                                         segment_index=segment_index)

    @default_return([])
    def _get_channel_property_names(self):
        default_properties = ["location", "gain", "offset", "group"]
        return list(set(self.recording.get_property_keys()).union(default_properties))

    @default_return([])
    def _get_channel_property_values(self, prop):
        if prop == "location":
            try:
                return self.recording.get_channel_locations()
            except:
                return np.nan*np.ones(len(self._get_channel_ids()), 2)
        elif prop == "gain":
            if self.recording.get_channel_gains() is None:
                return np.ones(len(self._get_channel_ids()))
            else:
                return self.recording.get_channel_gains()
        elif prop == "offset":
            if self.recording.get_channel_offsets() is None:
                return np.zeros(len(self._get_channel_ids()))
            else:
                return self.recording.get_channel_offsets()
        elif prop == "group":
            if self.recording.get_channel_groups() is None:
                return np.zeros(len(self._get_channel_ids()))
            else:
                return self.recording.get_channel_groups()
        else:
            prop_values = self.recording.get_property(prop)
            return self._check_valid_property(prop_values)

    @default_return([])
    def _get_recording_times(self, segment_index=0):
        return np.range(0, self._get_num_frames(segment_index=segment_index)
                        *self._get_sampling_frequency(), self._get_sampling_frequency())

    @default_return([])
    def _get_unit_feature_names(self):
        return

    @default_return([])
    def _get_unit_feature_values(self, prop):
        return

    @default_return([])
    def _get_unit_spike_train_ids(self, unit_id, start_frame=None, end_frame=None, segment_index=None):
        return self.sorting.get_unit_spike_train(unit_id, start_frame=start_frame,
                                                 end_frame=end_frame, segment_index=segment_index)

    @default_return([])
    def _get_unit_spike_train_times(self, unit_id, segment_index=0):
        return self._get_unit_spike_train_ids(unit_id, segment_index)/self._get_unit_sampling_frequency()

    def _get_unit_property_names(self):
        properties = self.sorting.get_property_keys()
        if 'max_channel' not in properties:
            properties = properties.extend('max_channel')
        return properties

    @default_return([])
    def _get_unit_property_values(self, prop):
        prop_values = self.sorting.get_unit_property(prop)
        if prop_values is None and prop == 'max_channel':
            from spikeinterface.toolkit import get_template_extremum_channel
            channels_dict = get_template_extremum_channel(self.waveforms)
            prop_values = [channels_dict.get(id, np.nan) for id in self._get_unit_ids()]
        return self._check_valid_property(prop_values)

    @default_return([])
    def _get_unit_waveforms_templates(self, unit_id, mode='mean'):
        return self.waveforms.get_template(unit_id, mode=mode)

    def add_epochs(self):
        return
