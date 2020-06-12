import pyvyu as pv
import pandas as pd
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
        print(f"Can't find resource: {file}")


@pytest.fixture
def sample_spreadsheet():
    return get_resource("DatavyuSampleSpreadsheet.opf")

@pytest.fixture
def trimmed_sample_spreadsheet():
    return get_resource("DatavyuSampleSpreadsheetTrimmed.opf")

@pytest.fixture
def offset():
    return pv.to_millis('00:00:38:789')

@pytest.fixture
def onset():
    return pv.to_millis('00:00:36:861')


def test_init():
    assert "load_opf" in dir(pv)


def test_load_sample(sample_spreadsheet):
    sheet = pv.load_opf(sample_spreadsheet)
    assert len(sheet.get_column_list()) == 6

    momspeech = sheet.get_column("MomSpeech")
    assert len(momspeech.sorted_cells()) == 20


def test_trim_sheet_fail(sample_spreadsheet, trimmed_sample_spreadsheet, onset, offset):
    columns = ["MomSpeech", "MomObject"]
    sheet = pv.load_opf(sample_spreadsheet)
    sheet = pv.trim_sheet(onset, offset, sheet, True, False, *columns)
    sheet_trimmed = pv.load_opf(trimmed_sample_spreadsheet)
    assert sheet != sheet_trimmed

def test_trim_sheet(sample_spreadsheet, trimmed_sample_spreadsheet, onset, offset):
    sheet = pv.load_opf(sample_spreadsheet)
    sheet = pv.trim_sheet(onset, offset, sheet, True, False)
    sheet_trimmed = pv.load_opf(trimmed_sample_spreadsheet)
    assert sheet == sheet_trimmed

def test_spreadsheet_to_df(sample_spreadsheet):
    sheet = pv.load_opf(sample_spreadsheet)
    df = sheet.to_df()

    pd.set_option("display.max_columns", None)
    log.info(df)
    assert 156 == len(df)

    ms = sheet.to_df("MomSpeech")
    log.info(ms)
    assert 20 == len(ms)


def test_json(sample_spreadsheet):
    sheet = pv.load_opf(sample_spreadsheet)
    pv.save_json(sheet, "test.json")
    json_sheet = pv.load_json("test.json")
    momspeech = json_sheet.get_column("MomSpeech")
    assert len(momspeech.sorted_cells()) == 20
    o_momspeech = sheet.get_column("MomSpeech")
    for oc, c in zip(o_momspeech.cells, momspeech.cells):
        assert all([x == y for x, y in zip(oc.get_values(), c.get_values())])
    # Cleanup
    os.remove("test.json")


@pytest.mark.skip
def test_df_to_csv(sample_spreadsheet):
    sheet = pv.load_opf(sample_spreadsheet)
    df = sheet.to_df()
    # df.to_csv('./DatavyuSampleSpreadsheet.csv')

    df = sheet.to_df("MomSpeech")
    log.info(df)
    # df.to_csv('./MomSpeech.csv')


@pytest.fixture
def rsrc_millis():
    """List of test times as milliseconds. Matches rsrc_timestamps."""
    return [
        36_000_000,
        3_600_000,
        600_000,
        60_000,
        10_000,
        1000,
        100,
        10,
        1,
        0,
        86_399_999,
        61_123,
    ]


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


def test_to_timestamp(rsrc_millis, rsrc_timestamps):
    for m, t in zip(rsrc_millis, rsrc_timestamps):
        assert t == pv.to_timestamp(m)
