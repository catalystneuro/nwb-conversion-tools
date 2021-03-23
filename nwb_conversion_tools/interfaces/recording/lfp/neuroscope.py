import spikeextractors as se

from nwb_conversion_tools.interfaces.recording.lfp.base_lfp import BaseLFPExtractorInterface
from nwb_conversion_tools.interfaces.recording.neuroscope import NeuroscopeRecordingInterface, get_shank_channels, get_xml_file_path


class NeuroscopeLFPInterface(BaseLFPExtractorInterface):
    """Primary data interface class for converting Neuroscope LFP data."""

    RX = se.NeuroscopeRecordingExtractor

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subset_channels = get_shank_channels(
            xml_file_path=get_xml_file_path(data_file_path=self.source_data['file_path']),
            sort=True
        )

    def get_metadata(self):
        """Retrieve Ecephys metadata specific to the Neuroscope format."""
        metadata = NeuroscopeRecordingInterface.get_ecephys_metadata(
            xml_file_path=get_xml_file_path(data_file_path=self.source_data['file_path'])
        )
        metadata['Ecephys'].update(
            LFPElectricalSeries=dict(
                name="LFP",
                description="Local field potential signal."
            )
        )

        return metadata