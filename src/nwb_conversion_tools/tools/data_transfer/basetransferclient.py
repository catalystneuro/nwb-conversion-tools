"""Collection of base classes for performing data transfer commands across various services."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List
from numbers import Real

from .helpers import make_cache
from ...utils import FilePathType, FolderPathType, OptionalFolderPathType


@dataclass
class Manifest:
    """Common data class for describing file contents and attributes on the client side."""

    files: List[FilePathType]
    file_size: List[Real]


class BaseTransferClient(ABC):
    """Common API for performing data transfer commands across various services."""

    total_manifest: Manifest = None
    transfer_manifest: Manifest = None

    @abstractmethod
    def __init__(self, cache_folder: OptionalFolderPathType = None, **kwargs):
        """
        When instantiating, remember to check that the service is setup.

        It is highly recommended to cache the most general manifest possible early in the process to reduce the
        overall number of API calls that have to be sent to the server.
        """
        self.cache_folder = make_cache(cache_folder=cache_folder)
        # Some child kwargs may involve candidates for optional keyword argument `parent_directory` in `make_cache`
        # So in those cases do not call super().__init__(...)

    @abstractmethod
    def fetch_total_manifest(self, source_directory: FolderPathType):
        """Retrieve the total file contents available on the client side by recursing the source_directory."""
        raise NotImplementedError(f"The method 'fetch_total_manifest' has not been defined for class {self.__class__}!")

    def set_transfer_manifest(self, transfer_manifest: FolderPathType):
        """Select a subset of the total_manifest to submit a transfer request."""
        self.transfer_manifest = transfer_manifest

    @abstractmethod
    def transfer_data(self):
        """Submit and track the request for files in the transfer_manifest through the appropriate child API/SDK."""
        raise NotImplementedError(f"The method 'transfer_data' has not been defined for class {self.__class__}!")
