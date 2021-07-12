"""Authors: Luiz Tauffer"""
import spikeextractors as se
from typing import Union
from pathlib import Path

from ..baserecordingextractorinterface import BaseRecordingExtractorInterface

PathType = Union[str, Path]


class CEDRecordingInterface(BaseRecordingExtractorInterface):
    """Primary data interface class for converting a CEDRecordingExtractor."""

    RX = se.CEDRecordingExtractor

    def __init__(self, file_path: PathType):
        super().__init__(file_path=file_path)

    @classmethod
    def get_all_channels_info(cls, file_path):
        return cls.RX.get_all_channels_info(file_path)
