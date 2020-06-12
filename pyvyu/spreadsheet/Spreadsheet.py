from ..column.Column import Column
import pandas as pd
import logging as log

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

    def filter_columns(self, *columns_name):
        if len(columns_name) != 0:
            raise AttributeError('Columns list cannot be empty')

        self.columns = {colname: col for (colname, col) in columns_name.items() if colname in columns_name}
        return self

    def remove_empty_columns(self):
        self.columns = {colname: col for (colname, col) in self.columns.items() if len(col.cells) > 0}
        return self

    def trim(self, onset, offset, shift=True):
        if onset > offset:
            raise AttributeError('the Onset cannot be greater than the Offset')

        self.columns = {colname: col.trim(onset, offset, shift) for (colname, col) in self.columns.items()}
        return self

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
        return {"passes": [self.columns[col]._to_json() for col in columns]}

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            for colname, col in self.columns.items():
                if other.columns[colname] is None or other.columns[colname] != col:
                    return False

        return True

