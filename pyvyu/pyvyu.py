import zipfile
import re
import pandas as pd
import logging as log
import numbers
from math import floor
import tempfile
import os
import json

_line_formats = {
    "column": re.compile(r"(?P<colname>\w+)\s\(.*\)\-(?P<codes>.*)"),
    "cell": re.compile(
        r"(?P<onset>\d{2}\:\d{2}\:\d{2}\:\d{3}),"
        r"(?P<offset>\d{2}\:\d{2}\:\d{2}\:\d{3}),"
        r"\((?P<values>.*)\)"
    ),
}


def _parse_line(line):
    for key, rx in _line_formats.items():
        match = rx.search(line)
        if match:
            return key, match

    return None, None


def load_json(filename):
    with open(filename, 'r') as jf:
        sheet = Spreadsheet()
        col = None
        ordinal_counter = 1

        json_sheet = json.load(jf)
        for column in json_sheet["passes"]:
            codes = column["arguments"]
            cells = column["cells"]
            name = column["name"]
            coltype = column["type"]

            col = sheet.new_column(name, *codes)
            log.debug(
                f"Created column {col.name} with code(s): %s\n",
                ", ".join(col.codelist),
            )

            for cell in cells:
                ordinal = cell["id"]
                onset = cell["onset"]
                offset = cell["offset"]
                values = cell["values"]
                cell = col.new_cell(
                        ordinal = ordinal,
                        onset = to_millis(onset),
                        offset = to_millis(offset),
                        *values,
                )
                log.debug(f"New cell: {cell}\n")
        return sheet


def load_opf(filename):
    """Extract data from a .opf file and return a Spreadsheet"""

    with zipfile.ZipFile(filename, "r") as zf:
        assert "db" in zf.namelist()

        # Open the db file
        with zf.open("db") as db:
            sheet = Spreadsheet()
            col = None
            ordinal_counter = 1

            for line_num, line in enumerate(db):
                line_stripped = line.strip().decode("utf8")

                # Check type of line
                line_type, match = _parse_line(line_stripped)
                if line_type == "column":
                    codes = [x.split("|")[0] for x in match.group("codes").split(",")]
                    log.debug(f"Stripped line: {line_stripped}\n")

                    # Create new column
                    col = sheet.new_column(match.group("colname"), *codes)
                    log.debug(
                        f"Created column {col.name} with code(s): %s\n",
                        ", ".join(col.codelist),
                    )

                    ordinal_counter = 1

                elif line_type == "cell":
                    values = match.group("values").split(",")
                    cell = col.new_cell(
                        ordinal=ordinal_counter,
                        onset=to_millis(match.group("onset")),
                        offset=to_millis(match.group("offset")),
                        *values,
                    )
                    ordinal_counter += 1
                    log.debug(f"New cell: {cell}\n")
                else:
                    log.warning("Can't parse line %d: %s\n", line_num, line_stripped)
    return sheet


def save_json(sheet, filename, *columns):
    with open(filename, 'w') as outfile:
        json.dump(sheet._to_json(), outfile, indent=4)


def save_opf(sheet, filename, *columns):
    """
    Save sheet to file. For existing zip files, need to recreate the whole thing.
    See: https://stackoverflow.com/questions/25738523
    """

    tmpfd, tmpname = tempfile.mkstemp(dir=os.path.dirname(filename))
    os.close(tmpfd)

    # make copy
    with zipfile.ZipFile(filename, "r") as zfin:
        with zipfile.ZipFile(tmpname, "w") as zfout:
            zfout.comment = zfin.comment
            for item in zfin.infolist():
                if item.filename != "db":
                    zfout.writestr(item, zfin.read(item.filename))

    os.remove(filename)
    os.rename(tmpname, filename)

    with zipfile.ZipFile(filename, mode="a") as zf:
        zf.writestr("db", "#4\n" + sheet._to_opfdb(columns=columns))


class Spreadsheet:
    """Collection of columns."""

    name = ""
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

    def map_columns(self, *column_names):
        return [
            self.get_column(col) if (isinstance(col, str)) else col
            for col in column_names
        ]

    def merge_columns(self, name, *columns, prune=True):
        """
        Merge cells of the given columns into a new column.

        If prune is True, removes cells spanning intervals
        with no values for any codes.
        """

        if len(columns) == 0:
            columns = self.columns.values()

        cols = self.map_columns(*columns)

        # Construct new column using column names and codes to make the code list.
        codes = [
            f"{col.name}_{codename}"
            for col in cols
            for codename in (["ordinal"] + col.codelist)
        ]
        ncol = Column(name, *codes)

        # Get a list of unique timestamps across all cells
        all_cells = [cell for col in cols for cell in col.cells]
        unique_times = list(
            dict.fromkeys(
                [time for cell in all_cells for time in [cell.onset, cell.offset]]
            )
        )

        # Get times of point cells (onset == offset)
        point_times = list(
            dict.fromkeys(
                [
                    cell.onset
                    for cell in filter(lambda x: x.onset == x.offset, all_cells)
                ]
            )
        )

        times = sorted(
            set(unique_times + [x + 1 for x in point_times])
        )  # this should put a time 1 ms after each of the point times
        log.debug(times)

        # Iterate over each interval and generate row of values for that interval
        ordinal = 1
        prev_time = times[0]
        for time in times[1:]:
            onset = prev_time
            offset = time
            ncell = ncol.new_cell(ordinal=ordinal, onset=onset, offset=offset)
            valid_cells = 0  # num cols with data in interval
            for col in cols:
                cell = col.cell_at(onset)
                if cell is not None:
                    # Don't print point cells unless point region
                    if onset != offset and cell.onset == cell.offset:
                        continue
                    for code in ["ordinal"] + col.codelist:
                        ncell.change_code(f"{col.name}_{code}", cell.get_code(code))
                    valid_cells += 1
            ordinal += 1
            prev_time = offset + 1

            # Remove this cell if empty and we are pruning
            if prune and ncell.isempty():
                ncol.cells.remove(ncell)
                ordinal -= 1

        return ncol

    def to_df(self, *columns):
        """Convert column set from this spreadsheet to a Pandas dataframe"""

        if len(columns) == 0:
            columns = self.columns.values()

        merge_col = self.merge_columns("temp", *columns)
        log.debug(merge_col)

        variable_list = ["ordinal", "onset", "offset"] + merge_col.codelist
        data = [cell.get_values(intrinsics=True) for cell in merge_col.sorted_cells()]
        df = pd.DataFrame(data, columns=variable_list)
        df.set_index("ordinal", inplace=True)
        return df

    def values_at(self, time, *columns):
        """Find values of codes in columns at a time point."""

        if len(columns) == 0:
            columns = self.columns.values()

        return [val for cell in self.cells_at(time, *columns) for val in cell.values()]

    def cells_at(self, time, *columns):
        """Find the cells spanning a time point."""

        if len(columns) == 0:
            columns = self.columns.values()

        cols = self.map_columns(*columns)

        return [col.cell_at(time) for col in cols]

    def _to_opfdb(self, columns=columns.keys()):
        """Converts to .opf compatible string."""
        return "\n".join([self.columns[col]._to_opfdb() for col in columns])

    def _to_json(self, columns=columns.keys()):
        return {"passes" : [self.columns[col]._to_json() for col in columns]}


class Column:
    """Representation of a Datavyu coding pass."""

    def __init__(self, name="", *codes):
        self.name = name
        self.codelist = list(codes)
        self.cells = []

    def new_cell(self, *values, **kwargs):
        """New cell with values in order of codelist, or defined as keyword args."""

        c = Cell(parent=self)

        c.set_values(*values)

        for code, value in kwargs.items():
            c.change_code(code, value)

        # Insert '' for undefined codes
        for code in self.codelist - c.values.keys():
            c.change_code(code, "")

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

    def __repr__(self):
        return (
            f"{self.name}("
            + ",".join(self.codelist)
            + "):\n["
            + "\n".join(map(str, self.sorted_cells()))
            + "]"
        )

    def _to_opfdb(self):
        """Converts to .opf compatible string."""

        header = f"{self.name} (MATRIX,false,)-" + ",".join(
            [str(c) + "|NOMINAL" for c in self.codelist]
        )
        lst = [c._to_opfdb() for c in self.cells]
        lst.insert(0, header)
        return "\n".join(lst)

    def _to_json(self):
        return {"name": self.name,
                "type": "MATRIX",
                "arguments": {c : "NOMINAL" for c in self.codelist},
                "cells": [c._to_json() for c in self.cells]}


class Cell:
    """Representation of a Datavyu annotation."""

    def __init__(self, parent=None, ordinal=0, onset=0, offset=0):
        self._parent = parent
        self._ordinal = ordinal
        self.onset = to_millis(onset)
        self.offset = to_millis(offset)
        self.values = {} if parent is None else {k: "" for k in parent.codelist}

    def __repr__(self):
        return (
            f"{self.parent.name}({self.ordinal},"
            + f"{to_timestamp(self.onset)}-{to_timestamp(self.offset)},"
            + ",".join(map(str, self.get_values()))
            + ")"
        )

    def change_code(self, code, value):
        if code == "ordinal":
            self._ordinal = value
        elif code == "onset":
            self.onset = to_millis(value)
        elif code == "offset":
            self.offset = to_millis(value)
        elif code in self.values.keys():
            self.values[code] = value
        else:
            raise Exception(f"Cell does not have code: {code}")

    def get_code(self, code):
        if code == "ordinal":
            return self._ordinal
        elif code == "onset":
            return self.onset
        elif code == "offset":
            return self.offset
        elif code in self.values.keys():
            return self.values[code]
        else:
            raise Exception(f"Cell does not contain code: {code}")

    def set_values(self, *values):
        for code, value in zip(self.parent.codelist, values):
            self.change_code(code, value)

    def get_values(self, intrinsics=False, *codes):
        """
        Values of this cell.
        Also includes ordinal, onset, and offset if intrinsics=True
        """

        if len(codes) == 0:
            codes = self.parent.codelist

        if intrinsics:
            codes = ["ordinal", "onset", "offset"] + codes

        return [self.get_code(c) for c in codes]

    def spans(self, time):
        return self.onset <= time <= self.offset

    def isempty(self):
        """ Return true if all code values are "" or null"""
        return all(v == "" or v is None for v in self.values.values())

    @property
    def parent(self):
        return self._parent

    @property
    def ordinal(self):
        return self._ordinal

    def _to_opfdb(self):
        return (
            f"{to_timestamp(self.onset)},{to_timestamp(self.offset)},"
            + "("
            + ",".join([v for v in self.get_values()])
            + ")"
        )

    def _to_json(self):
        return {"id": self.ordinal,
                "onset": to_timestamp(self.onset),
                "offset": to_timestamp(self.offset),
                "values": [v for v in self.get_values()]
            }


def to_millis(timestamp):
    if isinstance(timestamp, numbers.Number):
        return timestamp
    ms = 0
    factors = [1, 60, 60, 1000]
    parts = timestamp.split(":")
    for factor, part in zip(factors, parts):
        ms *= factor
        ms += int(part)

    log.debug(f"{timestamp} converted to: {ms}")
    return ms


def to_timestamp(millis):
    factors = [1000, 60, 60, 24]
    ms = millis
    parts = []
    for factor in factors:
        parts.append(ms % factor)
        ms = floor(ms / factor)
    parts.reverse()

    ts = "{:02d}:{:02d}:{:02d}:{:03d}".format(*parts)
    log.debug(f"{millis} converted to: {ts}")
    return ts
