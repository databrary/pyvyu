import zipfile
import os
import sys
import re


def load_opf(filename):
    """Extract data from a .opf file and return a Spreadsheet"""

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

    with zipfile.ZipFile(filename, 'r') as zf:
        assert('db' in zf.namelist())

        # Open the db file
        with zf.open('db') as db:
            sheet = Spreadsheet()
            col = None
            ordinal_counter = 1

            for line in db:
                line_stripped = line.strip().decode('utf8')
                
                # Check type of line
                line_type, match = _parse_line(line_stripped)
                if line_type == 'column':
                    name = match.group('colname')
                    codes = [x.split('|')[0] for x in match.group('codes').split(',')]
                    # print(line_stripped)
                    # print(name)
                    # print(codes)

                    # Create new column
                    # if col is not None:
                    #     print(f"Column {col.name} has {len(col.cells)} cells.")
                    col = sheet.new_column(match.group('colname'), *codes)
                    # print(f"Created column {col.name}, with codes: {', '.join(col.codelist)}")

                    ordinal_counter = 1

                elif line_type == 'cell':
                    # print(f"{match.group('onset')}\t{match.group('offset')}\t{match.group('values')}")
                    values = match.group('values').split(',')
                    cell = col.new_cell(*values)
                    cell.onset = match.group('onset')
                    cell.offset = match.group('offset')
                    cell.ordinal = ordinal_counter
                    ordinal_counter += 1

                    # print(f"{cell.values.values()}")

                else:
                    print(f"Can't parse: {line_stripped}")
    return sheet


class Spreadsheet:
    """Collection of columns."""

    name = ''
    columns = {}

    def __init__(self):
        pass

    def new_column(self, name, *codes):
        ncol = Column(name, *codes)
        self.columns[name] = ncol
        return ncol

    def get_column_list(self):
        return [*self.columns]

    def get_column(self, name):
        return self.columns[name]

class Column:
    """Representation of a Datavyu coding pass."""

    def __init__(self, name='', *codes):
        self.name = name
        self.codelist = codes
        self.cells = []

    def new_cell(self, *values, **kwargs):
        """New cell with values in order of codelist, or defined as keyword args."""

        c = Cell()
        c.parent = self

        c.change_codes(*values)

        for code, value in kwargs.items():
            c.change_code(code, value)
        self.cells.append(c)
        return c

    def sorted_cells(self):
        return sorted(self.cells, key=lambda x: x.ordinal)


class Cell:
    """Representation of a Datavyu annotation."""

    def __init__(self, parent=None, ordinal=0, onset=0, offset=0):
        self.parent = parent
        self.values = {
            'ordinal': ordinal,
            'onset': onset,
            'offset': offset
        }

    def change_code(self, code, value):
        self.values[code] = value

    def change_codes(self, *values):
        for code, value in zip(self.parent.codelist, values):
            self.change_code(code, value)

    @property
    def ordinal(self):
        return self.values['ordinal']

    @ordinal.setter
    def ordinal(self, value):
        self.values['ordinal'] = value

    @property
    def onset(self):
        return self.values['onset']

    @onset.setter
    def onset(self, value):
        self.values['onset'] = value

    @property
    def offset(self):
        return self.values['offset']

    @offset.setter
    def offset(self, value):
        self.values['offset'] = value


# class Time:
#     time = 0
#     timestamp = '00:00:00:000'
#
#     def __init__(self, time):
#         if isinstance(time, str):
#             self.time = Time.to_millis(time)
#             self.timestamp = time
#         elif isinstance(time, int):
#             self.time = time
#             self.timestamp = Time.to_timestamp(time)
#
#     def timestamp(self):
#         factors = [60, 60, 1000, 1]
#         str = ''
#         for f in factors:
#             t = (self.time % f)
#     @staticmethod
#     def to_millis(ts):
#         factors = [60, 60, 1000, 1]
#         t = sum(a * b for a, b in zip(factors, ts.split(':')))
#         return t
