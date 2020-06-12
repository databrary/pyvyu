from .. import pyvyu as pv


class Cell:
    """Representation of a Datavyu annotation."""

    def __init__(self, parent=None, ordinal=0, onset=0, offset=0):
        self._parent = parent
        self._ordinal = ordinal
        self.onset = pv.to_millis(onset)
        self.offset = pv.to_millis(offset)
        self.values = {} if parent is None else {k: "" for k in parent.codelist}

    def __repr__(self):
        return (
                f"{self.parent.name}({self.ordinal},"
                + f"{pv.to_timestamp(self.onset)}-{pv.to_timestamp(self.offset)},"
                + ",".join(map(str, self.get_values()))
                + ")"
        )

    def change_code(self, code, value):
        if code == "ordinal":
            self._ordinal = value
        elif code == "onset":
            self.onset = pv.to_millis(value)
        elif code == "offset":
            self.offset = pv.to_millis(value)
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

    def in_range(self, onset, offset):
        if onset > self.offset or offset < self.onset:
            return False

        return True

    def trim(self, onset, offset):
        self.onset = max(onset, self.onset)
        self.offset = min(offset, self.offset)

        return self

    def shift(self, offset):
        self.onset = max(self.onset - offset, 0)
        self.offset = max(self.offset - offset, 0)
        return self

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
                f"{pv.to_timestamp(self.onset)},{pv.to_timestamp(self.offset)},"
                + "("
                + ",".join([v for v in self.get_values()])
                + ")"
        )

    def _to_json(self):
        return {
            "id": self.ordinal,
            "onset": pv.to_timestamp(self.onset),
            "offset": pv.to_timestamp(self.offset),
            "values": [v for v in self.get_values()],
        }

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.onset == other.onset and self.offset == other.offset and self.values == other.values

        return False
