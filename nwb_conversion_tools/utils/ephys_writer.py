from distutils.version import StrictVersion

# import ephys writers
from .si013nwbephyswriter import SI013NwbEphysWriter
from .si090nwbephyswriter import SI090NwbEphysWriter
from .neonwbephyswriter import NEONwbEphysWriter


def export_to_nwb(objects_to_write, nwb_file_path=None, nwbfile=None, metadata=None, **kwargs):
    """
    Writes one or multiple objects to NWB.

    Supported objects are:
        - spikeinterface version <= 0.13 extractors
          (spikeextractors.RecordingExtractor / spikeextractors.SortingExtractor)
        - spikeinterface version >= 0.90 objects
          (spikeinterface.RecordingExtractor / spikeinterface.SortingExtractor / spikeinterface.WaveformExtractor)
        - NEO >= 0.10 objects
          (neo.rawIO / neo.IO)

    Parameters
    ----------
    objects_to_write
    nwb_file_path
    metadata
    kwargs

    Returns
    -------

    """
    if not isinstance(objects_to_write, list):
        objects_to_write = [objects_to_write]

    for object_to_write in objects_to_write:
        writer_class = None
        try:
            if isinstance(object_to_write, SI090NwbEphysWriter.supported_types()):
                writer_class = SI090NwbEphysWriter
        except AssertionError:
            pass
        try:
            if isinstance(object_to_write, SI013NwbEphysWriter.supported_types()):
                writer_class = SI013NwbEphysWriter
        except AssertionError:
            pass
        try:
            if isinstance(object_to_write, NEONwbEphysWriter.supported_types()):
                writer_class = NEONwbEphysWriter
        except AssertionError:
            pass

        if writer_class is None:
            raise Exception(f"Could not write object of typo {type(object_to_write)}")
        else:
            writer = writer_class(
                object_to_write, nwbfile=nwbfile, nwb_file_path=nwb_file_path, metadata=metadata, **kwargs
            )
            writer.write_to_nwb()
