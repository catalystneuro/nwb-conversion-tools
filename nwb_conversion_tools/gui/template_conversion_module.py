

def conversion_function(source_paths, f_nwb, metadata, **kwargs):
    """
    A template conversion function that can be executed from GUI.
    Write your code to create and then save an nwb file, integrating
    the metadata filled from the gui with your data.
    Parameters
    ----------
    source_paths : dict
            source_file1:
                type: 'file' OR 'folder'
                path: filename.* OR foldername
            source_file2:
                type: 'file' OR 'folder'
                path: filename.* OR foldername
    f_nwb : str
        Path to output NWB file, e.g. 'my_file.nwb'.
    metadata : dict
        data from the gui converted to a dict (.yaml source as a dictionary)
    kwargs:
        custom conditions relevant to your conversion code set as True/False from within the gui
            condition1: True
            condition2: False
    """
    #
    # **Fill your code here**
    # sample:
    print('Source files:')
    for f in source_paths:
        print(f)
    print(' ')
    print('Output file:')
    print(f_nwb)
    print(' ')
    print(kwargs)

