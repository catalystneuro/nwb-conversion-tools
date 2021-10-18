# NWB conversion tools
[![PyPI version](https://badge.fury.io/py/nwb-conversion-tools.svg)](https://badge.fury.io/py/nwb-conversion-tools)

NWB Conversion Tools is a package for creating NWB files by converting and 
combining neural data in proprietary formats and adding essential metadata.

**Under heavy construction. API is changing rapidly.**


Features:
* Command line interface
* Python API
* Leverages SpikeExtractor to support conversion from a number or proprietary formats.

## Installation
To install **nwb-conversion-tools** directly in an existing environment:
```
$ pip install nwb-conversion-tools
```

Alternatively, to clone the repository and set up a conda environment, do:
```
$ git clone https://github.com/catalystneuro/nwb-conversion-tools
$ cd nwb-conversion-tools
$ conda env create -f make_env.yml
$ conda activate nwb_conversion_env
$ pip install .
```

## Dependencies
NWB Conversion Tools relies heavily on [SpikeExtractors](https://github.com/SpikeInterface/spikeextractors) for electrophysiology and on [ROIExtractors](https://github.com/catalystneuro/roiextractors) for optophysiology data.

You can use a graphical interface for your converter with [NWB Web GUI](https://github.com/catalystneuro/nwb-web-gui).


## Rebuilding on Read the Docs
As a maintainer, once the changes to the documentation are on the master branch, go to [https://readthedocs.org/projects/nwb-conversion-tools/](https://readthedocs.org/projects/nwb-conversion-tools/) and click "Build version". Check the console output and its log for any errors.


## Catalogue

### Extracellular Electrophysiology - Recordings, LFP, and Spike Sorted Units

#### v0.9.3
* [Buzsáki Lab](https://buzsakilab.com/wp/): [buzsaki-lab-to-nwb](https://github.com/catalystneuro/buzsaki-lab-to-nwb)
* Shenoy lab: [shenoy-lab-to-nwb](https://github.com/catalystneuro/shenoy-lab-to-nwb)

#### v0.9.2
* [Brody Lab](http://brodylab.org/): [brody-lab-to-nwb](https://github.com/catalystneuro/brody-lab-to-nwb)

#### v0.8.10
* [Feldman Lab](https://www.feldmanlab.org/): [feldman-lab-to-nwb](https://github.com/catalystneuro/feldman-lab-to-nwb)

#### v0.8.1
* Hussaini Lab: [hussaini-lab-to-nwb](https://github.com/catalystneuro/hussaini-lab-to-nwb)

#### v0.7.2
* [Movson lab](https://www.cns.nyu.edu/labs/movshonlab/): [movshon-lab-to-nwb](https://github.com/catalystneuro/movshon-lab-to-nwb)

#### v0.7.0
* [Tank Lab](https://pni.princeton.edu/faculty/david-tank): [tank-lab-to-nwb](https://github.com/catalystneuro/tank-lab-to-nwb)
* [Groh lab](https://www.uni-heidelberg.de/izn/researchgroups/groh/): [mease-lab-to-nwb](https://github.com/catalystneuro/mease-lab-to-nwb)
* [Giocomo lab](https://giocomolab.weebly.com/): [giocomo-lab-to-nwb](https://github.com/catalystneuro/giocomo-lab-to-nwb/tree/master/giocomo_lab_to_nwb/mallory21)


### Other labs that use NWB standard
* [Axel lab](https://www.axellab.columbia.edu/): [axel-lab-to-nwb](https://github.com/catalystneuro/axel-lab-to-nwb)
* [Brunton lab](https://www.eigensteve.com/): [brunton-lab-to-nwb](https://github.com/catalystneuro/brunton-lab-to-nwb)
* [Buffalo lab](https://buffalomemorylab.com/): [buffalo-lab-data-to-nwb](https://github.com/catalystneuro/buffalo-lab-data-to-nwb)
* [Jaeger lab](https://scholarblogs.emory.edu/jaegerlab/): [jaeger-lab-to-nwb](https://github.com/catalystneuro/jaeger-lab-to-nwb)
* [Tolias lab](https://toliaslab.org/): [tolias-lab-to-nwb](https://github.com/catalystneuro/tolias-lab-to-nwb)
