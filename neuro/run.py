import os
from pathlib import Path
from time import time

import polars as pl
import yaml
from loguru import logger

from neuro import DATES_CSV, DRIVE_DIR, LOG_DIR, SONGS_CSV
from neuro.song_detect import export_json, extract_all
from neuro.song_tags import CustomSong, DriveSong
from neuro.utils import format_logger, time_format


def set_includes(exclude_flags: list[str]) -> None:
    """Disables the songs that have the flags that are excluded.

    Args:
        exclude_flags (list[str]): List of flags provided in the yaml file.
    """
    songs_df = pl.read_csv(SONGS_CSV)

    has_flag = pl.lit(False)
    # Checks if any flag is present
    for flag in exclude_flags:
        has_flag |= pl.col("Flags").str.contains(flag)

    songs_df.with_columns(
        # Use this syntax despite `has_flag` being boolean because otherwise the rows that don't have
        # any flags are ignored
        pl.when(has_flag)
        .then(pl.lit(False))  # If it has flags it's disabled
        .otherwise(pl.lit(True))  # Else it's included (manually disabled songs will be reactivated)
        .alias("include")  # Overwrites the existing include column
    ).write_csv(SONGS_CSV)


def standalone_set_includes() -> None:
    """Standalone version of the include flag setter so it can be ran from the terminal without
    running the whole song generation code."""

    with open("config.yml", "r") as file:
        config = yaml.safe_load(file)
    if config["automatically-disable-songs"]:
        set_includes(config["disabled-flags"])


def new_batch_detection() -> None:
    """Re-runs the song detection based on regex. Adds songs that aren't already in\
        the database in a JSON file for them to be reviewed.
    """
    format_logger(verbosity=5, log_file=LOG_DIR / "batches.log")
    # These 3 lines could be ine call, but it would just make the code less clear
    songs = pl.read_csv(SONGS_CSV)
    out = extract_all(songs)  # Exctacts data
    export_json(out)  # Writing into JSON


def generate_songs() -> None:
    """Generates all songs files. For each files it first copies the files into\
    its destination, then edits the metadata of the destination file. This is\
    just to avoid tempering the original files."""

    format_logger(log_file=LOG_DIR / "generation.log")
    logger.info("[GEN] Starting generation batch")

    # Loading config file
    with open("config.yml", "r") as file:
        config = yaml.safe_load(file)

    # Output folder
    OUT = Path(config["out-path"])
    os.makedirs(OUT, exist_ok=True)

    # If the disabled songs are generated, set their folder and create it if needed
    if config["generate-disabled"]:
        OUT_DIS = Path(config["diabled-path"])
        os.makedirs(OUT_DIS, exist_ok=True)

    # Filtered
    if config["automatically-disable-songs"]:
        set_includes(config["disabled-flags"])

    # Start time
    t = time()

    songs = pl.read_csv(SONGS_CSV)
    N_SONGS = len(songs)

    dates = pl.read_csv(DATES_CSV)
    # Easier data format to deal with
    dates_dict = {k["Date"]: k for k in dates.iter_rows(named=True)}

    for i, song_dict in enumerate(songs.iter_rows(named=True)):
        if song_dict["include"]:
            out_dir = OUT
        elif config["generate-disabled"]:  # Not included, but still generated
            out_dir = OUT_DIS
        else:
            logger.debug(f"[GEN] [{i + 1:3d}/{N_SONGS}] Skipped {song_dict['Song']}")
            continue

        logger.debug(f"[GEN] [{i + 1:3d}/{N_SONGS}] Generating {song_dict['Song']}")
        # Differenciate songs from drive and custom songs. Mainly because they aren't
        # from the same contexts (streams vs collabs mainly)
        if Path(song_dict["File_IN"]).is_relative_to(DRIVE_DIR):
            date_dict = dates_dict.get(song_dict["Date"], {})
            s = DriveSong(song_dict, date_dict)
        else:
            s = CustomSong(song_dict)
        s.create_out_file(create=True, out_dir=out_dir)
        s.apply_tags()

    logger.success(f"[GEN] Done converting {N_SONGS} songs in {time_format(time() - t)} !")


if __name__ == "__main__":
    generate_songs()
