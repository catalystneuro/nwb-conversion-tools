"""Authors: Saksham Sharda."""
from typing import Tuple, Iterable
import numpy as np
from .genericdatachunkiterator import GenericDataChunkIterator


class NwbEphysWriterDataChunkIterator(GenericDataChunkIterator):
    """DataChunkIterator specifically for use on RecordingExtractor objects."""

    def __init__(
        self,
        ephys_writer,
        segment_index: int = 0,
        unsigned_coercion: list = None,
        write_scaled: bool = True,
        buffer_gb: float = None,
        buffer_shape: tuple = None,
        chunk_mb: float = None,
        chunk_shape: tuple = None,
    ):
        self.segment_index = segment_index
        self.write_scaled = write_scaled
        self.ephys_writer = ephys_writer
        self.channel_ids = list(ephys_writer._get_channel_ids())
        self.unsigned_coercion = [0] * len(self.channel_ids) if unsigned_coercion is None else unsigned_coercion
        super().__init__(buffer_gb=buffer_gb, buffer_shape=buffer_shape, chunk_mb=chunk_mb, chunk_shape=chunk_shape)

    def _get_data(self, selection: Tuple[slice]) -> Iterable:
        channel_ids = self.channel_ids[selection[1]]
        channel_idxs = [self.channel_ids.index(ch) for ch in channel_ids]
        return (
            self.ephys_writer._get_traces(
                channel_ids=channel_ids,
                start_frame=selection[0].start,
                end_frame=selection[0].stop,
                return_scaled=self.write_scaled,
                segment_index=self.segment_index,
            )
            + self.unsigned_coercion[np.array(channel_idxs)]
        )

    def _get_dtype(self):
        return self.ephys_writer._get_dtype(self.write_scaled)

    def _get_maxshape(self):
        return (self.ephys_writer._get_num_frames(self.segment_index), len(self.ephys_writer._get_channel_ids()))
