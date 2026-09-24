"""
Safe Pandas Fallback for Windows 11 Smart App Control environments.
If pandas C-extension DLLs (such as parsers.cp311-win_amd64.pyd) are blocked by OS policy,
this pure-Python replacement implements the exact DataFrame and read_csv subset used by ShramRakshak.
"""

import csv
import io
from typing import List, Dict, Any, Optional, Union

def isna(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, float) and val != val: # NaN
        return True
    s = str(val).strip()
    return s == "" or s.lower() in ("nan", "none", "null")

def notnull(val: Any) -> bool:
    return not isna(val)

isnull = isna

class Index(list):
    def tolist(self) -> List[str]:
        return list(self)

class StringAccessor:
    def __init__(self, series: 'Series'):
        self._series = series

    def strip(self) -> 'Series':
        return Series([str(x).strip() if x is not None else "" for x in self._series._data])

    def lower(self) -> 'Series':
        return Series([str(x).lower() if x is not None else "" for x in self._series._data])

class Series:
    def __init__(self, data: List[Any], name: Optional[str] = None):
        self._data = list(data)
        self.name = name

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, idx: Union[int, 'Series', List[bool]]) -> Any:
        if isinstance(idx, int):
            return self._data[idx]
        if isinstance(idx, (Series, list)):
            mask = list(idx)
            return Series([item for item, m in zip(self._data, mask) if m])
        return self._data[idx]

    def isnull(self) -> 'Series':
        return Series([isna(x) for x in self._data])

    def isna(self) -> 'Series':
        return self.isnull()

    def notnull(self) -> 'Series':
        return Series([notnull(x) for x in self._data])

    def sum(self) -> int:
        return sum(1 for x in self._data if bool(x))

    def astype(self, t: Any) -> 'Series':
        return Series([str(x) if x is not None else "" for x in self._data])

    @property
    def str(self) -> StringAccessor:
        return StringAccessor(self)

    @property
    def shape(self):
        return (len(self._data),)

    def unique(self) -> List[Any]:
        seen = set()
        out = []
        for x in self._data:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    def to_list(self) -> List[Any]:
        return list(self._data)

    def tolist(self) -> List[Any]:
        return list(self._data)

    def __eq__(self, other: Any) -> 'Series':
        if isinstance(other, Series):
            return Series([a == b for a, b in zip(self._data, other._data)])
        return Series([a == other for a in self._data])

    def __ne__(self, other: Any) -> 'Series':
        if isinstance(other, Series):
            return Series([a != b for a, b in zip(self._data, other._data)])
        return Series([a != other for a in self._data])

class DataFrame:
    def __init__(self, data: Optional[Union[List[Dict[str, Any]], Dict[str, List[Any]]]] = None, columns: Optional[List[str]] = None):
        self._rows: List[Dict[str, Any]] = []
        if isinstance(data, list):
            self._rows = [dict(r) for r in data]
            if columns:
                self.columns = Index(columns)
            elif self._rows:
                self.columns = Index(self._rows[0].keys())
            else:
                self.columns = Index([])
        elif isinstance(data, dict):
            self.columns = Index(data.keys())
            n = len(next(iter(data.values()))) if data else 0
            self._rows = [{col: data[col][i] for col in self.columns} for i in range(n)]
        else:
            self.columns = Index(columns) if columns else Index([])
            self._rows = []

    def __len__(self) -> int:
        return len(self._rows)

    @property
    def shape(self):
        return (len(self._rows), len(self.columns))

    def __contains__(self, col: str) -> bool:
        return col in self.columns

    def __getitem__(self, key: Union[str, Series, List[bool]]) -> Any:
        if isinstance(key, str):
            vals = [r.get(key) for r in self._rows]
            return Series(vals, name=key)
        if isinstance(key, (Series, list)):
            mask = list(key)
            filtered = [r for r, m in zip(self._rows, mask) if m]
            return DataFrame(filtered, columns=self.columns)
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any):
        if key not in self.columns:
            self.columns.append(key)
        if isinstance(value, (Series, list)):
            vals = list(value)
            for i, r in enumerate(self._rows):
                r[key] = vals[i] if i < len(vals) else None
        else:
            for r in self._rows:
                r[key] = value

    def iterrows(self):
        for idx, r in enumerate(self._rows):
            yield idx, r

    def dropna(self, subset: Optional[List[str]] = None) -> 'DataFrame':
        check_cols = subset or self.columns
        res = []
        for r in self._rows:
            if not any(isna(r.get(c)) for c in check_cols if c in r):
                res.append(r)
        return DataFrame(res, columns=self.columns)

    def duplicated(self, subset: Optional[List[str]] = None) -> Series:
        check_cols = subset or self.columns
        seen = set()
        dups = []
        for r in self._rows:
            key = tuple(str(r.get(c, "")).strip().lower() for c in check_cols)
            if key in seen:
                dups.append(True)
            else:
                seen.add(key)
                dups.append(False)
        return Series(dups)

    def fillna(self, val: Any) -> 'DataFrame':
        res = []
        for r in self._rows:
            new_r = {k: (val if isna(v) else v) for k, v in r.items()}
            res.append(new_r)
        return DataFrame(res, columns=self.columns)

    def copy(self) -> 'DataFrame':
        return DataFrame([dict(r) for r in self._rows], columns=list(self.columns))

    def head(self, n: int = 5) -> 'DataFrame':
        return DataFrame(self._rows[:n], columns=self.columns)

    def to_dict(self, orient: str = "records") -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        if orient == "records":
            return [dict(r) for r in self._rows]
        return {c: [r.get(c) for r in self._rows] for c in self.columns}

def read_csv(filepath_or_buffer: Any, **kwargs) -> DataFrame:
    if isinstance(filepath_or_buffer, bytes):
        text = filepath_or_buffer.decode('utf-8', errors='replace')
        f = io.StringIO(text)
    elif hasattr(filepath_or_buffer, 'read'):
        raw = filepath_or_buffer.read()
        if isinstance(raw, bytes):
            text = raw.decode('utf-8', errors='replace')
        else:
            text = str(raw)
        f = io.StringIO(text)
    elif isinstance(filepath_or_buffer, str):
        if '\n' in filepath_or_buffer:
            f = io.StringIO(filepath_or_buffer)
        else:
            f = open(filepath_or_buffer, 'r', encoding='utf-8', errors='replace')
    else:
        f = filepath_or_buffer

    reader = csv.reader(f)
    try:
        header = next(reader)
    except StopIteration:
        return DataFrame([])

    # Clean header names
    header = [h.strip() for h in header]
    rows = []
    for r in reader:
        if not r or not any(x.strip() for x in r):
            continue
        row_dict = {}
        for i, col in enumerate(header):
            row_dict[col] = r[i] if i < len(r) else None
        rows.append(row_dict)

    if hasattr(f, 'close') and not isinstance(filepath_or_buffer, io.StringIO):
        try:
            f.close()
        except Exception:
            pass

    return DataFrame(rows, columns=header)
