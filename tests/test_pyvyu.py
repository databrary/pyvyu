from distutils import dir_util
from pytest import fixture
import pyvyu as pv
import os

@fixture
def datadir(tmpdir, request):
    """""
    Fixture responsible for searching a folder with the same name of test
    module and, if available, moving all contents to a temporary directory so
    tests can use them freely.
    Code from SO: https://stackoverflow.com/questions/29627341/pytest-where-to-store-expected-data
    """

    filename = request.module.__file__
    test_dir, _ = os.path.splitext(filename)

    if os.path.isdir(test_dir):
        dir_util.copy_tree(test_dir, str(tmpdir))

    return tmpdir

def test_init():
    assert 'load_opf' in dir(pv)


def test_load_sample(datadir):
    testfile = datadir.join('DatavyuSampleSpreadsheet.opf')
    sheet = pv.load_opf(testfile)
    # print(sheet.get_column_list())
    assert len(sheet.get_column_list()) == 6

    momspeech = sheet.get_column('MomSpeech')
    print([x.ordinal for x in momspeech.sorted_cells()])
    assert len(momspeech.sorted_cells()) == 20
