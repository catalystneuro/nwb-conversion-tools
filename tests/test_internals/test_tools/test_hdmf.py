import numpy as np
from numpy.testing import assert_array_equal

from nwb_conversion_tools.tools.hdmf import MemmapDataChunkIterator


def test_memmap_data_chunk_iterator():

    data = np.arange(100).reshape(10, 10)

    dci = MemmapDataChunkIterator(data=data, buffer_shape=(5, 5), chunk_shape=(5, 5))

    data_chunk = next(dci)

    assert data_chunk.selection == (slice(0, 5, None), slice(0, 5, None))

    assert_array_equal(
        data_chunk.data,
        [[0, 1, 2, 3, 4], [10, 11, 12, 13, 14], [20, 21, 22, 23, 24], [30, 31, 32, 33, 34], [40, 41, 42, 43, 44]],
    )
