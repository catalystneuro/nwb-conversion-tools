from pynwb import NWBFile
from nwb_conversion_tools import AbfNeoDataInterface, NWBConverter
from nwb_conversion_tools.utils.conversion_tools import make_nwbfile_from_metadata
from ndx_dandi_icephys import DandiIcephysMetadata
from typing import Optional
import json
from pathlib import Path
import pandas as pd


class GuagweiConverter(NWBConverter):
    data_interface_classes = dict(AbfNeoDataInterface=AbfNeoDataInterface)

    def run_conversion(
        self, 
        metadata: Optional[dict] = None, 
        save_to_file: Optional[bool] = True, 
        nwbfile_path: Optional[str] = None, 
        overwrite: Optional[bool] = False, 
        nwbfile: Optional[NWBFile] = None, 
        conversion_options: Optional[dict] = None
    ):
        if metadata is None:
            metadata = self.get_metadata()
        nwbfile = make_nwbfile_from_metadata(metadata=metadata)

        # Add LabMetadata to nwbfile
        if "LabMetadata" in metadata:
            lab_metadata = DandiIcephysMetadata(
                # Required fields for DANDI
                cell_id=metadata["LabMetadata"].get("cell_id", ""),
                slice_id=metadata["LabMetadata"].get("slice_id", ""),
                # Lab specific metadata
                targeted_layer=metadata["LabMetadata"].get("targeted_layer", ""),
                inferred_layer=metadata["LabMetadata"].get("estimate_laminate", "")
            )
            nwbfile.add_lab_meta_data(lab_metadata)

        return super().run_conversion(metadata=metadata, save_to_file=save_to_file, nwbfile_path=nwbfile_path, overwrite=overwrite, nwbfile=nwbfile, conversion_options=conversion_options)
