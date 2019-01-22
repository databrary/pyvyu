import pyvyu as pv
import logging as log


def test_init():
    assert 'load_opf' in dir(pv)


def test_load_sample():
    sheet = pv.load_opf('./DatavyuSampleSpreadsheet.opf')
    # print(sheet.get_column_list())
    assert len(sheet.get_column_list()) == 6

    momspeech = sheet.get_column('MomSpeech')
    print([x.ordinal for x in momspeech.sorted_cells()])
    assert len(momspeech.sorted_cells()) == 20


def test_spreadsheet_to_df():
    print("Testing conversion to dataframe...")
    sheet = pv.load_opf('./DatavyuSampleSpreadsheet.opf')
    df = sheet.to_df()

    print(df)

    assert(156 == len(df))
    df.to_csv('./DatavyuSampleSpreadsheet.csv')

    df = sheet.to_df('MomSpeech')
    print(df)
    df.to_csv('./MomSpeech.csv')
