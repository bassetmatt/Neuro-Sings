"""Detects new files and parse their data."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import polars as pl
from loguru import logger

from neuro import CUSTOM_DIR, DRIVE_DIR, ROOT_DIR, SONGS_JSON
from neuro.polars_utils import load_db

SongEntry = dict[str, Optional[str]]
"""Dictionary representing a song in the JSON, containing fields like "Song", "Artist", etc..."""
SongJSON = dict[str, list[SongEntry]]
"""Whole JSON file expected format. A list of date-indexed lists of songs."""


def get_files(songs: pl.DataFrame) -> dict[str, list[Path]]:
    """Gets filenames from expected directories. Skips files that are already in the database.\
        Check the function code to see which directories are searched through.

    Args:
        songs (pl.DataFrame): Songs database, here to check the current existing files.

    Returns:
        dict[str, list[Path]]: Audio files filtered by directories.\
            Keys: "Neuro", "Evil", "Duets", "V1", "V2", "Custom".
    """
    # Set of all files already treated and registered
    existing = set(map(lambda x: ROOT_DIR / Path(x), songs.get_column("File_IN").to_list()))

    def get_audios(p: Path, *, filetype: str = "mp3") -> list[Path]:
        files = list(p.glob(f"*.{filetype}"))
        return list(filter(lambda f: f not in existing, files))

    neuro_dir = DRIVE_DIR
    duets_dir = DRIVE_DIR / "Duets"
    evil_dir = [DRIVE_DIR / "Evil", DRIVE_DIR / "Evil/QUARANTINE"]
    v1_dir = DRIVE_DIR / "v1 voice"
    v2_dir = DRIVE_DIR / "v2 voice"
    custom_dir = CUSTOM_DIR

    return {
        "Neuro": get_audios(neuro_dir),
        "Evil": get_audios(evil_dir[0]) + get_audios(evil_dir[1]),
        "Duets": get_audios(duets_dir),
        "V1": get_audios(v1_dir),
        "V2": get_audios(v2_dir),
        "Custom": get_audios(custom_dir) + get_audios(custom_dir, filetype="flac"),
    }


def get_regexes() -> dict[str, list[str]]:
    """Gets different patterns as lists to match all cases of filenames. Check function code \
        to see which patterns are used. The patterns are made to be from the most selective to the least.

    Returns:
        dict[str, list[str]]: Lists of patterns grouped by use cases: common, evil, v1.\
            v2 can use common. custom can use common.
    """
    # Naming regex groups to ease treatment
    TITLE_FULL = "(?P<art>.+) - (?P<song>.+)"
    TITLE_PART = "(?P<full>.+)"
    EVIL = r"\(evil\)"
    DATE = r"\((?P<date>\d\d \d\d \d\d)\)"
    EXT = r"\.(?:mp3|wav)"
    common = [
        f"{TITLE_FULL} {DATE}{EXT}",
        f"{TITLE_PART} {DATE}{EXT}",
        f"{TITLE_FULL}{EXT}",
        f"{TITLE_PART}{EXT}",
    ]
    evil = [
        f"{TITLE_FULL} {DATE} {EVIL}{EXT}",
        f"{TITLE_FULL} {EVIL} {DATE}{EXT}",
        f"{TITLE_FULL} {EVIL}{EXT}",
        f"{TITLE_PART} {DATE} {EVIL}{EXT}",
        f"{TITLE_PART} {EVIL} {DATE}{EXT}",
        f"{TITLE_PART} {EVIL}{EXT}",
    ]
    DATE_V1 = r"\[(?P<date_v1>\d\d[-／]\d\d[-／]\d\d)\]"
    RANDOM_HASH_WTF = r"\[\d+\]"  # Some v1 songs have some sort of hash...
    v1 = [
        f"{DATE_V1} {TITLE_PART} {RANDOM_HASH_WTF}{EXT}",
        f"{DATE_V1} {TITLE_PART}{EXT}",
    ]
    return {"Neuro": common, "Evil": evil, "v1": v1}


def get_artist_and_title(groups: dict[str, str]) -> tuple[str, str]:
    """Returns song title and artist extracted from a filename using regexes.

    Args:
        groups (dict[str, str]): Groups obtained by matching a pattern with filename.\
            Groups must be named, obtained with `groupdicts`.

    Returns:
        tuple[str, str]: Tuple (artist, song). If the title has no "-", then the only field.\
            Is considered to be the song name.
    """
    artist = groups.get("art", "")
    song = groups.get("song", "")

    if "full" in groups.keys():  # Title with no dash or not detected
        full = groups["full"]
        if "-" in full:
            artist, song = full.split("-")
        else:
            song = full
    return (artist.strip(), song.strip())  # Removes possible spaces around


def get_date(groups: dict[str, str]) -> str:
    """Formats the date obtained via regex to a unique format YYYY-MM-DD.\
        The v1 dates are treated separately because they don't use the same format.

    Args:
        groups (dict[str, str]): Groups obtained by matching a pattern with filename.\
            Groups must be named, obtained with `groupdicts`.

    Returns:
        str: The date with YYYY_MM_DD format. If no date was provided via regex, "outlier"\
            is returned.
    """
    y, m, d = "", "", ""  # Avoids unbound variable error
    if "date_v1" in groups:  # v1 are M/D/Y
        date_pat = groups["date_v1"]
        if "-" in date_pat:
            m, d, y = date_pat.split("-")
        if "／" in date_pat:  # For that one v1 song that uses this annoying character...
            m, d, y = date_pat.split("／")
    elif "date" in groups:  # v3 are D/M/Y
        date_pat = groups["date"]
        d, m, y = date_pat.split(" ")
    else:  # "date" not in groups:
        return "outlier"
    dt = datetime(year=2000 + int(y), month=int(m), day=int(d))
    date = dt.strftime(r"%Y-%m-%d")
    return date


def extract_common(file: Path, regexes: list[str]) -> tuple[str, SongEntry]:
    """Tries to find a regex pattern to match a file structure to extract data.\
        Function applied to drive files mostly.

    Args:
        file (Path): File concerned.
        regexes (list[str]): List of regex patterns to try to match.

    Raises:
        ValueError: If none of the patterns matched.

    Returns:
        tuple[str, SongEntry]: A tuple with the 'date' (can be "outlier") and the main info\
            about the song: artist, song title, the original file and an album id.
    """
    data, date = {}, ""  # Avoids unbound variable error
    for i, pat in enumerate(regexes):
        matched = re.match(pat, str(file.name))
        if matched is None:
            continue
        logger.debug(f"File '{file.name}' matched pattern {i}")

        groups = matched.groupdict()
        artist, song = get_artist_and_title(groups)
        date = get_date(groups)
        if date == "outlier":
            logger.warning(f"File '{file.name} is an outlier")

        data = {
            "Artist": artist,
            "Song": song,
            "file": str(file),
            "id": None,
        }
        break  # Once a pattern matched, we stop looking for one
    if data == {}:  # Date is always assigned if a pattern matched
        logger.error(f"Couldn't find match for file '{file}'")
        raise ValueError
    return date, data


def extract_list(files: list[Path], regexes: list[str], out: SongJSON = {}) -> SongJSON:
    """Applies `extract_common` to a list of files and group them by date in a dictionary.

    Args:
        files (list[Path]): List of files to treat.
        regexes (list[str]): List of regex patterns.
        out (SongJSON, optional): Output dictionary, if no dictionary is passed, it's created\
            and returned. But an existing one can be passed to be completed. Defaults to {}.

    Returns:
        SongJSON: The output dict completed with the list of files' information.
    """
    for file in files:
        date, data = extract_common(file, regexes)
        if date in out:
            out[date].append(data)
        else:
            out[date] = [data]
    return out


def extract_custom(files: list[Path], out: SongJSON = {}) -> SongJSON:
    """Function on the same level as `extract_list`, but specialized for treatment of \
        custom files.

    Args:
        files (list[Path]): List of files.
        out (SongJSON, optional): Same as for `extract_list`. Dictionary created or completed\
            with files' data. Defaults to {}.

    Returns:
        SongJSON: Dictionary with at least these files' information.
    """
    outputs = []
    for file in files:
        filename = str(file.name).strip(file.suffix)
        # We can require this format for custom songs as the filename is chosen
        try:
            artist, song = map(str.strip, filename.split(" - "))
        except ValueError:
            logger.warning(f"Couldn't extract artist - song pattern for {file}")
            artist = ""
            song = filename
        data = {
            "Artist": artist,
            "Song": song,
            "file": str(file),
            "id": None,
        }
        outputs.append(data)
    out["custom"] = outputs
    return out


def extract_all() -> SongJSON:
    """Runs all the extraction functions on all defined patterns.

    Returns:
        SongJSON: Output dictionary containg all files that are not yet in the database.\
            They are grouped by date, or category if no date was provided in filename.
    """
    songs_db = load_db()
    files = get_files(songs_db)
    regex = get_regexes()

    out: SongJSON = {}
    # Neuro
    extract_list(files["Neuro"], regex["Neuro"], out)
    # Evil
    extract_list(files["Evil"], regex["Evil"], out)
    # Duets
    extract_list(files["Duets"], regex["Neuro"], out)

    # v1
    extract_list(files["V1"], regex["v1"], out)
    # v2
    extract_list(files["V2"], regex["Neuro"], out)

    # Custom
    extract_custom(files["Custom"], out)
    return out


def export_json(all_songs: SongJSON) -> None:
    """Takes an existing result of new files search and exports it in a json file.

    Args:
        all_songs (SongJSON): Dictionary with lists of files grouped by date.
    """
    songs = {}
    # Sorting songs by date for easier treatment
    for k in sorted(list(all_songs.keys())):
        songs[k] = all_songs[k]

    with open(SONGS_JSON, "w") as f:
        json.dump(songs, f, indent=2, ensure_ascii=False)
        f.write("\n")
