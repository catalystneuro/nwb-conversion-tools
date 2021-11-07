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
    object_to_write: object
        spike interface/extractors object
    nwb_file_path: str
        path to the nwbfile. if exists and overwrite is False, then it will append.
    metadata: dict
    kwargs:
        use_times (False): True then use timestamps array, else use starting time and rate for TimeSeries object in nwbfile
        write_as ("raw"): write the traces as raw or processed
        es_key (str): Key in metadata dictionary containing metadata info for the specific electrical series
        buffer_gb (float): If buffer_shape is not specified, it will be inferred as the smallest chunk below the buffer_gb threshold.
            Defaults to 1 GB.
        buffer_shape (tuple): Manually defined shape of the buffer. Defaults to None.
        chunk_mb (float): If chunk_shape is not specified, it will be inferred as the smallest chunk below the chunk_mb threshold.
            H5 reccomends setting this to around 1 MB (our default) for optimal performance.
        iterator_type ("v2"): v2 is using the custom datachunkiterator for chunking, v1 is using the built in datachunk iterator from hdf5
        chunk_shape (tuple): Manually defined shape of the chunks. Defaults to None.
        write_scaled (False): If True, writes the scaled traces (return_scaled=True)
        compression ("gzip"): Type of compression to use. Valid types are "gzip" and "lzf". Set to None to disable all compression.
        compression_opts (int): Only applies to compression="gzip". Controls the level of the GZIP.
        skip_unit_properties (list): names of unit properties to skip writing to nwbfile,
        skip_unit_features (list): names of unit features (old spikeextractors) to skip,
        skip_electrode_properties= (list): extractors' channel properties to skip,
        unit_property_descriptions(dict()): custom descriptions for the unit properties (units column in nwbfile) defaults to "no description"
        write_electrical_series (True): whether to store traces as electricalseries in nwb object.
        overwrite (True): whether to overwrite the nwbfile or not, only valid if the file path exists.

    Returns
    -------

    """
    conversion_ops = default_export_ops()
    conversion_ops.update(kwargs)
    conversion_opt_schema = default_export_ops_schema()
    validate(instance=conversion_ops, schema=conversion_opt_schema)

    if nwb_file_path is not None:
        nwb_file_path = Path(nwb_file_path)
        if nwb_file_path.is_file() and not conversion_ops["overwrite"]:
            raise FileExistsError(f"{nwb_file_path} is already existing!")
        assert nwb_file_path.suffix == ".nwb", f"{nwb_file_path} needs to be an .nwb file"

    if nwbfile is None:
        # instantiate
        class TempNWBConverter(NWBConverter):
            data_interface_classes = dict()

        converter = TempNWBConverter({})
        nwbfile = converter.run_conversion(metadata=metadata, save_to_file=False)

    writer_class = map_si_object_to_writer(object_to_write)
    writer = writer_class(object_to_write)
    writer.add_to_nwb(nwbfile=nwbfile, metadata=metadata, **conversion_ops)

    # handle modes and overwrite
    if nwb_file_path is not None:
        if nwb_file_path.is_file() and not conversion_ops["overwrite"]:
            with pynwb.NWBHDF5IO(str(nwb_file_path), mode="a") as io:
                io.write(nwbfile)
        else:
            if nwb_file_path.is_file():
                nwb_file_path.unlink()
            with pynwb.NWBHDF5IO(str(nwb_file_path), mode="w") as io:
                io.write(nwbfile)

    return nwbfile
