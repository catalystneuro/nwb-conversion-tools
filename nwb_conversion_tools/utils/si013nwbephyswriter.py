import uuid
from datetime import datetime
import warnings
import numpy as np
import distutils.version
from pathlib import Path
from typing import Union, Optional, List
from warnings import warn
import psutil
from collections import defaultdict
from copy import deepcopy

import pynwb
from numbers import Real
from hdmf.data_utils import DataChunkIterator
from hdmf.backends.hdf5.h5_utils import H5DataIO
from .json_schema import dict_deep_update
from .basenwbephyswriter import BaseNwbEphysWriter
from .basesinwbephyswriter import BaseSINwbEphysWriter
from .common_writer_tools import ArrayType, PathType, set_dynamic_table_property, check_module, list_get

try:
    import spikeextractors as se

    HAVE_SI013 = True
except ImportError:
    HAVE_SI013 = False


_default_sorting_property_descriptions = dict(
    isi_violation="Quality metric that measures the ISI violation ratio as a proxy for the purity of the unit.",
    firing_rate="Number of spikes per unit of time.",
    template="The extracellular average waveform.",
    max_channel="The recording channel id with the largest amplitude.",
    halfwidth="The full-width half maximum of the negative peak computed on the maximum channel.",
    peak_to_valley="The duration between the negative and the positive peaks computed on the maximum channel.",
    snr="The signal-to-noise ratio of the unit.",
    quality="Quality of the unit as defined by phy (good, mua, noise).",
    spike_amplitude="Average amplitude of peaks detected on the channel.",
    spike_rate="Average rate of peaks detected on the channel.",
)


class SI013NwbEphysWriter(BaseSINwbEphysWriter):
    """
    Class to write RecordingExtractor and SortingExtractor object from SI<=0.13 to NWB

    Parameters
    ----------
    object_to_write: se.RecordingExtractor or se.SortingExtractor
    nwb_file_path: Path type
    nwbfile: pynwb.NWBFile or None
    metadata: dict or None
    **kwargs: list kwargs and meaning
    """

    def __init__(
        self,
        object_to_write: Union[se.RecordingExtractor, se.SortingExtractor],
        nwbfile: pynwb.NWBFile = None,
        metadata: dict = None,
        **kwargs,
    ):
        assert HAVE_SI013, "spikeextractors 0.13 version not installed"
        BaseSINwbEphysWriter.__init__(self, object_to_write, nwbfile=nwbfile, metadata=metadata, **kwargs)
        if isinstance(self.object_to_write, se.RecordingExtractor):
            self.recording = self.object_to_write
        elif isinstance(self.object_to_write, se.SortingExtractor):
            self.sorting = self.object_to_write

    @staticmethod
    def supported_types():
        assert HAVE_SI013
        return (se.RecordingExtractor, se.SortingExtractor)

    def add_to_nwb(self):
        if isinstance(self.object_to_write, se.RecordingExtractor):
            self.add_recording()
        elif isinstance(self.object_to_write, se.SortingExtractor):
            self.add_sorting()

    def add_sorting(self):
        """
        Primary method for writing a SortingExtractor object to an NWBFile.

        Parameters
        ----------
        sorting: SortingExtractor
        save_path: PathType
            Required if an nwbfile is not passed. The location where the NWBFile either exists, or will be written.
        overwrite: bool
            If using save_path, whether or not to overwrite the NWBFile if it already exists.
        nwbfile: NWBFile
            Required if a save_path is not specified. If passed, this function
            will fill the relevant fields within the nwbfile. E.g., calling
            spikeextractors.NwbRecordingExtractor.add_recording(
                my_recording_extractor, my_nwbfile
            )
            will result in the appropriate changes to the my_nwbfile object.
        property_descriptions: dict
            For each key in this dictionary which matches the name of a unit
            property in sorting, adds the value as a description to that
            custom unit column.
        skip_properties: list of str
            Each string in this list that matches a unit property will not be written to the NWBFile.
        skip_features: list of str
            Each string in this list that matches a spike feature will not be written to the NWBFile.
        use_times: bool (optional, defaults to False)
            If True, the times are saved to the nwb file using sorting.frame_to_time(). If False (default),
            the sampling rate is used.
        metadata: dict
            Information for constructing the nwb file (optional).
            Only used if no nwbfile exists at the save_path, and no nwbfile was directly passed.
        """
        self.add_units()

    def _get_traces(self, channel_ids=None, start_frame=None, end_frame=None, return_scaled=True):
        return self.recording.get_traces(channel_ids=None, start_frame=None, end_frame=None, return_scaled=True)

    def _get_channel_property_names(self, chan_id):
        return self.recording.get_channel_property_names(channel_id=chan_id)

    def _get_channel_property_values(self, prop, chan_id):
        if prop == "location":
            return self.recording.get_channel_locations(channel_ids=chan_id)
        elif prop == "gain":
            return self.recording.get_channel_gains(channel_ids=chan_id)
        elif prop == "offset":
            return self.recording.get_channel_offsets(channel_ids=chan_id)
        elif prop == "group":
            return self.recording.get_channel_groups(channel_ids=chan_id)
        return self.recording.get_channel_property(channel_id=chan_id, property_name=prop)

    def _get_times(self):
        if self.recording._times is None:
            return np.range(0, self._get_num_frames() * self._get_sampling_frequency(), self._get_sampling_frequency())
        return self.recording._times

    def add_units(self):
        """Auxilliary function for add_sorting."""
        unit_ids = self.sorting.get_unit_ids()
        fs = self.sorting.get_sampling_frequency()
        if fs is None:
            raise ValueError("Writing a SortingExtractor to an NWBFile requires a known sampling frequency!")

        all_properties = set()
        all_features = set()
        for unit_id in unit_ids:
            all_properties.update(self.sorting.get_unit_property_names(unit_id))
            all_features.update(self.sorting.get_unit_spike_feature_names(unit_id))

        if self._conversion_ops["property_descriptions"] is None:
            property_descriptions = dict(_default_sorting_property_descriptions)
        else:
            property_descriptions = dict(
                _default_sorting_property_descriptions, **self._conversion_ops["property_descriptions"]
            )

        if self.nwbfile.units is None:
            # Check that array properties have the same shape across units
            property_shapes = dict()
            for pr in all_properties:
                shapes = []
                for unit_id in unit_ids:
                    if pr in self.sorting.get_unit_property_names(unit_id):
                        prop_value = self.sorting.get_unit_property(unit_id, pr)
                        if isinstance(prop_value, (int, np.integer, float, str, bool)):
                            shapes.append(1)
                        elif isinstance(prop_value, (list, np.ndarray)):
                            if np.array(prop_value).ndim == 1:
                                shapes.append(len(prop_value))
                            else:
                                shapes.append(np.array(prop_value).shape)
                        elif isinstance(prop_value, dict):
                            print(f"Skipping property '{pr}' because dictionaries are not supported.")
                            self._conversion_ops["skip_unit_properties"].append(pr)
                            break
                    else:
                        shapes.append(np.nan)
                property_shapes[pr] = shapes

            for pr in property_shapes.keys():
                elems = [elem for elem in property_shapes[pr] if not np.any(np.isnan(elem))]
                if not np.all([elem == elems[0] for elem in elems]):
                    print(f"Skipping property '{pr}' because it has variable size across units.")
                    self._conversion_ops["skip_unit_properties"].append(pr)

            write_properties = set(all_properties) - set(self._conversion_ops["skip_unit_properties"])
            for pr in write_properties:
                if pr not in property_descriptions:
                    warnings.warn(
                        f"Description for property {pr} not found in property_descriptions. "
                        f"Description for property {pr} not found in property_descriptions. "
                        "Setting description to 'no description'"
                    )
            for pr in write_properties:
                unit_col_args = dict(name=pr, description=property_descriptions.get(pr, "No description."))
                if pr in ["max_channel", "max_electrode"] and self.nwbfile.electrodes is not None:
                    unit_col_args.update(table=self.nwbfile.electrodes)
                self.nwbfile.add_unit_column(**unit_col_args)

            for unit_id in unit_ids:
                unit_kwargs = dict()
                if self._conversion_ops["use_times"]:
                    spkt = self.sorting.frame_to_time(self.sorting.get_unit_spike_train(unit_id=unit_id))
                else:
                    spkt = self.sorting.get_unit_spike_train(unit_id=unit_id) / self.sorting.get_sampling_frequency()
                for pr in write_properties:
                    if pr in self.sorting.get_unit_property_names(unit_id):
                        prop_value = self.sorting.get_unit_property(unit_id, pr)
                        unit_kwargs.update({pr: prop_value})
                    else:  # Case of missing data for this unit and this property
                        unit_kwargs.update({pr: np.nan})
                self.nwbfile.add_unit(id=int(unit_id), spike_times=spkt, **unit_kwargs)

            # Check that multidimensional features have the same shape across units
            feature_shapes = dict()
            for ft in all_features:
                shapes = []
                for unit_id in unit_ids:
                    if ft in self.sorting.get_unit_spike_feature_names(unit_id):
                        feat_value = self.sorting.get_unit_spike_features(unit_id, ft)
                        if isinstance(feat_value[0], (int, np.integer, float, str, bool)):
                            break
                        elif isinstance(feat_value[0], (list, np.ndarray)):  # multidimensional features
                            if np.array(feat_value).ndim > 1:
                                shapes.append(np.array(feat_value).shape)
                                feature_shapes[ft] = shapes
                        elif isinstance(feat_value[0], dict):
                            print(f"Skipping feature '{ft}' because dictionaries are not supported.")
                            self._conversion_ops["skip_unit_features"].append(ft)
                            break
                    else:
                        print(f"Skipping feature '{ft}' because not share across all units.")
                        self._conversion_ops["skip_unit_features"].append(ft)
                        break

            nspikes = {k: get_num_spikes(self.nwbfile.units, int(k)) for k in unit_ids}

            for ft in feature_shapes.keys():
                # skip first dimension (num_spikes) when comparing feature shape
                if not np.all([elem[1:] == feature_shapes[ft][0][1:] for elem in feature_shapes[ft]]):
                    print(f"Skipping feature '{ft}' because it has variable size across units.")
                    self._conversion_ops["skip_unit_features"].append(ft)

            for ft in set(all_features) - set(self._conversion_ops["skip_unit_features"]):
                values = []
                if not ft.endswith("_idxs"):
                    for unit_id in self.sorting.get_unit_ids():
                        feat_vals = self.sorting.get_unit_spike_features(unit_id, ft)

                        if len(feat_vals) < nspikes[unit_id]:
                            self._conversion_ops["skip_unit_features"].append(ft)
                            print(f"Skipping feature '{ft}' because it is not defined for all spikes.")
                            break
                            # this means features are available for a subset of spikes
                            # all_feat_vals = np.array([np.nan] * nspikes[unit_id])
                            # feature_idxs = sorting.get_unit_spike_features(unit_id, feat_name + '_idxs')
                            # all_feat_vals[feature_idxs] = feat_vals
                        else:
                            all_feat_vals = feat_vals
                        values.append(all_feat_vals)

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
        else:
            warnings.warn("The nwbfile already contains units. These units will not be over-written.")

    def add_epochs(self):
        """
        Auxiliary static method for nwbextractor.

        Adds epochs from recording object to nwbfile object.

        """
        if self.nwbfile is not None:
            assert isinstance(self.nwbfile, pynwb.NWBFile), "'nwbfile' should be of type pynwb.NWBFile"

        # add/update epochs
        for epoch_name in self.recording.get_epoch_names():
            epoch = self.recording.get_epoch_info(epoch_name)
            if self.nwbfile.epochs is None:
                self.nwbfile.add_epoch(
                    start_time=self.recording.frame_to_time(epoch["start_frame"]),
                    stop_time=self.recording.frame_to_time(epoch["end_frame"] - 1),
                    tags=epoch_name,
                )
            else:
                if [epoch_name] in self.nwbfile.epochs["tags"][:]:
                    ind = self.nwbfile.epochs["tags"][:].index([epoch_name])
                    self.nwbfile.epochs["start_time"].data[ind] = self.recording.frame_to_time(epoch["start_frame"])
                    self.nwbfile.epochs["stop_time"].data[ind] = self.recording.frame_to_time(epoch["end_frame"])
                else:
                    self.nwbfile.add_epoch(
                        start_time=self.recording.frame_to_time(epoch["start_frame"]),
                        stop_time=self.recording.frame_to_time(epoch["end_frame"]),
                        tags=epoch_name,
                    )


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
