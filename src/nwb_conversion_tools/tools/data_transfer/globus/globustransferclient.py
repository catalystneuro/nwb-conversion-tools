"""Collection of base classes for performing data transfer commands across various services."""
import json
import os
from typing import Dict

from .. import BaseTransferClient
from ..helpers import make_cache
from ...processes import deploy_process
from ....utils import FolderPathType, OptionalFolderPathType


def _have_globus():
    try:
        import globus_cli

        return True
    except ModuleNotFoundError:
        return False


def _logged_into_globus():
    # if not os.popen("globus ls 188a6110-96db-11eb-b7a9-f57b2d55370d").read():
    if not deploy_process("globus ls 188a6110-96db-11eb-b7a9-f57b2d55370d", catch_output=True):
        return False


class GlobusTransferClient(BaseTransferClient):
    """Automated transfers for Globus data."""

    installation_message = "Please install the Globus CLI to use the GlobusTransferClient! (`pip install globus-cli`)"
    logged_in_message = (
        "You must login to the Globus service through the CLI! (`globus login`, then follow instructions)"
    )

    def __init__(self, source_endpoint_id: str, destination_endpoint: str, cache_folder: OptionalFolderPathType = None):
        """
        Automatically manage Globus task submissions.

        Parameters
        ----------
        source_endpoint_id : str
          DESCRIPTION.
        destination_endpoint : str
          DESCRIPTION.
        cache_folder : OptionalFolderPathType, optional
          DESCRIPTION. The default is None.
        """
        assert _have_globus(), self.installation_message
        assert _logged_into_globus(), self.logged_in_message

        self.source_endpoint_id = source_endpoint_id
        self.cache_folder = make_cache(cache_folder=cache_folder)
        # Some child kwargs may involve candidates for optional keyword argument `parent_directory` in `make_cache`
        # So in those cases do not call super().__init__(...) and remember to record the kwargs

    def fetch_total_manifest(
        self, source_directory: FolderPathType, recursive: bool = True, timeout: float = 120.0
    ) -> Dict[str, int]:
        assert _logged_into_globus(), self.logged_in_message

        recursive_flag = " --recursive" if recursive else ""
        contents = json.loads(
            deploy_process(
                command=f"globus ls -Fjson {self.source_endpoint_id}:{source_directory}{recursive_flag}",
                catch_output=True,
                timeout=timeout,
            )
        )
        files_and_sizes = {item["name"]: item["size"] for item in contents["DATA"] if item["type"] == "file"}
        return files_and_sizes

    def transfer_data(self):
        assert _logged_into_globus(), self.logged_in_message

        pass
