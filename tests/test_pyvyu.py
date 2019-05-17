import pyvyu as pv
import logging as log
import os
import pkg_resources
import pytest


def get_resource(file):
    """Get test resources. """
    path = os.path.join("resources", file)

    if pkg_resources.resource_exists(__name__, path):
        return pkg_resources.resource_stream(__name__, path)
    else:
        raise (Exception(f"Can't find resource: {file}"))


@pytest.fixture
def sample_spreadsheet():
    return get_resource("DatavyuSampleSpreadsheet.opf")


def test_init():
    assert "load_opf" in dir(pv)


def test_load_sample(sample_spreadsheet):
    sheet = pv.load_opf(sample_spreadsheet)
    assert len(sheet.get_column_list()) == 6

    momspeech = sheet.get_column("MomSpeech")
    assert len(momspeech.sorted_cells()) == 20


def test_spreadsheet_to_df(sample_spreadsheet):
    sheet = pv.load_opf(sample_spreadsheet)
    df = sheet.to_df()

    print(df)
    assert 156 == len(df)

    ms = sheet.to_df("MomSpeech")
    print(ms)
    assert 20 == len(ms)


def test_df_to_csv(sample_spreadsheet):
    sheet = pv.load_opf(sample_spreadsheet)
    df = sheet.to_df()
    # df.to_csv('./DatavyuSampleSpreadsheet.csv')

    df = sheet.to_df("MomSpeech")
    print(df)
    # df.to_csv('./MomSpeech.csv')


@pytest.fixture
def rsrc_millis():
    """List of test times as milliseconds. Matches rsrc_timestamps."""
    return [36_000_000, 3_600_000, 600_000, 60_000, 10_000, 1000, 100, 10, 1, 0, 86_399_999, 61_123]


@pytest.fixture
def rsrc_timestamps():
    """List of test times as Datavyu's timestamp format. Matches rsrc_millis."""
    return [
        "10:00:00:000",
        "01:00:00:000",
        "00:10:00:000",
        "00:01:00:000",
        "00:00:10:000",
        "00:00:01:000",
        "00:00:00:100",
        "00:00:00:010",
        "00:00:00:001",
        "00:00:00:000",
        "23:59:59:999",
        "00:01:01:123",
    ]


def test_to_millis(rsrc_millis, rsrc_timestamps):
    for m, t in zip(rsrc_millis, rsrc_timestamps):
        assert m == pv.to_millis(t)


#     ms = pv.to_millis("01:00:00:000")
#     assert 3600000 == ms

#     ms = pv.to_millis("00:01:00:000")
#     assert 60000 == ms

#     ms = pv.to_millis("00:00:01:000")
#     assert 1000 == ms

#     ms = pv.to_millis("00:00:00:001")
#     assert 1 == ms

#     ms = pv.to_millis("00:00:00:000")
#     assert 0 == ms

#     ms = pv.to_millis("23:59:59:999")
#     assert 86399999 == ms

#     ms = pv.to_millis("00:01:01:123")
#     assert 61123 == ms


def test_to_timestamp(rsrc_millis, rsrc_timestamps):
    for m, t in zip(rsrc_millis, rsrc_timestamps):
        assert t == pv.to_timestamp(m)
