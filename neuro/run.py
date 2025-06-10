import os
from pathlib import Path
from time import time

import polars as pl
import yaml
from loguru import logger

from neuro import DATES_CSV, DRIVE_ROOT, LOG_DIR, SONGS_CSV
from neuro.song_tags import CustomSong, DriveSong
from neuro.utils import format_logger, time_format


def main() -> None:
    format_logger(log_file=LOG_DIR / "generation.log")
    logger.info("[GEN] Starting generation batch")

    with open("config.yml", "r") as file:
        config = yaml.safe_load(file)

    OUT = Path(config["out-path"])
    os.makedirs(OUT, exist_ok=True)

    if config["generate-disabled"]:
        OUT_DIS = Path(config["diabled-path"])
        os.makedirs(OUT_DIS, exist_ok=True)

    # Start time
    t = time()

    songs = pl.read_csv(SONGS_CSV)
    N_SONGS = len(songs)

    dates = pl.read_csv(DATES_CSV)
    dates_dict = {k["Date"]: k for k in dates.iter_rows(named=True)}

    i = 0
    for song_dict in songs.iter_rows(named=True):
        i += 1

        if song_dict["include"]:
            out_dir = OUT
        elif config["generate-disabled"]:  # Not included, but still generated
            out_dir = OUT_DIS
        else:
            logger.debug(f"[GEN] [{i:3d}/{N_SONGS}] Skipped {song_dict['Song']}")
            continue

        logger.debug(f"[GEN] [{i:3d}/{N_SONGS}] Generating {song_dict['Song']}")
        if Path(song_dict["File_IN"]).is_relative_to(DRIVE_ROOT):
            d_dict = dates_dict.get(song_dict["Date"], {})
            s = DriveSong(song_dict, d_dict)
        else:
            s = CustomSong(song_dict)
        s.create_out_file(create=True, out_dir=out_dir)
        s.apply_tags()

    logger.success(
        f"[GEN] Done converting {N_SONGS} songs in {time_format(time() - t)} !"
    )


if __name__ == "__main__":
    main()
