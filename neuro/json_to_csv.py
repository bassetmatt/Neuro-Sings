import json
from pathlib import Path
from typing import Literal, Optional

import polars as pl
from loguru import logger

from neuro import DATES_CSV, LOG_DIR, SONGS_CSV, SONGS_JSON
from neuro.song_detect import SongEntry, SongJSON
from neuro.utils import format_logger, get_sha256


def is_eliv(s: SongEntry) -> bool:
    assert s["file"] is not None
    return "/Evil" in s["file"]


def field_ascii(song: SongEntry, field: Literal["Song", "Artist"]) -> tuple[str, str]:
    normal = song[f"{field}"]
    assert normal is not None

    ascii = song.get(f"{field} ASCII", normal)
    assert ascii is not None

    return normal, ascii


def flags(file: Path, eliv: bool) -> Optional[str]:
    flags = ""
    if eliv:
        flags += "evil;"
    if "/Duets" in str(file):
        flags += "duets;"
    if flags == "":
        flags = None
    return flags


def update_csv() -> None:
    format_logger(log_file=LOG_DIR / "json.log")
    with open(SONGS_JSON, "r") as f:
        json_data: SongJSON = json.load(f)

    # Absolutely doesn't work if the CSV is empty
    # Using series is annoying

    songs_df = pl.read_csv(SONGS_CSV)
    dates_df = pl.read_csv(DATES_CSV)
    # [-1] Makes sure id=0 if the column is empty
    id = max(songs_df.get_column("id").to_list() + [-1]) + 1

    streams_done = []

    # date is like 2025-04-02
    # songs is a list of dict with song infos
    for date, songs in json_data.items():
        eliv = sum(map(is_eliv, songs)) > 0
        singer = "Evil" if eliv else "Neuro"

        # Avoids adding "outlier" and "custom" as dates
        if date[0] == "2" and date not in dates_df.get_column("Date"):
            df = pl.DataFrame({"Date": date, "Singer": singer, "Duet Format": "v2"})
            dates_df = pl.concat([dates_df, df])
            logger.info(f"[Karaoke][+] {date} with {singer} singing")

        remove = 0
        # Just ensures the songs ids' are increasing with album id
        for song in sorted(songs, key=lambda x: x["id"] if x["id"] is not None else 5000):
            if song["id"] is None:
                continue

            assert song["file"] is not None
            file = Path(song["file"])
            if str(file) in songs_df.get_column("File_IN"):
                remove += 1
                logger.debug(f"File {str(file)} already in database")
                continue

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
                    "include": True,
                    "Flags": flags(file, eliv),
                }
            )
            id += 1
            remove += 1
            songs_df = pl.concat([songs_df, df])
            logger.info(f"[Song][+] {artist} - {name}")

        if remove == len(songs):
            streams_done += [date]

    for date in streams_done:
        json_data.pop(date)
        logger.info(f"All songs from {date} treated, removed stream")

    with open(SONGS_JSON, "w") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    songs_df.write_csv(SONGS_CSV)
    dates_df.write_csv(DATES_CSV)


if __name__ == "__main__":
    update_csv()
