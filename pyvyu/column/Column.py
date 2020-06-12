from ..cell.Cell import Cell

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

    def cell_in_range(self, onset, offset):
        cell = next((cell for cell in self.cells if cell.in_range(onset, offset)), None)
        return cell

    def trim(self, onset, offset, shift=True):
        if shift:
            self.cells = [cell.trim(onset, offset).shift(onset) for cell in self.cells if
                             cell.in_range(onset, offset)]
        else:
            self.cells = [cell.trim(onset, offset) for cell in self.cells if
                             cell.in_range(onset, offset)]

        return self

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

        header = f"{self.name} (MATRIX,true,)-" + ",".join(
            [str(c) + "|NOMINAL" for c in self.codelist]
        )
        lst = [c._to_opfdb() for c in self.cells]
        lst.insert(0, header)
        return "\n".join(lst)

    def _to_json(self):
        return {
            "name": self.name,
            "type": "MATRIX",
            "arguments": {c: "NOMINAL" for c in self.codelist},
            "cells": [c._to_json() for c in self.cells],
        }

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            for index, cell in enumerate(self.cells):
                if cell != other.cells[index]:
                    return False

        return True


