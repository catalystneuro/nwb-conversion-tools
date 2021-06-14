from tempfile import mkdtemp
from shutil import rmtree
from pathlib import Path

from pynwb import NWBFile
from ndx_events import LabeledEvents

from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools import NWBConverter, TutorialRecordingInterface


def test_converter():
    test_dir = Path(mkdtemp())
    nwbfile_path = str(test_dir / "test1.nwb")

    class NdxEventsInterface(BaseDataInterface):
        def run_conversion(self, nwbfile: NWBFile):
            events = LabeledEvents(
                name="LabeledEvents",
                description="events from my experiment",
                timestamps=[0., 0.5, 0.6, 2., 2.05, 3., 3.5, 3.6, 4.],
                resolution=1e-5,
                data=[0, 1, 2, 3, 5, 0, 1, 2, 4],
                labels=["trial_start", "cue_onset", "cue_offset", "response_left", "response_right", "reward"]
            )
            nwbfile.add_acquisition(events)

    class ExtensionTestNWBConverter(NWBConverter):
        data_interface_classes = dict(Tutorial=TutorialRecordingInterface, NdxEvents=NdxEventsInterface)

    converter = ExtensionTestNWBConverter(source_data=dict())
    metadata = converter.get_metadata()
    converter.run_conversion(metadata=metadata, nwbfile_path=nwbfile_path, overwrite=True)

    rmtree(test_dir)
