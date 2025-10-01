import json
from pathlib import Path
from typing import Literal, Optional

import polars as pl
from loguru import logger

from neuro import DATES_CSV, LOG_DIR, SONGS_CSV, SONGS_DB, SONGS_JSON
from neuro.detection import SongEntry, SongJSON
from neuro.polars_utils import load_dates, load_db
from neuro.utils import file_check, format_logger, get_sha256


def is_eliv(s: SongEntry) -> bool:
    """Checks if the file from an Entry is in the Evil subdirectory.

    Args:
        s (SongEntry): Song Entry.

    Returns:
        bool: True if it's in the subfolder.
    """
    assert s["file"] is not None
    return "/Evil" in s["file"]


def field_ascii(song: SongEntry, field: Literal["Song", "Artist"]) -> tuple[str, str]:
    """Gets the "normal" and "ASCII" versions of the 2 fields that have these variants.

    Args:
        song (SongEntry): A song Entry (dict from JSON file).
        field (Literal["Song", "Artist"]): The field.

    Returns:
        tuple[str, str]: A tuple with (normal, ascci).
    """
    normal = song[f"{field}"]
    assert normal is not None

    ascii = song.get(f"{field} ASCII", normal)
    assert ascii is not None

    return normal, ascii


def get_flags(file: Path, eliv: Optional[bool] = None) -> Optional[str]:
    """Gets the common evil/duet flag given a file. Evil flag can be set from \
        another boolean.

    Args:
        file (Path): File to check
        eliv (Optional[bool], optional): Can be ignored, but in case of an evil \
            stream, the duets will be in `/Duets` and not `/Evil`, so a global flag\
            for the stream can be given. Defaults to None.

    Returns:
        Optional[str]: String with flags if any, None otherwise.
    """
    flags = "v3;"
    if eliv is None:
        if "/Evil" in str(file):
            flags += "evil;"
    elif eliv:  # eliv is not None, then it's a bool, and here the bool is True
        flags += "evil;"
    else:
        flags += "neuro;"
    if "/Duets" in str(file):
        flags += "duet;"
    if flags == "":
        flags = None
    return flags


def update_db() -> None:
    """Updates the song databse, adding songs in the JSON files that aren't yet in it.
    The Date CSV/Table is also updated for each new stream."""
    format_logger(log_file=LOG_DIR / "json.log")
    with open(SONGS_JSON, "r") as f:
        json_data: SongJSON = json.load(f)

    # Absolutely doesn't work if the CSV is empty
    songs_df = load_db()
    dates_df = load_dates()

    # [-1] Makes sure id=0 if the column is empty
    id = max(songs_df.get_column("id").to_list() + [-1]) + 1

    streams_done: list[str] = []

    # date is like 2025-04-02
    # songs is a list of dict with song infos
    for date, songs in json_data.items():
        eliv = sum(map(is_eliv, songs)) > 0
        singer = "Evil" if eliv else "Neuro"

        # Avoids adding "outlier" and "custom" as dates
        if date[0] == "2" and date not in dates_df.get_column("Date"):
            df = pl.DataFrame(
                {
                    "Date": date,
                    "Singer": singer,
                    "Duet Format": "v2",
                }
            )
            # Adds a row for a new stream in the dates CSV
            dates_df.extend(df)
            logger.info(f"[Karaoke][+] {date} with {singer} singing")

        remove = 0
        # Just ensures that when sorting by id, the songs from a same album will also be sorted
        for song in sorted(songs, key=lambda x: x["id"] if x["id"] is not None else 5000):
            if song["id"] is None:
                continue

            assert song["file"] is not None
            file = Path(song["file"])
            file_check(file)  # Checks if file exists on disk
            if str(file) in songs_df.get_column("File_IN"):
                remove += 1
                logger.debug(f"File {str(file)} was already in database")
                continue

            # Using helper function to avoid code duplication
            name, name_ascii = field_ascii(song, "Song")
            artist, artist_ascii = field_ascii(song, "Artist")

            df = pl.DataFrame(
                {
                    "id": id,
                    "Song": name,
                    "Artist": artist,
                    "Song_ASCII": name_ascii,
                    "Artist_ASCII": artist_ascii,
                    "Date": date,
                    "Album": f"{singer} {date} Karaoke",
                    "Album_ID": song["id"],
                    "Image": None,
                    "File_IN": str(file),
                    "Hash_IN": get_sha256(file),
                    "Flags": get_flags(file, eliv),
                    "Key": None,
                    "Tempo (1/4 beat)": None,
                }
            )
            id += 1
            remove += 1
            songs_df.extend(df)
            logger.info(f"[Song][+] {artist} - {name}")

        if remove == len(songs):
            streams_done += [date]

    for date in streams_done:
        json_data.pop(date)
        logger.info(f"All songs from {date} treated, removed stream")

    # Updates JSON file with treated songs removed
    with open(SONGS_JSON, "w") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Write modifications if both CSVs
    songs_df.write_csv(SONGS_CSV)
    dates_df.write_csv(DATES_CSV)
    # Write modifications if DBs
    songs_df.write_database("Songs", f"sqlite:///{SONGS_DB}", if_table_exists="replace")
    dates_df.write_database("Dates", f"sqlite:///{SONGS_DB}", if_table_exists="replace")


if __name__ == "__main__":
    update_db()
