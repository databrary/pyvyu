import zipfile
import os
import sys
import re

line_formats = {
    'column': re.compile(r'(?P<colname>\w+)\s\(.*\)\-(?P<codes>.*)'),
    'cell': re.compile(r'(?P<onset>\d{2}\:\d{2}\:\d{2}\:\d{3}),'
                       r'(?P<offset>\d{2}\:\d{2}\:\d{2}\:\d{3}),'
                       r'\((?P<values>.*)\)')
}

def _parse_line(line):
    for key, rx in line_formats.items():
        match = rx.search(line)
        if match:
            return key, match

    return None, None

# Open a zip archive
def load_opf(filename):
    with zipfile.ZipFile(filename, 'r') as zf:
        assert('db' in zf.namelist())

        # Open the db file
        with zf.open('db') as db:
            for line in db:
                l = line.strip().decode('utf8')
                print(l)

                # Check type of line
                type, match = _parse_line(l)
                if type == 'column':
                    print(f"{match.group('colname')}\t{match.group('codes')}")
                elif type == 'cell':
                    print(f"{match.group('onset')}\t{match.group('offset')}\t{match.group('values')}")
                else:
                    print("Can't parse!")

if __name__ == '__main__':
    load_opf('../tests/DatavyuSampleSpreadsheet.opf')
