import pyvyu as pv
import os
import pkg_resources

def get_resource(file):
    """Get test resources. """
    path = os.path.join('resources', file)

    if pkg_resources.resource_exists(__name__, path):
        return pkg_resources.resource_stream(__name__, path)
    else:
        raise(Exception(f"Can't find resource: {file}"))


def test_init():
    assert 'load_opf' in dir(pv)


def test_load_sample():
    testfile = get_resource('DatavyuSampleSpreadsheet.opf')
    sheet = pv.load_opf(testfile)
    assert len(sheet.get_column_list()) == 6

    momspeech = sheet.get_column('MomSpeech')
    print([x.ordinal for x in momspeech.sorted_cells()])
    assert len(momspeech.sorted_cells()) == 20
