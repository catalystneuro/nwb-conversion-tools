"""Authors: Cody Baker."""
from pathlib import Path
import numpy as np
from typing import Union

try:
    import cv2

    HAVE_OPENCV = True
except ImportError:
    HAVE_OPENCV = False

PathType = Union[str, Path]


def get_movie_timestamps(movie_file: PathType):
    """
    Return numpy array of the timestamps for a movie file.

    Parameters
    ----------
    movie_file : PathType
    """
    cap = cv2.VideoCapture(str(movie_file))
    timestamps = []
    success, frame = cap.read()
    while success:
        timestamps.append(cap.get(cv2.CAP_PROP_POS_MSEC))
        success, frame = cap.read()
    cap.release()
    return np.array(timestamps)


def get_movie_fps(movie_file: PathType):
    """
    Return the internal frames per second (fps) for a movie file.

    Parameters
    ----------
    movie_file : PathType
    """
    cap = cv2.VideoCapture(str(movie_file))
    if int((cv2.__version__).split(".")[0]) < 3:
        fps = cap.get(cv2.cv.CV_CAP_PROP_FPS)
    else:
        fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    return fps


def get_frame_shape(movie_file: PathType):
    """
    Return the shape of frames from a movie file.

    Parameters
    ----------
    movie_file : PathType
    """
    cap = cv2.VideoCapture(str(movie_file))
    success, frame = cap.read()
    cap.release()
    return frame.shape


def get_movie_frame_count(movie_file: PathType):
    """
    Return the total number of frames for a movie file.

    """
    cap = cv2.VideoCapture(str(movie_file))
    if int(cv2.__version__.split(".")[0]) < 3:
        count = cap.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT)
    else:
        count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    return int(count)


def get_frame_no(movie_file: PathType, frame_no: int=0):
    """
    Retrive the frame no from a movie and return as array
    Parameters
    ----------
    movie_file: PathType
    frame_no: int
    Returns
    -------
    frame: np.array
    """
    assert frame_no < get_movie_frame_count(movie_file), "frame number is greater than length of movie"
    cap = cv2.VideoCapture(str(movie_file))
    if int(cv2.__version__.split(".")[0]) < 3:
        set_arg = cv2.cv.CV_CAP_PROP_POS_FRAMES
    else:
        set_arg = cv2.CAP_PROP_POS_FRAMES
    set_value = cap.set(set_arg, frame_no)
    if not set_value:
        return
    success, frame = cap.read()
    if success:
        return frame


def get_movie_frames(movie_file: PathType, count_max: int=None):
    """
    Returns a generator that returns sequential movie frames
    Parameters
    ----------
    movie_file: PathType

    Returns
    -------
    frame: np.array
    """
    no_frames = get_movie_frame_count(movie_file)
    count_max = no_frames if count_max is None else count_max
    for frame_no in range(count_max):
        cap = cv2.VideoCapture(str(movie_file))
        success, frame = cap.read()
        yield frame
    cap.release()
