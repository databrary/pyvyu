import pyvyu as pv


def test_init():
    assert 'load_opf' in dir(pv)


def test_load_sample():
    sheet = pv.load_opf('./DatavyuSampleSpreadsheet.opf')
    # print(sheet.get_column_list())
    assert len(sheet.get_column_list()) == 6

    momspeech = sheet.get_column('MomSpeech')
    print([x.ordinal for x in momspeech.sorted_cells()])
    assert len(momspeech.sorted_cells()) == 20
