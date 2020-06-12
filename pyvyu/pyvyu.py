import zipfile
import re
import logging as log
import tempfile
import os
import json
import numbers
from math import floor
from .spreadsheet.Spreadsheet import Spreadsheet

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
    with open(filename, "r") as jf:
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
                    ordinal=ordinal,
                    onset=to_millis(onset),
                    offset=to_millis(offset),
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

def trim_sheet(onset, offset, sheet: Spreadsheet, shift = True, remove_empty = False ,*columns):
    if onset > offset:
        raise AttributeError('the Onset cannot be greater than the Offset')

    if len(columns) != 0:
        sheet = sheet.filter_columns(columns)

    sheet = sheet.trim(onset, offset, shift)

    if remove_empty:
        sheet = sheet.remove_empty_columns()

    return sheet


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

def save_json(sheet, filename, *columns):
    with open(filename, "w") as outfile:
        json.dump(sheet._to_json(), outfile, indent=4)

def save_opf(sheet, filename, overwrite_project=False, *columns):
    """
    Save sheet to file. For existing zip files, need to recreate the whole thing.
    See: https://stackoverflow.com/questions/25738523
    """

    if len(columns) == 0:
        columns = sheet.columns.keys()

    # make copy
    if os.path.exists(filename) and not overwrite_project:  # check to see if we're creating opf denovo
        tmpfd, tmpname = tempfile.mkstemp(dir=os.path.dirname(filename))
        os.close(tmpfd)

        print("tmpfd {} and tmpname {} and filename {}".format(tmpfd, tmpname, filename))

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
    else:
        with zipfile.ZipFile(filename, mode="w") as zf:
            print(zf.infolist())
            zf.writestr("db", "#4\n" + sheet._to_opfdb(columns=columns))
            zf.writestr("project", 
                    """!project
dbFile: {}
name: {}
version: 5
viewerSettings: []
""".format(filename, filename.replace(".opf", "")))


