"""Authors: Cody Baker."""
from pathlib import Path
import numpy as np
from typing import Union, Tuple, Iterable
from ....utils.genericdatachunkiterator import GenericDataChunkIterator

try:
    import cv2

    HAVE_OPENCV = True
except ImportError:
    HAVE_OPENCV = False

PathType = Union[str, Path]


class VideoCaptureContext(cv2.VideoCapture):
    def __init__(self, *args, **kwargs):
        super(VideoCaptureContext, self).__init__(*args, **kwargs)
        self.frame = self.get_movie_frame(0)
        assert self.frame is not None, "unable to read the movie file provided"

    def get_movie_timestamps(self):
        """
        Return numpy array of the timestamps for a movie file.

        """
        return [self.get(cv2.self_PROP_POS_MSEC) for _ in self]

    def get_movie_fps(self):
        """
        Return the internal frames per second (fps) for a movie file.

        """
        if int((cv2.__version__).split(".")[0]) < 3:
            fps = self.get(cv2.cv.CV_CAP_PROP_FPS)
        else:
            fps = self.get(cv2.CAP_PROP_FPS)
        return fps

    def get_frame_shape(self) -> Tuple:
        """
        Return the shape of frames from a movie file.
        """
        return self.frame.shape

    def get_movie_frame_count(self):
        """
        Return the total number of frames for a movie file.

        """
        if int((cv2.__version__).split(".")[0]) < 3:
            count = self.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT)
        else:
            count = self.get(cv2.CAP_PROP_FRAME_COUNT)
        return int(count)

    def _set_frame(self, frame_no):
        if int((cv2.__version__).split(".")[0]) < 3:
            set_arg = cv2.cv.CV_CAP_PROP_POS_FRAMES
        else:
            set_arg = cv2.CAP_PROP_POS_FRAMES
        return self.set(set_arg, frame_no)

    def get_movie_frame(self, frame_no: int):
        """
        Return the specific frame from a movie.
        """
        assert frame_no < self.get_movie_frame_count()
        _ = self._set_frame(frame_no)
        success, frame = self.read()
        _ = self._set_frame(0)
        if success:
            return frame
        else:
            return np.nan * np.ones(self.get_frame_shape())

    def get_movie_frame_dtype(self):
        """
        Return the dtype for frame in a movie file.
        """
        return self.frame.dtype

    def __next__(self):
        try:
            for frame_no in range(self.get_movie_frame_count()):
                success, frame = self.read()
                if success:
                    yield frame
                else:
                    yield np.nan * np.ones(self.get_frame_shape())
            _ = self._set_frame(0)
        except Exception:
            raise StopIteration

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()


class MovieDataChunkIterator(GenericDataChunkIterator):
    """DataChunkIterator specifically for use on RecordingExtractor objects."""

    def __init__(
        self,
        movie_file: PathType,
        buffer_gb: float = None,
        buffer_shape: tuple = None,
        chunk_mb: float = None,
        chunk_shape: tuple = None,
        stub: bool = False,
    ):
        self.video_capture_ob = VideoCaptureContext(movie_file)
        self._stub = stub
        if chunk_shape is None:
            chunk_shape = (1, *self.video_capture_ob.get_frame_shape())
        super().__init__(buffer_gb=buffer_gb, buffer_shape=buffer_shape, chunk_mb=chunk_mb, chunk_shape=chunk_shape)

    def _get_data(self, selection: Tuple[slice]) -> Iterable:
        frames_return = []
        step = selection[0].step if selection[0].step is not None else 1
        for frame_no in range(selection[0].start, selection[0].stop, step):
            frame = self.video_capture_ob.get_movie_frame(frame_no)
            frames_return.append(frame[selection[1:]])
        return np.concatenate(frames_return, axis=0)

    def _get_dtype(self):
        return self.video_capture_ob.get_movie_frame_dtype()

    def _get_maxshape(self):
        # if stub the assume a max frame count of 10
        if self._stub:
            return min(10, self.video_capture_ob.get_movie_frame_count(), *self.video_capture_ob.get_frame_shape())
        else:
            return (self.video_capture_ob.get_movie_frame_count(), *self.video_capture_ob.get_frame_shape())
