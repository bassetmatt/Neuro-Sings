import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import polars as pl
from loguru import logger

from neuro import CUSTOM_ROOT, DRIVE_ROOT, ROOT, SONGS_JSON

SongEntry = dict[str, Optional[str]]
SongJSON = dict[str, list[SongEntry]]


def get_files(songs: pl.DataFrame) -> dict[str, list[Path]]:
    # Set of all files already treated and registered
    existing = set(map(lambda x: ROOT / Path(x), songs.get_column("File_IN").to_list()))

    def get_audios(p: Path, *, filetype: str = "mp3") -> list[Path]:
        files = list(p.glob(f"*.{filetype}"))
        return list(filter(lambda f: f not in existing, files))

    neuro_dir = DRIVE_ROOT
    duets_dir = DRIVE_ROOT / "Duets"
    evil_dir = [DRIVE_ROOT / "Evil", DRIVE_ROOT / "Evil/QUARANTINE"]
    v1_dir = DRIVE_ROOT / "v1 voice"
    v2_dir = DRIVE_ROOT / "v2 voice"
    custom_dir = CUSTOM_ROOT

    return {
        "Neuro": get_audios(neuro_dir),
        "Evil": get_audios(evil_dir[0]) + get_audios(evil_dir[1]),
        "Duets": get_audios(duets_dir),
        "V1": get_audios(v1_dir),
        "V2": get_audios(v2_dir),
        "Custom": get_audios(custom_dir) + get_audios(custom_dir, filetype="flac"),
    }


def get_regexes() -> dict[str, list[str]]:
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
    RANDOM_HASH_WTF = r"\[\d+\]"
    v1 = [
        f"{DATE_V1} {TITLE_PART} {RANDOM_HASH_WTF}{EXT}",
        f"{DATE_V1} {TITLE_PART}{EXT}",
    ]
    return {"Neuro": common, "Evil": evil, "v1": v1}


def get_song_artist(groups: dict[str, str]) -> tuple[str, str]:
    artist = groups.get("art", "")
    song = groups.get("song", "")

    if "full" in groups.keys():
        full = groups["full"]
        if "-" in full:
            artist, song = full.split("-")
        else:
            song = full
    return (artist.strip(), song.strip())


def get_date(groups: dict[str, str]) -> str:
    if "date_v1" in groups:
        date_pat = groups["date_v1"]
        if "-" in date_pat:
            m, d, y = date_pat.split("-")
        if "／" in date_pat:
            m, d, y = date_pat.split("／")
    elif "date" in groups:
        date_pat = groups["date"]
        d, m, y = date_pat.split(" ")
    else:  # "date" not in groups:
        return "outlier"
    dt = datetime(year=2000 + int(y), month=int(m), day=int(d))
    date = dt.strftime(r"%Y-%m-%d")
    return date


def extract_common(file: Path, regexes: list[str]) -> tuple[str, SongEntry]:
    data = {}
    for i, pat in enumerate(regexes):
        matched = re.match(pat, str(file.name))
        if matched is None:
            continue
        logger.debug(f"File '{file.name}' matched pattern {i}")

        groups = matched.groupdict()
        artist, song = get_song_artist(groups)
        date = get_date(groups)
        if date == "outlier":
            logger.warning(f"File '{file.name} is an outlier")

        data = {
            "Artist": artist,
            "Song": song,
            "file": str(file),
            "id": None,
        }
        break
    if date == {}:
        logger.error(f"Couldn't find match for file '{file}'")
        raise ValueError
    return date, data


def extract_list(files: list[Path], regexes: list[str], out: SongJSON = {}) -> SongJSON:
    for file in files:
        date, data = extract_common(file, regexes)
        if date in out:
            out[date].append(data)
        else:
            out[date] = [data]
    return out


def extract_custom(files: list[Path], out: SongJSON = {}) -> SongJSON:
    outputs = []
    for file in files:
        filename = str(file.name).strip(file.suffix)
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


def extract_all(songs: pl.DataFrame) -> SongJSON:
    files = get_files(songs)
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
    # TODO: Merge dicts, maybe add flags for duets, etc.. (useless with filename)


def export_json(all_songs: SongJSON) -> None:
    songs = {}
    # Sorting songs by date for easier treatment
    for k in sorted(list(all_songs.keys())):
        songs[k] = all_songs[k]

    with open(SONGS_JSON, "w") as f:
        json.dump(songs, f, indent=2, ensure_ascii=False)
