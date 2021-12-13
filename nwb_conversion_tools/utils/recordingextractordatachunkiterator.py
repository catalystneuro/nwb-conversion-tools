"""Authors: Cody Baker and Saksham Sharda."""
from typing import Tuple, Iterable
from tqdm import tqdm

from spikeextractors import RecordingExtractor

from .genericdatachunkiterator import GenericDataChunkIterator


class RecordingExtractorDataChunkIterator(GenericDataChunkIterator):
    """DataChunkIterator specifically for use on RecordingExtractor objects."""

    def __init__(
        self,
        recording: RecordingExtractor,
        buffer_gb: float = None,
        buffer_shape: tuple = None,
        chunk_mb: float = None,
        chunk_shape: tuple = None,
        display_progress: bool = True,
    ):
        self.recording = recording
        self.display_progress = display_progress
        self.channel_ids = recording.get_channel_ids()
        if self.display_progress:
            self.progress_bar = tqdm(total=self.num_buffers, position=0, leave=False)
        super().__init__(buffer_gb=buffer_gb, buffer_shape=buffer_shape, chunk_mb=chunk_mb, chunk_shape=chunk_shape)

    def _get_data(self, selection: Tuple[slice]) -> Iterable:
        return self.recording.get_traces(
            channel_ids=self.channel_ids[selection[1]],
            start_frame=selection[0].start,
            end_frame=selection[0].stop,
            return_scaled=False,
        ).T

    def _get_dtype(self):
        return self.recording.get_dtype(return_scaled=False)

    def _get_maxshape(self):
        return (self.recording.get_num_frames(), self.recording.get_num_channels())

    def __next__(self):
        if self.display_progress:
            self.progress_bar.update(n=1)
        try:
            super().__next__()
        except StopIteration:
            if self.display_progress:
                self.progress_bar.write("\n")  # Allows text to be written to new lines after completion
            raise StopIteration
