"""Utils functions dedicated to interacting with the polars library."""

from functools import reduce
from pathlib import Path
from typing import Optional

import polars as pl

from neuro import DATES_CSV, ROOT_DIR, SONGS_CSV, SONGS_DB
from neuro.utils import MP3GainMode, MP3ModeTuple


def flag_expr(flag: str) -> pl.Expr:
    """Small helper function to avoid heavy expressions.

    Args:
        flag (str): Which flag to consider.

    Returns:
        pl.Expr: An expression representing the rows that contain the given flag in the "Flags" column.
    """
    return pl.col("Flags").str.contains(flag)


def stack_or(flag_list: list[str]) -> pl.Expr:
    """Applies a reduction on conditions. It's literally `any(exprs)`. But the `any` function in \
        polars gives me the felling that it's not doing that.

    Args:
        flag_list (list[str]): list of flags as strings.

    Returns:
        pl.Expr: polars expression true if any of the flags is true.
    """
    return reduce(
        lambda acc, val: acc | flag_expr(val),
        flag_list,
        pl.lit(False),
    )


def load_db(as_db: bool = True, root: Path = ROOT_DIR) -> pl.DataFrame:
    """Wrapper to loader the songs DB regardless of the backend format.

    Args:
        as_db (bool, optional): If True, will look for a `.db` database, otherwise \
            looks for a CSV file. Defaults to True.
        root (Path, optional): Root dir to search the database from.Defaults to ROOT_DIR.

    Returns:
        pl.DataFrame: A polars DataFrame, regardless of the storage format.
    """
    if as_db:
        REQ = "SELECT * FROM Songs"
        return pl.read_database_uri(REQ, f"sqlite://{root / SONGS_DB}")
    else:
        return pl.read_csv(root / SONGS_CSV)


def load_dates(as_db: bool = True) -> pl.DataFrame:
    """Same as `load_db`. Loads dates database regardless of format.

    Args:
        as_db (bool, optional): Loads from a `.db` file or not. Defaults to True.

    Returns:
        pl.DataFrame: Polars DataFrame with dates.
    """
    if as_db:
        REQ = "SELECT * FROM Dates"
        return pl.read_database_uri(REQ, f"sqlite://{SONGS_DB}")
    else:
        return pl.read_csv(DATES_CSV)


PresetDict = dict[str, bool | str | list[str]]


class Preset:
    """Object to represent a preset in the TOML config file"""

    def get_list_assert(self, key: str) -> list[str]:
        """Returns include/exclude lists with type guaranteed.

        Args:
            key (str): config key, include/exclude-flags.

        Returns:
            list[str]: List of flags (may be empty).
        """
        if key in self.dict:
            ret = self.dict[key]
            assert type(ret) is list
            return ret
        else:
            return []

    def __init__(self, preset_dict: PresetDict, mp3gain_config: MP3ModeTuple, root: Optional[Path] = None) -> None:
        """Preset constructor.

        Args:
            preset_dict (PresetDict): Dict from the TOML loading.
            mp3gain_config (MP3ModeTuple): Configuration of mp3gain.
            root (Optional[Path], optional): Root path from outside of the Preset part, if None\
                then the path in preset is the full path, otherwise they use the root path\
                as a common folder for all presets. Defaults to None.
        """
        self.name = preset_dict["name"]
        self.dict = preset_dict

        self.include = self.get_list_assert("include-flags")
        self.exclude = self.get_list_assert("exclude-flags")

        self.mp3gain = MP3GainMode.OFF
        match mp3gain_config[0]:
            case MP3GainMode.ON_ALL:
                self.mp3gain = mp3gain_config[1]
            case MP3GainMode.PER_PRESET:
                if preset_dict.get("mp3gain", False) is True:
                    self.mp3gain = mp3gain_config[1]

        path = preset_dict["path"]
        assert type(path) is str

        if root is None:
            self.path = Path(path)
        else:
            self.path = root / path

    def get_filtered_df(self) -> pl.DataFrame:
        """Applies filters defined in a preset to get a filtered version of the database.

        Returns:
            pl.DataFrame: Filtered DB that only has rows that check the conditions.
        """
        songs_df = load_db()

        includes = stack_or(self.include)  # include#1 | include#2 ...
        excludes = stack_or(self.exclude)  # exclude#1 | exclude#2 ...

        # Has one of the include flags and none of the exclude
        return songs_df.filter(includes & excludes.not_())
