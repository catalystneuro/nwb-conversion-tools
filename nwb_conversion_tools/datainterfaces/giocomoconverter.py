from ..nwbconverter import NWBConverter
from .imagingextractorinterface import SbxImagingInterface
from .roiextractordatainterface import Suite2pSegmentationInterface
from .giocomovrdatainterface import GiocomoVRInterface


class GiocomoImagingInterface(NWBConverter):

    data_interface_classes = dict(
        SbxImagingInterface=SbxImagingInterface,
        Suite2pSegmentationInterface=Suite2pSegmentationInterface,
        GiocomoVRInterface=GiocomoVRInterface
    )