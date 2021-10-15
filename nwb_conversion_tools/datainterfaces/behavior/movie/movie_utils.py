"""Authors: Saksham Sharda, Cody Baker."""
from pathlib import Path
import numpy as np
from typing import Union, Tuple, Iterable
import warnings
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
        super().__init__(*args, **kwargs)
        self.stub = stub
        self._current_frame = 0
        self.frame_count = self.get_movie_frame_count()
        self.fps = self.get_movie_fps()
        self.frame = self.get_movie_frame(0)
        assert self.frame is not None, "unable to read the movie file provided"

    def get_movie_timestamps(self):
        """
        Return numpy array of the timestamps for a movie file.

        """
        if not self.isOpened():
            raise ValueError("movie file is not open")
        ts = [self.get(cv2.CAP_PROP_POS_MSEC)]
        for i in tqdm(range(1, self.get_movie_frame_count()), desc="retrieving video timestamps"):
            self.current_frame = i
            ts.append(self.get(cv2.CAP_PROP_POS_MSEC))
        self.current_frame = 0
        return np.array(ts)

    def get_movie_fps(self):
        """
        Return the internal frames per second (fps) for a movie file.

        """
        if int(cv2.__version__.split(".")[0]) < 3:
            return self.get(cv2.cv.CV_CAP_PROP_FPS)
        return self.get(cv2.CAP_PROP_FPS)

    def get_frame_shape(self) -> Tuple:
        """
        Return the shape of frames from a movie file.
        """
        return self.frame.shape

    def get_movie_frame_count(self):
        """
        Return the total number of frames for a movie file.

        """
        if self.stub:
            # if stub the assume a max frame count of 10
            return 10
        if int(cv2.__version__.split(".")[0]) < 3:
            count = self.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT)
        else:
            count = self.get(cv2.CAP_PROP_FRAME_COUNT)
        return int(count)

    @property
    def current_frame(self):
        return self._current_frame

    @current_frame.setter
    def current_frame(self, frame_no):
        if int(cv2.__version__.split(".")[0]) < 3:
            set_arg = cv2.cv.CV_CAP_PROP_POS_FRAMES
        else:
            set_arg = cv2.CAP_PROP_POS_FRAMES
        set_value = self.set(set_arg, frame_no)
        if set_value:
            self._current_frame = frame_no
        else:
            raise ValueError(f"could not set frame no {frame_no}")

    def get_movie_frame(self, frame_no: int):
        """
        Return the specific frame from a movie.
        """
        if not self.isOpened():
            raise ValueError("movie file is not open")
        assert frame_no < self.get_movie_frame_count(), "frame number is greater than length of movie"
        self.current_frame = frame_no
        success, frame = self.read()
        self.current_frame = 0
        if success:
            return frame
        elif frame_no > 0:
            return np.nan * np.ones(self.get_frame_shape())

    def get_movie_frame_dtype(self):
        """
        Return the dtype for frame in a movie file.
        """
        return self.frame.dtype

    def __iter__(self):
        return self

    def __next__(self):
        if not self.isOpened():
            raise StopIteration
        try:
            if self.current_frame < self.get_movie_frame_count():
                success, frame = self.read()
                self.current_frame += 1
                if success:
                    return frame
                else:
                    return np.nan*np.ones(self.get_frame_shape())
            else:
                self.current_frame = 0
                raise StopIteration
        except Exception:
            raise StopIteration

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()

    def __del__(self):
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
        self._default_chunk_shape = False
        if chunk_shape is None:
            chunk_shape = (1, *self.video_capture_ob.get_frame_shape())
            self._default_chunk_shape = True
        super().__init__(buffer_gb=buffer_gb, buffer_shape=buffer_shape, chunk_mb=chunk_mb, chunk_shape=chunk_shape)
        self._current_chunk = 1
        self._pbar = None

    def _get_data(self, selection: Tuple[slice]) -> Iterable:
        if self._pbar is None:
            self._pbar = tqdm(total=np.prod(self.num_chunks), desc="retrieving movie data chunk")
        if self._default_chunk_shape:
            print('calling next')
            self._current_chunk += 1
            self._pbar.update()
            return next(self.video_capture_ob)
        frames_return = []
        step = selection[0].step if selection[0].step is not None else 1
        for frame_no in range(selection[0].start, selection[0].stop, step):
            frame = self.video_capture_ob.get_movie_frame(frame_no)
            frames_return.append(frame[selection[1:]])
            self._pbar.update()
            self._current_chunk += 1
        return np.concatenate(frames_return, axis=0)

    def _get_dtype(self):
        return self.video_capture_ob.get_movie_frame_dtype()

    def _get_maxshape(self):
        return self.video_capture_ob.get_movie_frame_count(), *self.video_capture_ob.get_frame_shape()
