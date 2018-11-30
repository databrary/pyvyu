import pytest
import pyvyu

def test_load_sample():
    pyvyu.load_opf('DatavyuSampleSpreadsheet.opf')
    assert False

if __name__ == '__main__':
    pyvyu.load_opf('DatavyuSampleSpreadsheet')
