Frequently Asked Questions
==========================


Why is writing so much slower than binary?
------------------------------------------

**The short answer**: nwb-conversion-tools (NCT) uses advanced writing techniques to handle dataset larger than
available RAM and to use lossless compression to reduce filesize. Both of these features will operate more slowly
when compared to naive binary read and write, and both can be turned off.

**The long answer:**

There are two distinct features of NCT that are the cause of slower writing speeds.

*1. iterative write*: NCT is often used to handle datasets that are larger than would fit into RAM. In order to handle
these datasets efficiently, data is read from the source file and written to the NWB file one section at a time. This
iteration allows NCT to be used on datasets of any size, but it also can make performance slower in some cases.

*2. chunking and compression*: HDF5 provides the ability to chunk and use lossless compression to package datasets.
Lossless compression algorithms (e.g. the default, GZIP), are applied to the data so that the volume of the dataset
on disk is minimized without changing any of the dataset values. If this were applied to the entire dataset at once,
then writing or reading data would require compressing or decompressing the entire dataset. To make this more
efficient, compressed datasets are stored in chunks, which are compressed and decompressed individually whenever any
of the data within that chunk is written or read. While this approach provides quite nice properties of compressed
datasets that still permit efficient indexing, the chunk shape, compression algorithm, and level of compression can
all have large effects on read/write speed. We have chosen reasonable defaults for all of these settings, motivated
by efficient storage of the data. These settings can be altered or disabled to achieve better writing speed.