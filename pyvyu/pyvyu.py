import zipfile
import os
import sys
import re
import numpy as np
import pandas as pd


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
                    cell = col.new_cell(*values, onset=match.group('onset'),
                                                 offset=match.group('offset'),
                                                 ordinal=ordinal_counter)
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

    def map_columns(self, column_names):
        return [self.get_column(col) if (isinstance(col, str)) else col for col in column_names]

    def merge_columns(self, name, *columns):
        """Merge cells of the given columns into a new column."""

        if len(columns) == 0:
            columns = self.columns.values()

        cols = self.map_columns(columns)

        # Construct new column using column names and codes to make the code list.
        codes = [f'{col.name}_{codename}' for col in cols for codename in col.get_codelist()]
        # print(codes)
        ncol = Column(name, *codes)

        # Get a list of unique timestamps across all cells
        all_cells = [cell for col in cols for cell in col.cells]
        all_times = [time for cell in all_cells for time in [cell.onset, cell.offset]]
        times = sorted(set(all_times))

        # Iterate over each interval and generate row of values for that interval
        ord = 1
        for onset, offset in zip(times, times[1:]):
            ncell = ncol.new_cell(ordinal=ord, onset=onset, offset=offset)
            for col in cols:
                cell = col.cell_at(onset)
                if cell is not None:
                    for code in col.get_codelist():
                        ncell.change_code(f'{col.name}_{code}', cell.get_code(code))
            ord += 1
        return ncol

    def to_df(self, *columns):
        """Convert column set from this spreadsheet to a Pandas dataframe"""

        if len(columns) == 0:
            columns = self.columns.values()

        merge_col = self.merge_columns('temp', *columns)

        data = []
        for cell in merge_col.sorted_cells():
            data.append(cell.get_values(intrinsics=True))

        variable_list = ['onset', 'offset'].extend(merge_col.codelist)
        df = pd.DataFrame(data, columns=variable_list)
        return df

    def values_at(self, time, columns=None):
        """Find values of codes in columns at a time point."""

        if columns is None:
            columns = self.columns.values()

        return [val for cell in self.cells_at(time) for val in cell.values()]

    def cells_at(self, time, columns=None):
        """Find the cells spanning a time point."""

        if columns is None:
            columns = self.columns.values()

        cols = self.map_columns(columns)

        return [col.cell_at(time) for col in cols]


class Column:
    """Representation of a Datavyu coding pass."""

    def __init__(self, name='', *codes):
        self.name = name
        self.codelist = set(codes)
        self.cells = []

    def new_cell(self, *values, **kwargs):
        """New cell with values in order of codelist, or defined as keyword args."""

        c = Cell(parent=self)

        c.set_values(*values)

        for code, value in kwargs.items():
            c.change_code(code, value)
        self.cells.append(c)
        return c

    def sorted_cells(self):
        return sorted(self.cells, key=lambda x: x.ordinal)

    def cell_at(self, time):
        """Return a cell spanning a time point in this column, if any."""

        cell = next((cell for cell in self.cells if cell.spans(time)), None)
        return cell

    def values_at(self, time, intrinsics=False):
        cell = self.cell_at(time)
        if cell is None:
            return []
        else:
            if intrinsics is True:
                return cell.get_values(True)
            else:
                return cell.values()

    def get_codelist(self):
        return self.codelist


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

    def get_code(self, code):
        return self.values[code]

    def set_values(self, *values):
        for code, value in zip(self.parent.codelist, values):
            self.change_code(code, value)

    def get_values(self, intrinsics=False):
        """Values of this cell. Also includes ordinal, onset, and offset if intrinsics=True"""

        if intrinsics:
            return self.values.values()
        else:
            return [v for (k, v) in self.values.items() if k not in ['ordinal', 'onset', 'offset']]

    def spans(self, time):
        return self.onset <= time <= self.offset

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
