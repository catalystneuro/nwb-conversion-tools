"""Collection of base classes for performing data transfer commands across various services."""
from .. import BaseTransferClient

from ..helpers import make_cache
from ....utils import FolderPathType, OptionalFolderPathType


class GlobusTransferClient(BaseTransferClient):
    """Automated transfers for Globus data."""

    def __init__(self, source_endpoint: str, destination_endpoint: str, cache_folder: OptionalFolderPathType = None):
        self.cache_folder = make_cache(cache_folder=cache_folder)
        # Some child kwargs may involve candidates for optional keyword argument `parent_directory` in `make_cache`
        # So in those cases do not call super().__init__(...) and remember to record the kwargs

    def fetch_total_manifest(
        self, source_directory: FolderPathType, recursive: bool = True, timeout: float = 120.0
    ) -> Dict[str, int]:
        assert HAVE_GLOBUS, "You must install the globus CLI (pip install globus-cli)!"

        recursive_flag = " --recursive" if recursive else ""
        contents = json.loads(
            deploy_process(
                command=f"globus ls -Fjson {globus_endpoint_id}:{path}{recursive_flag}",
                catch_output=True,
                timeout=timeout,
            )
        )
        files_and_sizes = {item["name"]: item["size"] for item in contents["DATA"] if item["type"] == "file"}
        return files_and_sizes

    def transfer_data(self):
        raise NotImplementedError(f"The method 'transfer_data' has not been defined for class {self.__class__}!")
