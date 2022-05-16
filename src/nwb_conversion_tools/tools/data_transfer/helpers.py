"""Collection of helper functions for the data transfer tools."""
from pathlib import Path
from tempfile import mkdtemp

from ...utils import FolderPathType, OptionalFolderPathType


def make_cache(
    cache_folder: OptionalFolderPathType = None, parent_directory: OptionalFolderPathType = None
) -> FolderPathType:
    """Make a cache folder in either the folder_path location or in the temporary system folder (default)."""
    if cache_folder is not None:
        Path(cache_folder).mkdir(exist_ok=True)
        return cache_folder
    if parent_directory is not None:
        cache_folder = Path(mkdtemp(dir=parent_directory))
        return cache_folder
    try:
        cache_folder = Path(mkdtemp())
        return cache_folder
    except PermissionError:  # Send more informative error message
        cache_folder = None
        raise PermissionError(
            "System does not have write access to the temporary folder! "
            "Please specify either an explicit cache_folder or an implicit parent_directory with write permissions."
        )
