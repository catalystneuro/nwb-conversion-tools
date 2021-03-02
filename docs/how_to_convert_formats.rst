Converting data to NWB
----------------------

Below is a collection of simple conversion scripts that are all tested
against small proprietary examples files. They are all optimized to
handle very large data by iteratively steping through large files and
read/writing them one piece at a time. They also leverage lossless
compression within HDF5, which allows you to make large datasets smaller
without losing any data. We have seen this reduce large datasets by up
to 66%!

 Extracellular electrophysiology

 For extracellular electrophysiology, we use the SpikeExtractors
repository from the
`SpikeInterface <http://spikeinterface.readthedocs.io/>`__ project. To
install this package, run

.. code:: bash

    $ pip install spikeextractors

All of the format listed below are tested against example dataset in the
`ephy\_testing\_data <https://gin.g-node.org/NeuralEnsemble/ephy_testing_data>`__
GIN repository maintained by the NEO team.

.. raw:: html

   <blockquote>
   <p>
       

 Recording

.. raw:: html

   <blockquote>
   <p>
           

 Blackrock

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from spikeextractors import NwbRecordingExtractor, BlackrockRecordingExtractor

    rx = BlackrockRecordingExtractor("dataset_path")
    NwbRecordingExtractor.write_recording(rx, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

 Intan

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from spikeextractors import NwbRecordingExtractor, IntanRecordingExtractor

    rx = IntanRecordingExtractor("intan_rhd_test_1.rhd")
    NwbRecordingExtractor.write_recording(rx, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

 MEArec

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from spikeextractors import NwbRecordingExtractor, MEArecRecordingExtractor

    rx = MEArecRecordingExtractor("mearec_test_10s.h5")
    NwbRecordingExtractor.write_recording(rx, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

 Neuralynx

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from spikeextractors import NwbRecordingExtractor, NeuralynxRecordingExtractor

    rx = NeuralynxRecordingExtractor("data_directory")
    NwbRecordingExtractor.write_recording(rx, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

 Neuroscope

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from spikeextractors import NwbRecordingExtractor, NeuroscopeRecordingExtractor

    rx = NeuroscopeRecordingExtractor("data_file.dat")
    NwbRecordingExtractor.write_recording(rx, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

 OpenEphys (legacy)

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from spikeextractors import NwbRecordingExtractor, OpenEphysRecordingExtractor

    rx = OpenEphysRecordingExtractor("data_folder")
    NwbRecordingExtractor.write_recording(rx, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

 OpenEphys binary (Neuropixels)

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from spikeextractors import NwbRecordingExtractor, OpenEphysNPIXRecordingExtractor

    rx = OpenEphysNPIXRecordingExtractor("folder_path")
    NwbRecordingExtractor.write_recording(rx, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

 Phy

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from spikeextractors import NwbRecordingExtractor, PhyRecordingExtractor

    rx = PhyRecordingExtractor("folder_path")
    NwbRecordingExtractor.write_recording(rx, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

 SpikeGLX

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from spikeextractors import NwbRecordingExtractor, SpikeGLXRecordingExtractor

    rx = SpikeGLXRecordingExtractor("MySession_g0_t0.imec0.ap.bin")
    NwbRecordingExtractor.write_recording(rx, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

.. raw:: html

   </p>
   </blockquote>

 Sorting

.. raw:: html

   <blockquote>
   <p>
           

 Blackrock

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from spikeextractors import NwbSortingExtractor, BlackrockSortingExtractor

    rx = BlackrockSortingExtractor("filename")
    NwbSortingExtractor.write_sorting(rx, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

 Klusta

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from spikeextractors import NwbSortingExtractor, KlustaSortingExtractor

    rx = KlustaSortingExtractor("neo.kwik")
    NwbSortingExtractor.write_sorting(rx, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

 MEArec

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from spikeextractors import NwbSortingExtractor, MEArecSortingExtractor

    rx = MEArecSortingExtractor("mearec_test_10s.h5")
    NwbSortingExtractor.write_sorting(rx, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

 Phy

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from spikeextractors import NwbSortingExtractor, PhySortingExtractor

    rx = PhySortingExtractor("data_folder")
    NwbSortingExtractor.write_sorting(rx, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

 Plexon

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from spikeextractors import NwbSortingExtractor, 

    rx = ("File_plexon_2.plx")
    NwbSortingExtractor.write_sorting(rx, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

 Spyking Circus

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from spikeextractors import NwbSortingExtractor, 

    rx = ("file_or_folder_path")
    NwbSortingExtractor.write_sorting(rx, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

.. raw:: html

   </p>
   </blockquote>

.. raw:: html

   </p>
   </blockquote>

 Optical physiology

 For optical physiology, we use the
`RoiExtractors <https://roiextractors.readthedocs.io/en/latest/>`__
library developed by `CatalystNeuro <catalystneuro.com>`__. To install,
run

.. code:: bash

    $ pip install roiextractors

All formats listed in the optical physiology section are tested against
the
`ophys\_testing\_data <https://gin.g-node.org/CatalystNeuro/ophys_testing_data>`__
GIN repository.

.. raw:: html

   <blockquote>
   <p>
       

 Imaging

.. raw:: html

   <blockquote>
   <p>
           

 Tiff

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from roiextractors import NwbImagingExtractor, TiffImagingExtractor

    imaging_ex = TiffImagingExtractor("imaging.tiff")
    NwbImagingExtractor.write_imaging(imaging_ex, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

 Hdf5

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from roiextractors import NwbImagingExtractor, Hdf5ImagingExtractor

    imaging_ex = Hdf5ImagingExtractor("Movie.hdf5")
    NwbImagingExtractor.write_imaging(imaging_ex, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

 SBX

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from roiextractors import NwbImagingExtractor, SbxImagingExtractor

    imaging_ex = SbxImagingExtractor("scanbox_file.mat")
    NwbImagingExtractor.write_imaging(imaging_ex, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

.. raw:: html

   </p>
   </blockquote>

 Segmentation

.. raw:: html

   <blockquote>
   <p>
           

 CaImAn

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from roiextractors import NwbSegmentationExtractor, CaimanSegmentationExtractor

    seg_ex = CaimanSegmentationExtractor("caiman_analysis.hdf5")
    NwbSegmentationExtractor.write_segmentation(seg_ex, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

 Suite2p

.. raw:: html

   <blockquote>
   <p>

.. code:: python

    from roiextractors import NwbSegmentationExtractor, Suite2pSegmentationExtractor

    seg_ex = Suite2pSegmentationExtractor("segmentation_datasets/suite2p")
    NwbSegmentationExtractor.write_segmentation(seg_ex, "output_path.nwb")

.. raw:: html

   </p>
   </blockquote>

.. raw:: html

   </p>
   </blockquote>

.. raw:: html

   </p>
   </blockquote>


