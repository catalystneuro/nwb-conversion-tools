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
