import json

try:
    from PIL import Image, ExifTags

    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

from ..tiff.tiffdatainterface import TiffImagingInterface
from ....utils import dict_deep_update

class ScanImageImagingInterface(TiffImagingInterface):

    def __init__(self, file_path: FilePathType, channel_names: ArrayType = None):

        assert (
            HAVE_PIL
        ), "To use the ScanImageTiffExtractor install Pillow: \n\n pip install pillow\n\n"
        image = Image.open(filename)
        image_exif = image.getexif()
        exif = {
            ExifTags.TAGS[k]: v
            for k, v in image_exif.items()
            if k in ExifTags.TAGS and type(v) is not bytes
        }
        self.image_metadata = {
            x.split("=")[0]: x.split("=")[1]
            for x in exif["ImageDescription"].split("\r")
            if "=" in x
        }

        sampling_frequency = float(self.image_description["state.acq.frameRate"])

        super().__init__(file_path=file_path, sampling_frequency=sampling_frequency, channel_names=channel_names)

    def get_metadata(self):
        session_start_time = parser.parse(
            self.image_metadata["state.internal.triggerTimeString"]
        )

        metadata = super().get_metadata()
        new_metadata = dict(
            NWBFile=dict(
                session_start_time=session_start_time),
            Ophys=dict(
                TwoPhotonSeries=dict(
                    description=json.dumps(self.image_metadata)
                )
            )
        )
        metadata = dict_deep_update(metadata, new_metadata)

        return metadata