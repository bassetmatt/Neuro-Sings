import json
from pathlib import Path

import polars as pl
from loguru import logger

from neuro import DATES_CSV, LOG_DIR, SONGS_CSV, SONGS_JSON
from neuro.song_detect import SongEntry, SongJSON
from neuro.utils import format_logger, get_sha256


def update_csv() -> None:
    format_logger(log_file=LOG_DIR / "json.log")
    with open(SONGS_JSON, "r") as f:
        json_data: SongJSON = json.load(f)

    # Absolutely doesn't work if the CSV is empty
    # Using series is annoying
    songs_dict = pl.read_csv(SONGS_CSV).to_dict(as_series=False)
    dates_dict = pl.read_csv(DATES_CSV).to_dict(as_series=False)

    if songs_dict["id"] == []:
        id = 0
    else:
        id = max(songs_dict["id"]) + 1

    streams_done = []

    # date is like 2025-04-02
    # songs is a list of dict with song infos
    for date, songs in json_data.items():

        def is_eliv(s: SongEntry) -> bool:
            assert s["file"] is not None
            return "Evil" in s["file"]

        eliv = sum(map(is_eliv, songs)) > 0

        if date not in dates_dict["Date"]:
            dates_dict["Date"].append(date)
            singer = "Evil" if eliv else "Neuro"
            dates_dict["Singer"].append(singer)
            dates_dict["Duet Format"].append("v2")
            logger.info(f"[Karaoke][+] {date} with {singer} singing")

        remove = 0
        for song in sorted(
            songs, key=lambda x: x["id"] if x["id"] is not None else 5000
        ):
            assert song["file"] is not None
            assert song["Song"] is not None

            if song["id"] is None:
                continue
            file = Path(song["file"])
            if str(file) in songs_dict["File_IN"]:
                remove += 1
                continue

            name: str = song["Song"]
            name_ascii = song.get("Song ASCII", name)
            # TODO Could be rewritten setting up individual Dataframes per
            # row and then concatenate them
            songs_dict["id"].append(id)
            songs_dict["Song"].append(name)
            songs_dict["Song_ASCII"].append(name_ascii)

            artist = song["Artist"]
            artist_ascii = song.get("Artist ASCII", artist)
            songs_dict["Artist"].append(artist)
            songs_dict["Artist_ASCII"].append(artist_ascii)

            songs_dict["Date"].append(date)

            songs_dict["Album"].append(None)
            songs_dict["Album_ID"].append(song["id"])

            songs_dict["Image"].append(None)

            songs_dict["File_OUT"].append(None)

            hash = get_sha256(file)

            songs_dict["File_IN"].append(str(file))
            songs_dict["Hash_IN"].append(hash)
            songs_dict["include"].append(True)
            flags = ""
            if "/Evil" in str(file):
                flags += "evil;"
            if "/Duets" in str(file):
                flags += "duets;"
            if flags == "":
                flags = None
            songs_dict["Flags"].append(flags)

            id += 1
            remove += 1
            logger.info(f"[Song][+] {artist} - {name}")
        if remove == len(songs):
            streams_done += [date]

    for date in streams_done:
        json_data.pop(date)
        logger.info(f"All songs from {date} treated, removed stream")

    with open(SONGS_JSON, "w") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    pl.from_dict(songs_dict).write_csv(SONGS_CSV)

    pl.from_dict(dates_dict).write_csv(DATES_CSV)


if __name__ == "__main__":
    update_csv()
