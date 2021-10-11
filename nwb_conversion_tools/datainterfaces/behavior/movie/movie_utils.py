"""Authors: Saksham Sharda, Cody Baker."""
from pathlib import Path
import numpy as np
from typing import Union, Tuple, Iterable
from tqdm import tqdm
from ....utils.genericdatachunkiterator import GenericDataChunkIterator

try:
    import cv2

    HAVE_OPENCV = True
except ImportError:
    HAVE_OPENCV = False

PathType = Union[str, Path]


class VideoCaptureContext(cv2.VideoCapture):
    def __init__(self, *args, stub=False, **kwargs):
        self._args = args
        self._kwargs = kwargs
        self._stub = stub
        self._current_frame = 0
        with self:
            self._frame_count = self._get_movie_frame_count()
            self._fps = self._get_movie_fps()
            self._frame = self.get_movie_frame(0)
            assert self._frame is not None, "unable to read the movie file provided"

    def get_movie_timestamps(self):
        """
        Return numpy array of the timestamps for a movie file.

        """
        if self.isOpened():
            ts = [self.get(cv2.CAP_PROP_POS_MSEC)]
            for i in tqdm(range(1, self.get_movie_frame_count())):
                self._set_frame(i)
                ts.append(self.get(cv2.CAP_PROP_POS_MSEC))
            self._set_frame(0)
            return np.array(ts)

    def _get_movie_fps(self):
        """
        Return the internal frames per second (fps) for a movie file.

        """
        if int((cv2.__version__).split(".")[0]) < 3:
            fps = self.get(cv2.cv.CV_CAP_PROP_FPS)
        else:
            fps = self.get(cv2.CAP_PROP_FPS)
        return fps

    def get_movie_fps(self):
        return self._fps

    def get_frame_shape(self) -> Tuple:
        """
        Return the shape of frames from a movie file.
        """
        return self._frame.shape

    def _get_movie_frame_count(self):
        """
        Return the total number of frames for a movie file.

        """
        if self._stub:
            # if stub the assume a max frame count of 10
            return 10
        if int((cv2.__version__).split(".")[0]) < 3:
            count = self.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT)
        else:
            count = self.get(cv2.CAP_PROP_FRAME_COUNT)
        return int(count)

    def get_movie_frame_count(self):
        return self._frame_count

    def _set_frame(self, frame_no):
        if int((cv2.__version__).split(".")[0]) < 3:
            set_arg = cv2.cv.CV_CAP_PROP_POS_FRAMES
        else:
            set_arg = cv2.CAP_PROP_POS_FRAMES
        self._current_frame = frame_no
        return self.set(set_arg, frame_no)

    def get_movie_frame(self, frame_no: int):
        """
        Return the specific frame from a movie.
        """
        if self.isOpened():
            assert frame_no < self.get_movie_frame_count()
            _ = self._set_frame(frame_no)
            success, frame = self.read()
            _ = self._set_frame(0)
            if success:
                return frame
            elif frame_no > 0:
                return np.nan * np.ones(self.get_frame_shape())

    def get_movie_frame_dtype(self):
        """
        Return the dtype for frame in a movie file.
        """
        return self._frame.dtype

    def __iter__(self):
        return self

    def __next__(self):
        if self.isOpened():
            try:
                if self._current_frame < self.get_movie_frame_count():
                    success, frame = self.read()
                    self._current_frame += 1
                    if success:
                        return frame
                    else:
                        return np.nan * np.ones(self.get_frame_shape())
                else:
                    _ = self._set_frame(0)
                    raise StopIteration
            except Exception:
                raise StopIteration
        else:
            raise StopIteration

    def __enter__(self):
        super(VideoCaptureContext, self).__init__(*self._args, **self._kwargs)
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
        self.video_capture_ob = VideoCaptureContext(movie_file, stub=stub)
        if chunk_shape is None:
            chunk_shape = (1, *self.video_capture_ob.get_frame_shape())
        super().__init__(buffer_gb=buffer_gb, buffer_shape=buffer_shape, chunk_mb=chunk_mb, chunk_shape=chunk_shape)

    def _get_data(self, selection: Tuple[slice]) -> Iterable:
        frames_return = []
        step = selection[0].step if selection[0].step is not None else 1
        for frame_no in range(selection[0].start, selection[0].stop, step):
            with self.video_capture_ob as vc:
                frame = vc.get_movie_frame(frame_no)
                frames_return.append(frame[selection[1:]])
        return np.concatenate(frames_return, axis=0)

    def _get_dtype(self):
        return self.video_capture_ob.get_movie_frame_dtype()

    def _get_maxshape(self):
        return (self.video_capture_ob.get_movie_frame_count(), *self.video_capture_ob.get_frame_shape())
