"""Authors: Saksham Sharda."""
import numpy as np
from distutils.version import StrictVersion

from .basesinwbephyswriter import BaseSINwbEphysWriter

try:
    import spikeinterface as si
    from spikeinterface.core.testing_tools import generate_recording, generate_sorting

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
    stub: bool
        whether to write a subset of recording extractor traces array as electrical series in nwbfile
    stub_channels: list
        channels to include when writing as stub
    """

    def __init__(self, object_to_write, stub=False, stub_channels=None):
        assert HAVE_SI_090
        BaseSINwbEphysWriter.__init__(self, object_to_write, stub=stub, stub_channels=stub_channels)
        if isinstance(self.object_to_write, si.BaseRecording):
            self.recording = self.object_to_write
            if self.stub:
                self._make_recording_stub()
        elif isinstance(self.object_to_write, si.BaseSorting):
            self.sorting = self.object_to_write
            if self.stub:
                self._make_sorting_stub()
        elif isinstance(self.object_to_write, si.BaseEvent):
            self.event = self.object_to_write
        elif isinstance(self.object_to_write, si.WaveformExtractor):
            self.recording = self.object_to_write.recording
            self.sorting = self.object_to_write.sorting
            self.waveforms = self.object_to_write
            if self.stub:
                self._make_sorting_stub()
                self._make_recording_stub()

    def _make_recording_stub(self):
        if self.stub_channels is not None:
            channel_stub = self.stub_channels
        else:
            num_channels = min(10, self.recording.get_num_channels())
            channel_stub = self.recording.get_channel_ids()[:num_channels]
        frame_stub = min(100, self.recording.get_num_frames())
        self.recording = si.ChannelSliceRecording(self.recording, channel_ids=channel_stub)
        self.recording = si.FrameSliceRecording(self.recording, end_frame=frame_stub)

    def _make_sorting_stub(self):
        max_min_spike_time = max(
            [min(x) for y in self.sorting.get_unit_ids() for x in [self.sorting.get_unit_spike_train(y)] if any(x)]
        )
        self.sorting = si.FrameSliceSorting(start_frame=0, end_frame=1.1 * max_min_spike_time)

    @staticmethod
    def supported_types():
        assert HAVE_SI_090
        return si.BaseRecording, si.BaseSorting, si.BaseEvent, si.WaveformExtractor

    def get_num_segments(self):
        return self.object_to_write.get_num_segments()

    def _get_num_frames(self, segment_index=0):
        return self.recording.get_num_frames(segment_index=segment_index)

    def _get_traces(self, channel_ids=None, start_frame=None, end_frame=None, return_scaled=True, segment_index=0):
        if return_scaled and not self.recording.has_scaled_traces():
            return_scaled = False
        return self.recording.get_traces(
            channel_ids=channel_ids,
            start_frame=start_frame,
            end_frame=end_frame,
            return_scaled=return_scaled,
            segment_index=segment_index,
        )

    def _get_dtype(self, return_scaled=True):
        if not return_scaled:
            return self.recording.get_dtype()
        else:
            return self._get_traces(
                channel_ids=self._get_channel_ids()[:1], start_frame=0, end_frame=2, return_scaled=return_scaled
            ).dtype

    def _get_channel_property_names(self):
        default_properties = ["location", "group"]
        if self.recording.get_channel_offsets() is not None:
            default_properties.append("offset")
        if self.recording.get_channel_gains() is not None:
            default_properties.append("gain")
        if isinstance(self.recording.get_channel_ids()[0], str):
            default_properties.append("name")
        skip_properties = ["contact_vector"]
        return list(set(self.recording.get_property_keys()).union(default_properties).difference(skip_properties))
    
    def _get_gains(self):
        if "gain_to_uV" in self.recording.get_property_keys():
            return self.recording.get_property("gain_to_uV")
        else:
            return None

    def _get_offsets(self):
        if "offset_to_uV" in self.recording.get_property_keys():
            return self.recording.get_property("offset_to_uV")
        else:
            return None


    def _get_channel_property_values(self, prop):
        if prop == "location":
            try:
                return self.recording.get_channel_locations()
            except:
                return np.nan * np.ones([len(self._get_channel_ids()), 2])
        elif prop == "gain":
            return self.recording.get_channel_gains()
        elif prop == "offset":
            return self.recording.get_channel_offsets()
        elif prop == "group":
            if self.recording.get_property("group_name") is not None:
                return self.recording.get_property("group_name")
            if self.recording.get_channel_groups() is None:
                return np.zeros(len(self._get_channel_ids()))
            else:
                return self.recording.get_channel_groups()
        elif prop == "name":
            ids = self.recording.get_channel_ids()
            if isinstance(ids[0], str):
                return ids
        else:
            prop_values = self.recording.get_property(prop)
            return self._check_valid_property(prop_values)

    def _get_recording_times(self, segment_index=0):
        return np.arange(
            0,
            self._get_num_frames(segment_index=segment_index) * self._get_sampling_frequency(),
            self._get_sampling_frequency(),
        )

    def _get_unit_feature_names(self):
        return []

    def _get_unit_feature_values(self, prop):
        return []

    def _get_unit_spike_train_ids(self, unit_id, start_frame=None, end_frame=None, segment_index=None):
        return self.sorting.get_unit_spike_train(
            unit_id, start_frame=start_frame, end_frame=end_frame, segment_index=segment_index
        )

    def _get_unit_spike_train_times(self, unit_id, segment_index=0):
        return self._get_unit_spike_train_ids(unit_id, segment_index) / self._get_unit_sampling_frequency()

    def _get_unit_property_names(self):
        properties = self.sorting.get_property_keys()
        if self.waveforms is not None:
            if "max_channel" not in properties:
                properties.append("max_channel")
        return properties

    def _get_unit_property_values(self, prop):
        prop_values = self.sorting.get_property(prop)
        if self.waveforms is not None:
            if prop_values is None and prop == "max_channel":
                from spikeinterface.toolkit import get_template_extremum_channel

                channels_dict = get_template_extremum_channel(self.waveforms)
                prop_values = [channels_dict.get(id, np.nan) for id in self._get_unit_ids()]
        return self._check_valid_property(prop_values)

    def _get_unit_waveforms_templates(self, unit_id, mode="average"):
        return self.waveforms.get_template(unit_id, mode=mode)

    def add_epochs(self):
        return
