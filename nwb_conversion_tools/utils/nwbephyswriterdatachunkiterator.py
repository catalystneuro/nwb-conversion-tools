"""Authors: Saksham Sharda."""
from typing import Tuple, Iterable

from .genericdatachunkiterator import GenericDataChunkIterator


class NwbEphysWriterDataChunkIterator(GenericDataChunkIterator):
    """DataChunkIterator specifically for use on RecordingExtractor objects."""

    def __init__(
        self,
        ephys_writer,
        segment_index: int = 0,
        unsigned_coercion: int = 0,
        write_scaled: bool = True,
        buffer_gb: float = None,
        buffer_shape: tuple = None,
        chunk_mb: float = None,
        chunk_shape: tuple = None,
    ):
        self.segment_index = segment_index
        self.unsigned_coercion = unsigned_coercion
        self.write_scaled = write_scaled
        self.ephys_writer = ephys_writer
        self.channel_ids = ephys_writer._get_channel_ids()
        super().__init__(buffer_gb=buffer_gb, buffer_shape=buffer_shape, chunk_mb=chunk_mb, chunk_shape=chunk_shape)

    def _get_data(self, selection: Tuple[slice]) -> Iterable:
        return self.ephys_writer._get_traces(
            channel_ids=self.channel_ids[selection[1]],
            start_frame=selection[0].start,
            end_frame=selection[0].stop,
            return_scaled=self.write_scaled,
            segment_index=self.segment_index,
        ) + self.unsigned_coercion

    def _get_dtype(self):
        return self.ephys_writer._get_traces(
            channel_ids=self.channel_ids[0],
            start_frame=0,
            end_frame=1,
            return_scaled=True,
            segment_index=self.segment_index,
        ).dtype

    def _get_maxshape(self):
        return (self.ephys_writer._get_num_frames(self.segment_index), len(self.ephys_writer._get_channel_ids()))
