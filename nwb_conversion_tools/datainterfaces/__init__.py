from .neuroscopedatainterface import NeuroscopeRecordingInterface, NeuroscopeSortingInterface
from .spikeglxdatainterface import SpikeGLXRecordingInterface
from .sipickledatainterfaces import SIPickleRecordingExtractorInterface, SIPickleSortingExtractorInterface
from .intandatainterface import IntanRecordingInterface
from .ceddatainterface import CEDRecordingInterface
from .cellexplorerdatainterface import CellExplorerSortingInterface

interface_list = [
    NeuroscopeRecordingInterface,
    NeuroscopeSortingInterface,
    SpikeGLXRecordingInterface,
    SIPickleRecordingExtractorInterface,
    SIPickleSortingExtractorInterface,
    IntanRecordingInterface,
    CEDRecordingInterface,
    CellExplorerSortingInterface
]
