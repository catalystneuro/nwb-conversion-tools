"""Collection of modifications of HDMF functions that are to be tested/used on this repo until propagation upstream."""
from itertools import product, chain
from warnings import warn
from typing import Tuple, Optional

import numpy as np
from hdmf.data_utils import GenericDataChunkIterator as HDMFGenericDataChunkIterator


class GenericDataChunkIterator(HDMFGenericDataChunkIterator):
    def __init__(
        self,
        buffer_gb: Optional[float] = None,
        buffer_shape: Optional[tuple] = None,
        chunk_mb: Optional[float] = None,
        chunk_shape: Optional[tuple] = None,
        display_progress: bool = True,
        progress_bar_options: Optional[dict] = None,
    ):
        if buffer_gb is None and buffer_shape is None:
            buffer_gb = 1.0

        self._maxshape = self._get_maxshape()
        self._dtype = self._get_dtype()

        if chunk_mb is not None and chunk_shape is not None:
            assert not any((chunk_axis is None for chunk_axis in chunk_shape)), (
                "When specifying both 'chunk_mb' and 'chunk_shape', at least one element of "
                "'chunk_shape must be set to 'None'!"
            )
            raise NotImplementedError("Partial shape inference is not yet functioning for chunk specification!")
            # self.chunk_shape = self._infer_full_shape(target_byte_size=chunk_mb * 1e6, partial_shape=chunk_shape)
        elif chunk_mb is not None and chunk_shape is None:
            self.chunk_shape = self._get_default_chunk_shape(chunk_mb=chunk_mb)
        elif chunk_mb is None and chunk_shape is None:
            self.chunk_shape = self._get_default_chunk_shape(chunk_mb=1.0)
        elif chunk_mb is None and chunk_shape is not None:
            self.chunk_shape = chunk_shape

        if buffer_gb is not None and buffer_shape is not None:
            assert not any((buffer_axis is None for buffer_axis in buffer_shape)), (
                "When specifying both 'buffer_gb' and 'buffer_shape', at least one element of "
                "'buffer_shape must be set to 'None'!"
            )
            self.buffer_shape = self._infer_buffer_shape(buffer_gb=buffer_gb, partial_shape=buffer_shape)
        elif buffer_gb is not None and buffer_shape is None:
            self.buffer_shape = self._get_default_chunk_shape(chunk_mb=chunk_mb)
        elif buffer_gb is not None and buffer_shape is None:
            self.buffer_shape = self._get_default_buffer_shape(buffer_gb=1.0)
        elif buffer_gb is None and buffer_shape is not None:
            self.buffer_shape = buffer_shape

        array_chunk_shape = np.array(self.chunk_shape)
        array_buffer_shape = np.array(self.buffer_shape)
        array_maxshape = np.array(self.maxshape)
        assert all(array_buffer_shape > 0), f"Some dimensions of buffer_shape ({self.buffer_shape}) are less than zero!"
        assert all(
            array_buffer_shape <= array_maxshape
        ), f"Some dimensions of buffer_shape ({self.buffer_shape}) exceed the data dimensions ({self.maxshape})!"
        assert all(
            array_chunk_shape <= array_buffer_shape
        ), f"Some dimensions of chunk_shape ({self.chunk_shape}) exceed the manual buffer shape ({self.buffer_shape})!"
        assert all((array_buffer_shape % array_chunk_shape == 0)[array_buffer_shape != array_maxshape]), (
            f"Some dimensions of chunk_shape ({self.chunk_shape}) do not "
            f"evenly divide the buffer shape ({self.buffer_shape})!"
        )

        self.num_buffers = np.prod(np.ceil(array_maxshape / array_buffer_shape))
        self.buffer_selection_generator = (
            tuple([slice(lower_bound, upper_bound) for lower_bound, upper_bound in zip(lower_bounds, upper_bounds)])
            for lower_bounds, upper_bounds in zip(
                product(
                    *[
                        range(0, max_shape_axis, buffer_shape_axis)
                        for max_shape_axis, buffer_shape_axis in zip(self.maxshape, self.buffer_shape)
                    ]
                ),
                product(
                    *[
                        chain(range(buffer_shape_axis, max_shape_axis, buffer_shape_axis), [max_shape_axis])
                        for max_shape_axis, buffer_shape_axis in zip(self.maxshape, self.buffer_shape)
                    ]
                ),
            )
        )

        if self.display_progress:
            if self.progress_bar_options is None:
                self.progress_bar_options = dict()

            try:
                from tqdm import tqdm

                if "total" in self.progress_bar_options:
                    warn("Option 'total' in 'progress_bar_options' is not allowed to be over-written! Ignoring.")
                    self.progress_bar_options.pop("total")
                self.progress_bar = tqdm(total=self.num_buffers, **self.progress_bar_options)
            except ImportError:
                warn(
                    "You must install tqdm to use the progress bar feature (pip install tqdm)! "
                    "Progress bar is disabled."
                )
                self.display_progress = False

    def _infer_buffer_shape(self, buffer_gb: float, partial_shape: tuple) -> tuple:
        """Calculate the values for the `None` elements of the partial shape which result in a size below the target."""
        num_axes = len(self.maxshape)
        target_byte_size = buffer_gb * 1e9
        none_axes = [axis is None for axis in partial_shape]
        none_axes_idx = np.where(none_axes)
        full_shape = np.zeros(shape=num_axes)
        full_shape[~none_axes] = partial_shape[~none_axes]

        # Minimum shape early exit
        unit_fill_full_shape = np.array(full_shape)
        unit_fill_full_shape[none_axes] = 1
        if np.prod(unit_fill_full_shape) * self.dtype.itemsize > target_byte_size:
            return tuple(unit_fill_full_shape)

        # Maximum fill early exit
        max_fill_full_shape = np.array(full_shape)
        max_fill_full_shape[none_axes] = np.array(self.maxshape)[none_axes]
        if np.prod(max_fill_full_shape) * self.dtype.itemsize <= target_byte_size:
            return tuple(max_fill_full_shape)

        # Unpadded estimation for partial axes
        chunk_bytes = np.prod(self.chunk_shape) * self.dtype.itemsize
        chunk_to_buffer_ratio = target_byte_size / chunk_bytes
        num_none_axes = len(none_axes_idx)
        chunk_scaling_factor = np.floor(chunk_to_buffer_ratio ** (1 / num_none_axes))
        unpadded_partial_buffer_shape = [
            np.clip(a=int(x), a_min=self.chunk_shape[j], a_max=self.maxshape[j])
            for j, x in enumerate(chunk_scaling_factor * np.array(self.chunk_shape))
        ]

    def _get_default_buffer_shape(self, buffer_gb: float = 1.0) -> Tuple[int]:
        num_axes = len(self.maxshape)
        chunk_bytes = np.prod(self.chunk_shape) * self.dtype.itemsize
        assert buffer_gb > 0, f"buffer_gb ({buffer_gb}) must be greater than zero!"
        assert (
            buffer_gb >= chunk_bytes / 1e9
        ), f"buffer_gb ({buffer_gb}) must be greater than the chunk size ({chunk_bytes / 1e9})!"
        assert all(
            np.array(self.chunk_shape) > 0
        ), f"Some dimensions of chunk_shape ({self.chunk_shape}) are less than zero!"

        maxshape = np.array(self.maxshape)

        # Early termination condition
        if np.prod(maxshape) * self.dtype.itemsize / 1e9 < buffer_gb:
            return tuple(self.maxshape)

        buffer_bytes = chunk_bytes
        axis_sizes_bytes = maxshape * self.dtype.itemsize
        smallest_chunk_axis, second_smallest_chunk_axis, *_ = np.argsort(self.chunk_shape)
        target_buffer_bytes = buffer_gb * 1e9

        # If the smallest full axis does not fit within the buffer size, form a square along the two smallest axes
        sub_square_buffer_shape = np.array(self.chunk_shape)
        if min(axis_sizes_bytes) > target_buffer_bytes:
            k1 = np.floor((target_buffer_bytes / chunk_bytes) ** 0.5)
            for axis in [smallest_chunk_axis, second_smallest_chunk_axis]:
                sub_square_buffer_shape[axis] = k1 * sub_square_buffer_shape[axis]
            return tuple(sub_square_buffer_shape)

        # Original one-shot estimation has good performance for certain shapes
        chunk_to_buffer_ratio = buffer_gb * 1e9 / chunk_bytes
        chunk_scaling_factor = np.floor(chunk_to_buffer_ratio ** (1 / num_axes))
        unpadded_buffer_shape = [
            np.clip(a=int(x), a_min=self.chunk_shape[j], a_max=self.maxshape[j])
            for j, x in enumerate(chunk_scaling_factor * np.array(self.chunk_shape))
        ]

        unpadded_buffer_bytes = np.prod(unpadded_buffer_shape) * self.dtype.itemsize

        # Method that starts by filling the smallest axis completely or calculates best partial fill
        padded_buffer_shape = np.array(self.chunk_shape)
        chunks_per_axis = np.ceil(maxshape / self.chunk_shape)
        small_axis_fill_size = chunk_bytes * min(chunks_per_axis)
        full_axes_used = np.zeros(shape=num_axes, dtype=bool)
        if small_axis_fill_size <= target_buffer_bytes:
            buffer_bytes = small_axis_fill_size
            padded_buffer_shape[smallest_chunk_axis] = self.maxshape[smallest_chunk_axis]
            full_axes_used[smallest_chunk_axis] = True
        for axis, chunks_on_axis in enumerate(chunks_per_axis):
            if full_axes_used[axis]:  # If the smallest axis, skip since already used
                continue
            if chunks_on_axis * buffer_bytes <= target_buffer_bytes:  # If multiple axes can be used together
                buffer_bytes *= chunks_on_axis
                padded_buffer_shape[axis] = self.maxshape[axis]
            else:  # Found an axis that is too large to use with the rest of the buffer; calculate how much can be used
                k3 = np.floor(target_buffer_bytes / buffer_bytes)
                padded_buffer_shape[axis] *= k3
                break
        padded_buffer_bytes = np.prod(padded_buffer_shape) * self.dtype.itemsize

        if padded_buffer_bytes >= unpadded_buffer_bytes:
            return tuple(padded_buffer_shape)
        else:
            return tuple(unpadded_buffer_shape)


class SliceableDataChunkIterator(GenericDataChunkIterator):
    """
    Generic data chunk iterator that works for any memory mapped array, such as a np.memmap or an h5py.Dataset
    """

    def __init__(self, data, **kwargs):
        self.data = data
        super().__init__(**kwargs)

    def _get_dtype(self) -> np.dtype:
        return self.data.dtype

    def _get_maxshape(self) -> tuple:
        return self.data.shape

    def _get_data(self, selection: Tuple[slice]) -> np.ndarray:
        return self.data[selection]
