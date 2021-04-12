"""Authors: Cody Baker and Ben Dichter."""
from pathlib import Path
import numpy as np

import spikeextractors as se

from ..baserecordingextractorinterface import BaseRecordingExtractorInterface
from ..baselfpextractorinterface import BaseLFPExtractorInterface
from ..basesortingextractorinterface import BaseSortingExtractorInterface

try:
    from lxml import etree as et
    HAVE_LXML = True
except ImportError:
    HAVE_LXML = False
INSTALL_MESSAGE = "Please install lxml to use this extractor!"


def get_xml(xml_file_path: str):
    """Auxiliary function for retrieving root of xml."""
    root = et.parse(xml_file_path).getroot()
    return root


def get_shank_channels(xml_file_path: str, sort: bool = False):
    """
    Auxiliary function for retrieving the list of structured shank-only channels.

    Attempts to retrieve these first from the spikeDetection sub-field in the event that spike sorting was performed on
    the raw data. In the event that spike sorting was not performed, it then retrieves only the anatomicalDescription.
    """
    root = get_xml(xml_file_path)
    try:
        shank_channels = [
            [int(channel.text) for channel in group.find('channels')]
            for group in root.find('spikeDetection').find('channelGroups').findall('group')
        ]
    except (TypeError, AttributeError):
        shank_channels = [
            [int(channel.text) for channel in group.findall('channel')]
            for group in root.find('anatomicalDescription').find('channelGroups').findall('group')
        ]

    if sort:
        shank_channels = sorted(np.concatenate(shank_channels))
    return shank_channels


class NeuroscopeRecordingInterface(BaseRecordingExtractorInterface):
    """Primary data interface class for converting a NeuroscopeRecordingExtractor."""

    RX = se.NeuroscopeRecordingExtractor

    @staticmethod
    def get_ecephys_metadata(xml_file_path: str):
        """
        Auto-populates ecephys metadata from the xml_file_path inferred.

        Though this is the same function called by the non-static get_metadata of any NeuroscopeRecordingInterface
        object, this was made static to be usable by other interfaces that require upstream ecephys metadata to be
        written to the NWBFile.
        """
        session_path = Path(xml_file_path).parent
        session_id = session_path.stem
        shank_channels = get_shank_channels(xml_file_path)

        ecephys_metadata = dict(
            Ecephys=dict(
                Device=[
                    dict(
                        description=session_id + '.xml'
                    )
                ],
                ElectrodeGroup=[
                    dict(
                        name=f'shank{n + 1}',
                        description=f"shank{n + 1} electrodes"
                    )
                    for n, _ in enumerate(shank_channels)
                ],
                Electrodes=[
                    dict(
                        name='shank_electrode_number',
                        description="0-indexed channel within a shank.",
                        data=[x for channels in shank_channels for x, _ in enumerate(channels)]
                    ),
                    dict(
                        name='group_name',
                        description="The name of the ElectrodeGroup this electrode is a part of.",
                        data=[f"shank{n + 1}" for n, channels in enumerate(shank_channels) for _ in channels]
                    )
                ]
            )
        )
        return ecephys_metadata

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subset_channels = get_shank_channels(
            xml_file_path=self.source_data["file_path"].replace(".dat", ".xml"),
            sort=True
        )

    def get_metadata(self):
        """Retrieve Ecephys metadata specific to the Neuroscope format."""
        metadata = NeuroscopeRecordingInterface.get_ecephys_metadata(
            xml_file_path=self.source_data["file_path"].replace(".dat", ".xml")
        )
        metadata['Ecephys'].update(
            ElectricalSeries=dict(
                name='ElectricalSeries',
                description="Raw acquisition traces."
            )
        )
        return metadata


class NeuroscopeMultiRecordingTimeInterface(BaseRecordingExtractorInterface):
    """Primary data interface class for converting a NeuroscopeMultiRecordingTimeExtractor."""

    RX = se.NeuroscopeMultiRecordingTimeExtractor

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subset_channels = get_shank_channels(
            xml_file_path=self.source_data["file_path"].replace(".dat", ".xml"),
            sort=True
        )

    def get_metadata(self):
        metadata = NeuroscopeRecordingInterface.get_ecephys_metadata(
            xml_file_path=self.source_data["file_path"].replace(".dat", ".xml")
        )
        metadata['Ecephys'].update(
            ElectricalSeries=dict(
                name='ElectricalSeries',
                description="Raw acquisition traces."
            )
        )
        return metadata


class NeuroscopeLFPInterface(BaseLFPExtractorInterface):
    """Primary data interface class for converting Neuroscope LFP data."""

    RX = se.NeuroscopeRecordingExtractor

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subset_channels = get_shank_channels(
            xml_file_path=self.source_data["file_path"].replace(Path(self.source_data["file_path"]).suffix, ".xml"),
            sort=True
        )

    def get_metadata(self):
        metadata = NeuroscopeRecordingInterface.get_ecephys_metadata(
            xml_file_path=self.source_data["file_path"].replace(Path(self.source_data["file_path"]).suffix, ".xml")
        )
        metadata['Ecephys'].update(
            LFPElectricalSeries=dict(
                name="LFP",
                description="Local field potential signal."
            )
        )
        return metadata


class NeuroscopeSortingInterface(BaseSortingExtractorInterface):
    """Primary data interface class for converting a NeuroscopeSortingExtractor."""

    SX = se.NeuroscopeMultiSortingExtractor

    def get_metadata(self):
        session_path = Path(self.source_data["folder_path"])
        session_id = session_path.name
        metadata = NeuroscopeRecordingInterface.get_ecephys_metadata(
            xml_file_path=str(session_path / f"{session_id}.xml")
        )
        metadata.update(UnitProperties=[])
        return metadata
