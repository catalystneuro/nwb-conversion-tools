import pynwb
import numpy as np
import uuid
from datetime import datetime
from copy import deepcopy
from numbers import Real
import warnings
import distutils.version
from .json_schema import dict_deep_update
from collections import Iterable, defaultdict
from .common_writer_tools import (default_export_ops, ArrayType,
                                  _default_sorting_property_descriptions,
                                  _add_properties_to_dynamictable)
from abc import ABC, abstractmethod
import psutil
from warnings import warn
from hdmf.data_utils import DataChunkIterator
from hdmf.backends.hdf5.h5_utils import H5DataIO


class BaseNwbEphysWriter(ABC):
    def __init__(self, object_to_write, nwbfile=None, metadata=None, **kwargs):
        self.object_to_write = object_to_write
        assert nwbfile is not None and isinstance(nwbfile, pynwb.NWBFile), "Instantiate an NWBFile and pass as argument"
        self.metadata = metadata if metadata is not None else dict()
        self.nwbfile = nwbfile
        self._conversion_ops = dict(**default_export_ops(), **kwargs)

    @abstractmethod
    def get_num_segments(self):
        pass

    @abstractmethod
    def _get_traces(self, channel_ids=None, start_frame=None, end_frame=None, return_scaled=True, segment_index=None):
        pass

    @abstractmethod
    def _get_channel_ids(self):
        pass

    @abstractmethod
    def _get_channel_property_names(self):
        pass

    @abstractmethod
    def _get_channel_property_values(self, prop):
        pass

    @abstractmethod
    def _get_unit_ids(self):
        pass

    @abstractmethod
    def _get_unit_sampling_frequency(self):
        pass

    @abstractmethod
    def _get_unit_property_names(self):
        pass

    @abstractmethod
    def _get_unit_property_values(self, prop):
        pass

    @abstractmethod
    def _get_unit_feature_names(self):
        pass

    @abstractmethod
    def _get_unit_feature_values(self, prop):
        pass

    @abstractmethod
    def _get_unit_spike_train_ids(self, unit_id, start_frame=None,
                                  end_frame=None, segment_index=None):
        pass

    @abstractmethod
    def _get_unit_spike_train_times(self, unit_id, segment_index=None):
        pass

    @abstractmethod
    def _get_sampling_frequency(self):
        pass

    @abstractmethod
    def _get_num_frames(self, segment_index):
        pass

    @abstractmethod
    def _get_recording_times(self, segment_index):
        pass

    @abstractmethod
    def _get_unit_waveforms_templates(self, unit_id, mode='mean'):
        """
        Parameters
        ----------
        mode: str
            'mean', 'std
        unit_id: int
        Returns
        -------
        waveforms: np.array()
            shape: (times, channels)
        """
        pass

    @abstractmethod
    def add_to_nwb(self):
        pass

    def add_devices(self):
        """
        Auxiliary static method for nwbextractor.

        Adds device information to nwbfile object.
        Will always ensure nwbfile has at least one device, but multiple
        devices within the metadata list will also be created.

        Missing keys in an element of metadata['Ecephys']['Device'] will be auto-populated with defaults.
        """
        if self.nwbfile is not None:
            assert isinstance(self.nwbfile, pynwb.NWBFile), "'nwbfile' should be of type pynwb.NWBFile"

        # Default Device metadata
        defaults = dict(name="Device", description="Ecephys probe. Automatically generated.")

        if "Ecephys" not in self.metadata:
            self.metadata["Ecephys"] = dict()

        if "Device" not in self.metadata["Ecephys"]:
            self.metadata["Ecephys"]["Device"] = [defaults]

        for dev in self.metadata["Ecephys"]["Device"]:
            if dev.get("name", defaults["name"]) not in self.nwbfile.devices:
                self.nwbfile.create_device(**dict(defaults, **dev))

        print(self.nwbfile.devices)

    def add_electrode_groups(self):
        """
        Auxiliary method to write electrode groups.

        Adds electrode group information to nwbfile object.
        Will always ensure nwbfile has at least one electrode group.
        Will auto-generate a linked device if the specified name does not exist in the nwbfile.

        Missing keys in an element of metadata['Ecephys']['ElectrodeGroup'] will be auto-populated with defaults.

        Group names set by RecordingExtractor channel properties will also be included with passed metadata,
        but will only use default description and location.
        """
        if len(self.nwbfile.devices) == 0:
            warnings.warn("When adding ElectrodeGroup, no Devices were found on nwbfile. Creating a Device now...")
            self.add_devices()

        if "Ecephys" not in self.metadata:
            self.metadata["Ecephys"] = dict()

        channel_groups_unique = np.unique(self._get_channel_property_values('group'))

        defaults = [
            dict(
                name=str(group_id),
                description="no description",
                location="unknown",
                device=[i.name for i in self.nwbfile.devices.values()][0],
            )
            for group_id in channel_groups_unique
        ]

        if "ElectrodeGroup" not in self.metadata["Ecephys"]:
            self.metadata["Ecephys"]["ElectrodeGroup"] = defaults

        assert all(
            [isinstance(x, dict) for x in self.metadata["Ecephys"]["ElectrodeGroup"]]
        ), "Expected metadata['Ecephys']['ElectrodeGroup'] to be a list of dictionaries!"

        for grp in self.metadata["Ecephys"]["ElectrodeGroup"]:
            if grp.get("name", defaults[0]["name"]) not in self.nwbfile.electrode_groups:
                device_name = grp.get("device", defaults[0]["device"])
                if device_name not in self.nwbfile.devices:
                    self.metadata["Ecephys"]["Device"].append(dict(name=device_name))
                    self.add_devices()
                    warnings.warn(
                        f"Device '{device_name}' not detected in "
                        "attempted link to electrode group! Automatically generating."
                    )
                electrode_group_kwargs = dict(defaults[0], **grp)
                electrode_group_kwargs.update(device=self.nwbfile.devices[device_name])
                self.nwbfile.create_electrode_group(**electrode_group_kwargs)

    def add_electrodes(self):
        """
        Auxiliary static method for nwbextractor.

        Adds channels from recording object as electrodes to nwbfile object.

        Missing keys in an element of metadata['Ecephys']['ElectrodeGroup'] will be auto-populated with defaults
        whenever possible.

        If 'my_name' is set to one of the required fields for nwbfile
        electrodes (id, x, y, z, imp, loccation, filtering, group_name),
        then the metadata will override their default values.

        Setting 'my_name' to metadata field 'group' is not supported as the linking to
        nwbfile.electrode_groups is handled automatically; please specify the string 'group_name' in this case.

        If no group information is passed via metadata, automatic linking to existing electrode groups,
        possibly including the default, will occur.
        """
        if self.nwbfile.electrodes is not None:
            ids_absent = [id not in self.nwbfile.electrodes.id for id in self._get_channel_ids()]
            if not all(ids_absent):
                warnings.warn("cannot create electrodes for this recording as ids already exist")
                return

        if self.nwbfile is not None:
            assert isinstance(self.nwbfile, pynwb.NWBFile), "'nwbfile' should be of type pynwb.NWBFile"
        if self.nwbfile.electrode_groups is None or len(self.nwbfile.electrode_groups) == 0:
            self.add_electrode_groups()
        # For older versions of pynwb, we need to manually add these columns
        if distutils.version.LooseVersion(pynwb.__version__) < "1.3.0":
            if self.nwbfile.electrodes is None or "rel_x" not in self.nwbfile.electrodes.colnames:
                self.nwbfile.add_electrode_column("rel_x", "x position of electrode in electrode group")
            if self.nwbfile.electrodes is None or "rel_y" not in self.nwbfile.electrodes.colnames:
                self.nwbfile.add_electrode_column("rel_y", "y position of electrode in electrode group")

        defaults = dict(
            x=np.nan,
            y=np.nan,
            z=np.nan,
            # There doesn't seem to be a canonical default for impedence, if missing.
            # The NwbRecordingExtractor follows the -1.0 convention, other scripts sometimes use np.nan
            imp=-1.0,
            location="unknown",
            filtering="none",
            group_name="0",
        )
        if self.metadata is None: #TODO: build complete metadata from a separate class/method and fill defaults
            self.metadata = dict(Ecephys=dict())

        if "Ecephys" not in self.metadata:
            self.metadata["Ecephys"] = dict()

        if "Electrodes" not in self.metadata["Ecephys"]:
            self.metadata["Ecephys"]["Electrodes"] = []

        assert all(
            [
                isinstance(x, dict) and set(x.keys()) == set(["name", "description"])
                for x in self.metadata["Ecephys"]["Electrodes"]
            ]
        ), (
            "Expected metadata['Ecephys']['Electrodes'] to be a list of dictionaries, "
            "containing the keys 'name' and 'description'"
        )
        assert all(
            [x["name"] != "group" for x in self.metadata["Ecephys"]["Electrodes"]]
        ), "Passing metadata field 'group' is deprecated; pass group_name instead!"

        if self.nwbfile.electrodes is None:
            nwb_elec_ids = []
        else:
            nwb_elec_ids = self.nwbfile.electrodes.id.data[:]

        # 1. Build column details from RX properties: dict(name: dict(description='',data=data, index=False))
        elec_columns = defaultdict(dict)
        property_names = self._get_channel_property_names()
        exclude_names = self._conversion_ops["skip_electrode_properties"]
        for prop in property_names:
            if prop not in exclude_names:
                data = self._get_channel_property_values(prop)
                # store data after build and remap some properties to relevant nwb columns:
                if prop=="location":
                    location_map = ["rel_x", "rel_y", "rel_z"]
                    for prop_name_new, loc in zip(location_map, range(data.shape[1])):
                        elec_columns[prop_name_new].update(description=prop_name_new, data=data[:,loc], index=False)
                else:
                    prop_name_new = "location" if prop == "brain_area" else prop
                    prop_name_new = "group_name" if prop == "group" else prop
                    index = isinstance(data[0], ArrayType)
                    elec_columns[prop_name_new].update(description=prop_name_new, data=data, index=index)

        # 2. fill with provided custom descriptions
        for x in self.metadata["Ecephys"]["Electrodes"]:
            if x["name"] not in list(elec_columns):
                raise ValueError(f'"{x["name"]}" not a property of se object, set it first and rerun')
            elec_columns[x["name"]]["description"] = x["description"]

        # 3. For existing electrodes table, add the additional columns and fill with default data:
        default_updated = \
            _add_properties_to_dynamictable(self.nwbfile.electrodes, elec_columns, defaults)

        # 4. add info to electrodes table:
        for j, channel_id in enumerate(self._get_channel_ids()):
            if channel_id not in nwb_elec_ids:
                electrode_kwargs = dict(default_updated)
                electrode_kwargs.update(id=channel_id)
                for name, desc in elec_columns.items():
                    if name == "group_name":
                        # this should always be present as an electrode column, electrode_groups with that group name
                        # also should be present and created on the call to create_electrode_groups()
                        electrode_kwargs.update(
                            dict(group=self.nwbfile.electrode_groups[name], group_name=name)
                        )
                    else:
                        electrode_kwargs[name] = desc["data"][j]
                self.nwbfile.add_electrode(**electrode_kwargs)

    def add_electrical_series(self, segment_index):
        """
        Auxiliary static method for nwbextractor.

        Adds traces from recording object as ElectricalSeries to nwbfile object.

        Parameters
        ----------
        recording: RecordingExtractor
        nwbfile: NWBFile
            nwb file to which the recording information is to be added
        metadata: dict
            metadata info for constructing the nwb file (optional).
            Should be of the format
                metadata['Ecephys']['ElectricalSeries'] = {'name': my_name,
                                                            'description': my_description}
        buffer_mb: int (optional, defaults to 500MB)
            maximum amount of memory (in MB) to use per iteration of the
            DataChunkIterator (requires traces to be memmap objects)
        use_times: bool (optional, defaults to False)
            If True, the times are saved to the nwb file using recording.frame_to_time(). If False (defualut),
            the sampling rate is used.
        write_as: str (optional, defaults to 'raw')
            How to save the traces data in the nwb file. Options:
            - 'raw' will save it in acquisition
            - 'processed' will save it as FilteredEphys, in a processing module
            - 'lfp' will save it as LFP, in a processing module
        es_key: str (optional)
            Key in metadata dictionary containing metadata info for the specific electrical series
        write_scaled: bool (optional, defaults to True)
            If True, writes the scaled traces (return_scaled=True)
        compression: str (optional, defaults to "gzip")
            Type of compression to use. Valid types are "gzip" and "lzf".
            Set to None to disable all compression.
        compression_opts: int (optional, defaults to 4)
            Only applies to compression="gzip". Controls the level of the GZIP.
        iterate: bool (optional, defaults to True)
            Whether or not to use DataChunkIteration. Highly recommended for large (16+ GB) recordings.

        Missing keys in an element of metadata['Ecephys']['ElectrodeGroup'] will be auto-populated with defaults
        whenever possible.
        """
        if self.nwbfile is not None:
            assert isinstance(self.nwbfile, pynwb.NWBFile), "'nwbfile' should be of type pynwb.NWBFile!"
        assert (
            self._conversion_ops["buffer_mb"] > 10
        ), "'buffer_mb' should be at least 10MB to ensure data can be chunked!"

        if not self.nwbfile.electrodes:
            self.add_electrodes()

        if self._conversion_ops["compression"] == "lzf" and self._conversion_ops["compression_opts"] is not None:
            warn(
                f"compression_opts ({self._conversion_ops['compression_opts']})"
                "were passed, but compression type is 'lzf'! Ignoring options."
            )
            compression_opts = None

        if self._conversion_ops["write_as"] == "raw":
            eseries_kwargs = dict(
                name="ElectricalSeries_raw",
                description="Raw acquired data",
                comments="Generated from SpikeInterface::NwbRecordingExtractor",
            )
        elif self._conversion_ops["write_as"] == "processed":
            eseries_kwargs = dict(
                name="ElectricalSeries_processed",
                description="Processed data",
                comments="Generated from SpikeInterface::NwbRecordingExtractor",
            )
            # Check for existing processing module and data interface
            ecephys_mod = check_module(
                nwbfile=self.nwbfile,
                name="ecephys",
                description="Intermediate data from extracellular electrophysiology recordings, e.g., LFP.",
            )
            if "Processed" not in ecephys_mod.data_interfaces:
                ecephys_mod.add(pynwb.ecephys.FilteredEphys(name="Processed"))
        elif self._conversion_ops["write_as"] == "lfp":
            eseries_kwargs = dict(
                name="ElectricalSeries_lfp",
                description="Processed data - LFP",
                comments="Generated from SpikeInterface::NwbRecordingExtractor",
            )
            # Check for existing processing module and data interface
            ecephys_mod = check_module(
                nwbfile=self.nwbfile,
                name="ecephys",
                description="Intermediate data from extracellular electrophysiology recordings, e.g., LFP.",
            )
            if "LFP" not in ecephys_mod.data_interfaces:
                ecephys_mod.add(pynwb.ecephys.LFP(name="LFP"))

        # If user passed metadata info, overwrite defaults
        if self.metadata is not None and "Ecephys" in self.metadata:
            assert (
                self._conversion_ops["es_key"] in self.metadata["Ecephys"]
            ), f"metadata['Ecephys'] dictionary does not contain key '{self._conversion_ops['es_key']}'"
            eseries_kwargs.update(self.metadata["Ecephys"][self._conversion_ops["es_key"]])
        # update name for segment:
        name = eseries_kwargs.get('name')
        eseries_kwargs.update(name=f'{name}_segment_{segment_index}')
        # Check for existing names in nwbfile
        if self._conversion_ops["write_as"] == "raw":
            assert (
                eseries_kwargs["name"] not in self.nwbfile.acquisition
            ), f"Raw ElectricalSeries '{eseries_kwargs['name']}' is already written in the NWBFile!"
        elif self._conversion_ops["write_as"] == "processed":
            assert (
                eseries_kwargs["name"]
                not in self.nwbfile.processing["ecephys"].data_interfaces["Processed"].electrical_series
            ), f"Processed ElectricalSeries '{eseries_kwargs['name']}' is already written in the NWBFile!"
        elif self._conversion_ops["write_as"] == "lfp":
            assert (
                eseries_kwargs["name"]
                not in self.nwbfile.processing["ecephys"].data_interfaces["LFP"].electrical_series
            ), f"LFP ElectricalSeries '{eseries_kwargs['name']}' is already written in the NWBFile!"

        # Electrodes table region
        channel_ids = self._get_channel_ids()
        table_ids = [list(self.nwbfile.electrodes.id[:]).index(id) for id in channel_ids]
        electrode_table_region = self.nwbfile.create_electrode_table_region(
            region=table_ids, description="electrode_table_region"
        )
        eseries_kwargs.update(electrodes=electrode_table_region)

        # channels gains - for RecordingExtractor, these are values to cast traces to uV.
        # For nwb, the conversions (gains) cast the data to Volts.
        # To get traces in Volts we take data*channel_conversion*conversion.
        channel_conversion = self._get_channel_property_values("gain", channel_ids)
        channel_offset = self._get_channel_property_values("offset", channel_ids)
        unsigned_coercion = channel_offset / channel_conversion
        if not np.all([x.is_integer() for x in unsigned_coercion]):
            raise NotImplementedError(
                "Unable to coerce underlying unsigned data type to signed type, which is currently required for NWB "
                "Schema v2.2.5! Please specify 'write_scaled=True'."
            )
        elif np.any(unsigned_coercion != 0):
            warnings.warn(
                "NWB Schema v2.2.5 does not officially support channel offsets. The data will be converted to a signed "
                "type that does not use offsets."
            )
            unsigned_coercion = unsigned_coercion.astype(int)
        if self._conversion_ops["write_scaled"]:
            eseries_kwargs.update(conversion=1e-6)
        else:
            if len(np.unique(channel_conversion)) == 1:  # if all gains are equal
                eseries_kwargs.update(conversion=channel_conversion[0] * 1e-6)
            else:
                eseries_kwargs.update(conversion=1e-6)
                eseries_kwargs.update(channel_conversion=channel_conversion)

        trace_dtype = self._get_traces(channel_ids=channel_ids[:1], end_frame=1, segment_index=segment_index).dtype
        estimated_memory = trace_dtype.itemsize * len(self._get_channel_ids()) * \
                           self._get_num_frames(segment_index=segment_index)
        if not self._conversion_ops["iterate"] and psutil.virtual_memory().available <= estimated_memory:
            warn("iteration was disabled, but not enough memory to load traces! Forcing iterate=True.")
            iterate = True
        if self._conversion_ops["iterate"]:
            if isinstance(
                self._get_traces(end_frame=5, return_scaled=self._conversion_ops["write_scaled"],
                                 segment_index=segment_index), np.memmap
            ) and np.all(channel_offset == 0):
                n_bytes = np.dtype(self.recording.get_dtype()).itemsize
                buffer_size = int(self._conversion_ops["buffer_mb"] * 1e6) // (len(self._get_channel_ids()) * n_bytes)
                ephys_data = DataChunkIterator(
                    data=self._get_traces(return_scaled=self._conversion_ops["write_scaled"],
                                          segment_index=segment_index).T,
                    # nwb standard is time as zero axis
                    buffer_size=buffer_size,
                )
            else:

                def data_generator(recording, channels_ids, unsigned_coercion, write_scaled):
                    for i, ch in enumerate(channels_ids):
                        data = recording._get_traces(channel_ids=[ch], return_scaled=write_scaled,
                                                     segment_index=segment_index)
                        if not write_scaled:
                            data_dtype_name = data.dtype.name
                            if data_dtype_name.startswith("uint"):
                                data_dtype_name = data_dtype_name[1:]  # Retain memory of signed data type
                            data = data + unsigned_coercion[i]
                            data = data.astype(data_dtype_name)
                        yield data.flatten()

                ephys_data = DataChunkIterator(
                    data=data_generator(
                        recording=self,
                        channels_ids=channel_ids,
                        unsigned_coercion=unsigned_coercion,
                        write_scaled=self._conversion_ops["write_scaled"],
                    ),
                    iter_axis=1,  # nwb standard is time as zero axis
                    maxshape=(self._get_num_frames(segment_index=segment_index), len(self._get_channel_ids())),
                )
        else:
            ephys_data = self._get_traces(return_scaled=self._conversion_ops["write_scaled"],
                                          segment_index=segment_index).T

        eseries_kwargs.update(
            data=H5DataIO(
                ephys_data,
                compression=self._conversion_ops["compression"],
                compression_opts=self._conversion_ops["compression_opts"],
            )
        )
        if not self._conversion_ops["use_times"]:
            eseries_kwargs.update(
                starting_time=float(self._get_recording_times(segment_index=segment_index)[0]),
                rate=float(self._get_sampling_frequency()),
            )
        else:
            eseries_kwargs.update(
                timestamps=H5DataIO(
                    self._get_recording_times(segment_index=segment_index),
                    compression=self._conversion_ops["compression"],
                    compression_opts=self._conversion_ops["compression_opts"],
                )
            )

        # Add ElectricalSeries to nwbfile object
        es = pynwb.ecephys.ElectricalSeries(**eseries_kwargs)
        if self._conversion_ops["write_as"] == "raw":
            self.nwbfile.add_acquisition(es)
        elif self._conversion_ops["write_as"] == "processed":
            ecephys_mod.data_interfaces["Processed"].add_electrical_series(es)
        elif self._conversion_ops["write_as"] == "lfp":
            ecephys_mod.data_interfaces["LFP"].add_electrical_series(es)


    def add_units(self):
        """Auxilliary function for add_sorting."""
        unit_ids = self._get_unit_ids()
        fs = self._get_unit_sampling_frequency()
        if fs is None:
            raise ValueError("Writing a SortingExtractor to an NWBFile requires a known sampling frequency!")

        if 'Units' not in self.metadata:
            self.metadata['Units'] = []

        if self._conversion_ops["unit_property_descriptions"] is None:
            property_descriptions = dict(_default_sorting_property_descriptions)
        else:
            property_descriptions = dict(
                _default_sorting_property_descriptions, **self._conversion_ops["unit_property_descriptions"]
            )

        if self.nwbfile.Units is None:
            nwb_units_ids = []
        else:
            nwb_units_ids = self.nwbfile.Units.id.data[:]

        defaults = dict()
        # 1. Build column details from unit properties: dict(name: dict(description='',data=data, index=False))
        unit_columns = defaultdict(dict)
        property_names = self._get_unit_property_names()
        exclude_names = self._conversion_ops["skip_unit_properties"]
        for prop in property_names:
            if prop not in exclude_names:
                data = self._get_unit_property_values(prop)
                index = isinstance(data[0], ArrayType)
                unit_columns[prop].update(description=property_descriptions.get(prop, "No description."),
                                          data=data, index=index)

        # 2. fill with provided custom descriptions
        for x in self.metadata["Units"]:
            if x["name"] not in list(unit_columns):
                raise ValueError(f'"{x["name"]}" not a property of sorting object, set it first and rerun')
            unit_columns[x["name"]]["description"] = x["description"]

        # 3. For existing electrodes table, add the additional columns and fill with default data:
        default_updated = \
            _add_properties_to_dynamictable(self.nwbfile.Units, unit_columns, defaults)

        # 4. Add info to units table:
        for pr in unit_columns:# TODO: need to implement this in add to dynamic table.
            unit_col_args = dict(name=pr, description=property_descriptions.get(pr, "No description."))
            if pr in ["max_channel", "max_electrode"] and self.nwbfile.electrodes is not None:
                unit_col_args.update(table=self.nwbfile.electrodes)
            self.nwbfile.add_unit_column(**unit_col_args)

        for j, unit_id in enumerate(unit_ids):
            if unit_id not in nwb_units_ids:
                unit_kwargs = dict(default_updated)
                if self._conversion_ops["use_times"]:
                    spkt = self._get_unit_spike_train_times(unit_id)
                else:
                    spkt = self._get_unit_spike_train_ids(unit_id) / self._get_unit_sampling_frequency()
                unit_kwargs.update(spike_times=spkt, id=unit_id)
                for name, desc in unit_columns.items():
                    unit_kwargs[name] = desc["data"][j]
                self.nwbfile.add_unit(**unit_kwargs)

        # ADDING FEATURES:
        all_features = self._get_unit_feature_names()
        nspikes = {k: get_num_spikes(self.nwbfile.units, int(k)) for k in unit_ids}

        for ft in set(all_features) - set(self._conversion_ops["skip_unit_features"]):
            values = []
            if not ft.endswith("_idxs"):
                feat_vals = self._get_unit_feature_values(ft)
                for no, unit_id in enumerate(unit_ids):
                    if len(feat_vals[no]) < nspikes[no]:# TODO: why is this necessary
                        self._conversion_ops["skip_unit_features"].append(ft)
                        print(f"Skipping feature '{ft}' because it is not defined for all spikes.")
                        break
                        # this means features are available for a subset of spikes
                        # all_feat_vals = np.array([np.nan] * nspikes[unit_id])
                        # feature_idxs = sorting.get_unit_spike_features(unit_id, feat_name + '_idxs')
                        # all_feat_vals[feature_idxs] = feat_vals
                    else:
                        values.append(feat_vals[no])

                flatten_vals = [item for sublist in values for item in sublist]
                nspks_list = [sp for sp in nspikes.values()]
                spikes_index = np.cumsum(nspks_list).astype("int64")
                if ft in self.nwbfile.units:  # If property already exists, skip it
                    warnings.warn(f"Feature {ft} already present in units table, skipping it")
                    continue
                set_dynamic_table_property(
                    dynamic_table=self.nwbfile.units,
                    row_ids=[int(k) for k in unit_ids],
                    property_name=ft,
                    values=flatten_vals,
                    index=spikes_index,
                )


    def add_units_waveforms(self):
        if self._get_unit_waveforms_templates(unit_id=0) is not None:
            if len(self.nwbfile.units) == 0:
                warnings.warn('create a units table before adding waveforms. Skipping operation')
                return
            units = self.nwbfile.units
            waveform_metrics = ['mean','std']
            for mode in waveform_metrics:
                #construct wavforms for all units:
                templates_all = []
                for id in units.id.data:
                    templates_all.append(self._get_unit_waveforms_templates(unit_id=id, mode=mode))
                set_dynamic_table_property(
                    dynamic_table=units,
                    row_ids=units.id.data,
                    property_name=f'waveform_{mode}',
                    values=templates_all,
                )

    @abstractmethod
    def add_epochs(self):
        pass


def list_get(li: list, idx: int, default):
    """Safe index retrieval from list."""
    try:
        return li[idx]
    except IndexError:
        return default


def set_dynamic_table_property(
    dynamic_table,
    row_ids,
    property_name,
    values,
    index=False,
    default_value=np.nan,
    table=False,
    description="no description",
):
    if not isinstance(row_ids, list) or not all(isinstance(x, int) for x in row_ids):
        raise TypeError("'ids' must be a list of integers")
    ids = list(dynamic_table.id[:])
    if any([i not in ids for i in row_ids]):
        raise ValueError("'ids' contains values outside the range of existing ids")
    if not isinstance(property_name, str):
        raise TypeError("'property_name' must be a string")
    if len(row_ids) != len(values) and index is False:
        raise ValueError("'ids' and 'values' should be lists of same size")

    if index is False:
        if property_name in dynamic_table:
            for (row_id, value) in zip(row_ids, values):
                dynamic_table[property_name].data[ids.index(row_id)] = value
        else:
            col_data = [default_value] * len(ids)  # init with default val
            for (row_id, value) in zip(row_ids, values):
                col_data[ids.index(row_id)] = value
            dynamic_table.add_column(
                name=property_name, description=description, data=col_data, index=index, table=table
            )
    else:
        if property_name in dynamic_table:
            # TODO
            raise NotImplementedError
        else:
            dynamic_table.add_column(name=property_name, description=description, data=values, index=index, table=table)


def check_module(nwbfile, name: str, description: str = None):
    """
    Check if processing module exists. If not, create it. Then return module.

    Parameters
    ----------
    nwbfile: pynwb.NWBFile
    name: str
    description: str | None (optional)

    Returns
    -------
    pynwb.module
    """
    assert isinstance(nwbfile, pynwb.NWBFile), "'nwbfile' should be of type pynwb.NWBFile"
    if name in nwbfile.modules:
        return nwbfile.modules[name]
    else:
        if description is None:
            description = name
        return nwbfile.create_processing_module(name, description)


def get_num_spikes(units_table, unit_id):
    """Return the number of spikes for chosen unit."""
    ids = np.array(units_table.id[:])
    indexes = np.where(ids == unit_id)[0]
    if not len(indexes):
        raise ValueError(f"{unit_id} is an invalid unit_id. Valid ids: {ids}.")
    index = indexes[0]
    if index == 0:
        return units_table["spike_times_index"].data[index]
    else:
        return units_table["spike_times_index"].data[index] - units_table["spike_times_index"].data[index - 1]
