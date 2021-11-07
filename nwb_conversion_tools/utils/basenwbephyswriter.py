"""Authors: Saksham Sharda, Alessio Buccino"""
import distutils.version
import warnings
from abc import ABC, abstractmethod
from collections import defaultdict, Iterable
from numbers import Real
from warnings import warn
from copy import deepcopy
import numpy as np
import psutil
import pynwb
from hdmf.backends.hdf5.h5_utils import H5DataIO
from hdmf.data_utils import DataChunkIterator

from .common_writer_tools import (
    default_export_ops,
    _default_sorting_property_descriptions,
    add_properties_to_dynamictable,
    set_dynamic_table_property,
    check_module,
    DynamicTableSupportedDtypes,
    get_num_spikes,
)
from .nwbephyswriterdatachunkiterator import NwbEphysWriterDataChunkIterator


class BaseNwbEphysWriter(ABC):
    def __init__(self, object_to_write, stub, stub_channels):
        self.object_to_write = object_to_write
        self.stub = stub
        self.stub_channels = stub_channels
        self.dt_column_defaults = DynamicTableSupportedDtypes
        self.nwbfile = None
        self._conversion_ops = dict()
        self.metadata = dict()

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
    def _get_dtype(self):
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
    def _get_unit_spike_train_ids(self, unit_id, start_frame=None, end_frame=None, segment_index=None):
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
    def _get_unit_waveforms_templates(self, unit_id, mode="mean"):
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
    def add_to_nwb(self, nwbfile: pynwb.NWBFile, metadata=None):
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

    def add_electrode_groups(self):
        """
        Adds electrode groups by looking for the "group" property of the channels. Overrides this with
        supplied values under metadata["Ecephys"]["ElectrodeGroup"]
        """
        if len(self.nwbfile.devices) == 0:
            warnings.warn("When adding ElectrodeGroup, no Devices were found on nwbfile. Creating a Device now...")
            self.add_devices()

        if "Ecephys" not in self.metadata:
            self.metadata["Ecephys"] = dict()

        channel_groups_unique = set(self._get_channel_property_values("group"))

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
        Adds channels from recording object as electrodes to nwbfile object.
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
            group=list(self.nwbfile.electrode_groups.values())[0],
            group_name=list(self.nwbfile.electrode_groups.values())[0].name,
        )
        if self.metadata is None:  # TODO: build complete metadata from a separate class/method and fill defaults
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
                if prop == "location":
                    location_map = ["rel_x", "rel_y", "rel_z"]
                    for prop_name_new, loc in zip(location_map, range(data.shape[1])):
                        elec_columns[prop_name_new].update(description=prop_name_new, data=data[:, loc], index=False)
                else:
                    if prop == "brain_area":
                        prop = "location"
                    elif prop == "group":
                        if "group_name" not in property_names:
                            prop = "group_name"
                        else:
                            continue
                    index = isinstance(data[0], (list, np.ndarray))
                    elec_columns[prop].update(description=prop, data=data, index=index)

        # 2. fill with provided custom descriptions
        for x in self.metadata["Ecephys"]["Electrodes"]:
            if x["name"] not in list(elec_columns):
                raise ValueError(f'"{x["name"]}" not a property of se object, set it first and rerun')
            elec_columns[x["name"]]["description"] = x["description"]

        # 3. For existing electrodes table, add the additional columns and fill with default data:
        add_properties_to_dynamictable(self.nwbfile, "electrodes", elec_columns, defaults)

        # 4. add info to electrodes table:
        for j, channel_id in enumerate(self._get_channel_ids()):
            if channel_id not in nwb_elec_ids:
                electrode_kwargs = dict(defaults)
                electrode_kwargs.update(id=channel_id)
                for name, desc in elec_columns.items():
                    if name == "group_name":
                        # this should always be present as an electrode column, electrode_groups with that group name
                        # also should be present and created on the call to create_electrode_groups()
                        group_name = str(desc["data"][j])
                        electrode_kwargs.update(
                            dict(group=self.nwbfile.electrode_groups[group_name], group_name=group_name)
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
        segment_index : int
            the index of segment (applies to the new spikeinterface version, defaults to 0 or spikeextractors)
        """
        if self.nwbfile is not None:
            assert isinstance(self.nwbfile, pynwb.NWBFile), "'nwbfile' should be of type pynwb.NWBFile!"

        if not self.nwbfile.electrodes:
            self.add_electrodes()

        if self._conversion_ops["compression"] == "lzf" and self._conversion_ops["compression_opts"] is not None:
            warn(
                f"compression_opts ({self._conversion_ops['compression_opts']})"
                "were passed, but compression type is 'lzf'! Ignoring options."
            )
            self._conversion_ops["compression_opts"] = None

        if self._conversion_ops["write_as"] == "raw":
            eseries_kwargs = dict(
                name="ElectricalSeries",
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

        # this is not needed anymore because metadata ar ehandled at class level
        # If user passed metadata info, overwrite defaults
        if self.metadata is not None and "Ecephys" in self.metadata:
            es_key = self._conversion_ops["es_key"]
            es_key = es_key if es_key is not None else eseries_kwargs["name"]
            if es_key not in self.metadata["Ecephys"]:
                warnings.warn(
                    f"metadata['Ecephys'] dictionary does not contain key '{es_key}'" f"picking default arguments"
                )
            else:
                eseries_kwargs.update(self.metadata["Ecephys"][self._conversion_ops["es_key"]])

        # update name for segment:
        if segment_index != 0:
            name = eseries_kwargs.get("name")
            eseries_kwargs.update(name=f"{name}_segment_{segment_index}")
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
        channel_conversion = np.ones(len(self._get_channel_ids()), dtype='int')
        channel_offset = np.zeros(len(self._get_channel_ids()), dtype='int')
        if "gain" in self._get_channel_property_names() and "offset" in self._get_channel_property_names():
            channel_conversion = self._get_channel_property_values("gain")
            channel_offset = self._get_channel_property_values("offset")
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

        iterator_opts = {
            i: self._conversion_ops[i] for i in ["write_scaled", "buffer_gb", "buffer_shape", "chunk_mb", "chunk_shape"]
        }
        if self._conversion_ops["iterator_type"] == "v2":
            ephys_data = NwbEphysWriterDataChunkIterator(
                ephys_writer=self, segment_index=segment_index, **iterator_opts
            )
        elif self._conversion_ops["iterator_type"] == "v1":
            if isinstance(
                self._get_traces(end_frame=5, return_scaled=iterator_opts.get("write_scaled")), np.memmap
            ) and np.all(channel_offset == 0):
                trace_dtype = self._get_traces(
                    channel_ids=channel_ids[:1], end_frame=1, segment_index=segment_index
                ).dtype
                n_bytes = trace_dtype.itemsize
                buffer_size = int(iterator_opts.get("buffer_gb", 1) * 1e9) // n_bytes
                ephys_data = DataChunkIterator(
                    data=self._get_traces(
                        return_scaled=iterator_opts.get("write_scaled")
                    ),  # nwb standard is time as zero axis
                    buffer_size=buffer_size,
                )
            else:
                raise ValueError(
                    "iterator_type='v1' only supports memmapable trace types! Use iterator_type='v2' instead."
                )
        else:
            raise NotImplementedError(
                f"iterator_type ({self._conversion_ops['iterator_type']}) should be either 'v1' or 'v2' (recommended)!"
            )

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

        if "units" not in self.metadata:
            self.metadata["units"] = []

        if self._conversion_ops["unit_property_descriptions"] is None:
            property_descriptions = dict(_default_sorting_property_descriptions)
        else:
            property_descriptions = dict(
                _default_sorting_property_descriptions, **self._conversion_ops["unit_property_descriptions"]
            )

        if self.nwbfile.units is None:
            nwb_units_ids = []
        else:
            nwb_units_ids = self.nwbfile.units.id.data[:]

        defaults = dict()
        # 1. Build column details from unit properties: dict(name: dict(description='',data=data, index=False))
        unit_columns = defaultdict(dict)
        property_names = self._get_unit_property_names()
        print(property_names)
        exclude_names = self._conversion_ops["skip_unit_properties"]
        for prop in property_names:
            if prop not in exclude_names:
                data = self._get_unit_property_values(prop)
                if len(data) == 0:
                    continue
                index = isinstance(data[0], (list, np.ndarray))
                unit_columns[prop].update(
                    description=property_descriptions.get(prop, "No description."), data=data, index=index
                )
                if prop in ["max_channel", "max_electrode"]:
                    if self.nwbfile.electrodes is None:
                        warnings.warn("first link a RX to the nwb file to create correct electrodes")
                        continue
                    assert set(data).issubset(
                        set(self.nwbfile.electrodes.id.data)
                    ), "sorting and recording extractor should be for the same data"
                    unit_columns[prop].update(table=self.nwbfile.electrodes)

        # 2. fill with provided custom descriptions
        for x in self.metadata["units"]:
            if x["name"] not in list(unit_columns):
                raise ValueError(f'"{x["name"]}" not a property of sorting object, set it first and rerun')
            unit_columns[x["name"]]["description"] = x["description"]

        # 3. For existing electrodes table, add the additional columns and fill with default data:
        add_properties_to_dynamictable(self.nwbfile, "units", unit_columns, defaults)

        # 4. Add info to units table:
        for j, unit_id in enumerate(unit_ids):
            if unit_id not in nwb_units_ids:
                unit_kwargs = dict(defaults)
                if self._conversion_ops["use_times"]:
                    spkt = self._get_unit_spike_train_times(unit_id)
                else:
                    spkt = self._get_unit_spike_train_ids(unit_id) / self._get_unit_sampling_frequency()
                unit_kwargs.update(spike_times=spkt, id=unit_id)
                for name, desc in unit_columns.items():
                    if "electrode_group" in name:
                        if self.nwbfile.electrode_groups is None or len(self.nwbfile.electrode_groups) == 0:
                            self.add_electrode_groups()
                        unit_kwargs["electrode_group"] = self.nwbfile.electrode_groups[desc["data"][j]]
                    else:
                        unit_kwargs[name] = desc["data"][j]
                self.nwbfile.add_unit(**unit_kwargs)

        # ADDING FEATURES:
        all_features = self._get_unit_feature_names()
        nspikes = {k: get_num_spikes(self.nwbfile.units, int(k)) for k in unit_ids}

        for ft in set(all_features) - set(self._conversion_ops["skip_unit_features"]):
            values = []
            if not ft.endswith("_idxs"):
                feat_vals = self._get_unit_feature_values(ft)
                if not isinstance(feat_vals[0], Iterable):
                    feat_vals = [[val] for val in feat_vals]
                for no, unit_id in enumerate(unit_ids):
                    if len(feat_vals[no]) < nspikes[unit_id]:  # TODO: why is this necessary
                        self._conversion_ops["skip_unit_features"].append(ft)
                        print(f"Skipping feature '{ft}' because it is not defined for all spikes.")
                        break
                        # this means features are available for a subset of spikes
                        # all_feat_vals = np.array([np.nan] * nspikes[unit_id])
                        # feature_idxs = sorting.get_unit_spike_features(unit_id, feat_name + '_idxs')
                        # all_feat_vals[feature_idxs] = feat_vals
                    else:
                        values.append(feat_vals[no])
                if len(values) != len(unit_ids):
                    break
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

    def add_unit_waveforms(self):
        if self._get_unit_waveforms_templates(unit_id=0):
            if len(self.nwbfile.units) == 0:
                warnings.warn("create a units table before adding waveforms. Skipping operation")
                return
            units = self.nwbfile.units
            waveform_metrics = {"mean": "mean", "std": "sd"}
            for mode in waveform_metrics:
                # construct wavforms for all units:
                templates_all = []
                for id in units.id.data:
                    templates_all.append(self._get_unit_waveforms_templates(unit_id=id, mode=mode))
                set_dynamic_table_property(
                    dynamic_table=units,
                    row_ids=units.id.data,
                    property_name=f"waveform_{waveform_metrics[mode]}",
                    values=templates_all,
                )

    @abstractmethod
    def add_epochs(self):
        pass
