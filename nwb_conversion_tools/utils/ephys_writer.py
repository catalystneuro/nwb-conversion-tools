from distutils.version import StrictVersion
import pynwb
from pathlib import Path
from jsonschema import validate

# import ephys writers
from .si013nwbephyswriter import SI013NwbEphysWriter
from .si090nwbephyswriter import SI090NwbEphysWriter
from .neonwbephyswriter import NEONwbEphysWriter
from nwb_conversion_tools.nwbconverter import NWBConverter
from .common_writer_tools import default_export_ops, default_export_ops_schema


def map_si_object_to_writer(object_to_write):
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
        raise Exception(f"Could not write object of type {type(object_to_write)}")
    return writer_class


def export_ecephys_to_nwb(
    object_to_write,
    nwb_file_path=None,
    nwbfile=None,
    metadata=None,
    **kwargs,
):
    """
    Writes one object to NWB.

    Supported objects are:
        - spikeinterface version <= 0.13 extractors
          (spikeextractors.RecordingExtractor / spikeextractors.SortingExtractor)
        - spikeinterface version >= 0.90 objects
          (spikeinterface.RecordingExtractor / spikeinterface.SortingExtractor / spikeinterface.WaveformExtractor)
        - NEO >= 0.10 objects
          (neo.rawIO / neo.IO)

    Parameters
    ----------
    object_to_write
    nwb_file_path
    metadata
    kwargs

    Returns
    -------

    """
    conversion_ops = dict(**default_export_ops(), **kwargs)
    conversion_opt_schema = default_export_ops_schema()
    validate(instance=conversion_ops, schema=conversion_opt_schema)

    if nwb_file_path is not None:
        nwb_file_path = Path(nwb_file_path)
        if nwb_file_path.is_file():
            raise FileExistsError(f"{nwb_file_path} is already existing!")
        assert nwb_file_path.suffix == ".nwb", f"{nwb_file_path} needs to be an .nwb file"

    if nwbfile is None:
        # instantiate
        class TempNWBConverter(NWBConverter):
            data_interface_classes = dict()

        converter = TempNWBConverter({})
        nwbfile = converter.run_conversion(metadata=metadata, save_to_file=False)

    writer_class = map_si_object_to_writer(object_to_write)
    writer = writer_class(object_to_write, nwbfile=nwbfile, metadata=metadata, **conversion_ops)
    writer.add_to_nwb()

    # handle modes and overwrite
    if nwb_file_path is not None:
        with pynwb.NWBHDF5IO(str(nwb_file_path), mode="w") as io:
            io.write(nwbfile)

    return nwbfile
