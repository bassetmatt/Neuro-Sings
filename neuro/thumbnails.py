import os
from string import digits
from time import time

import PIL.Image as Image
import PIL.ImageFile as ImageFile
import polars as pl
from loguru import logger
from PIL import Image as Image_mod

from neuro import (
    DATES_CSV,
    DATES_OLD_CSV,
    IMAGES_BG,
    IMAGES_COVERS,
    IMAGES_CUSTOM,
    IMAGES_DATES,
    LOG_DIR,
)
from neuro.utils import format_logger, time_format


def apply_text(
    image: ImageFile.ImageFile,
    dates: Image.Image,
    date_idx: int,
    *,
    date_w: int = 900,
    date_h: int = 170,
    OFFSET: int = 15,
    MAX_SIZE: int = 500,
) -> Image.Image:
    """Writes a date from a text atlas image on an image

    Args:
        image (ImageFile): Background image
        dates (ImageFile): Image atlas containing all dates, assumes the dates\
            image is an atlas where each date text is 900x183 px (or else, but \
            defined in date_w and date_h)
        date_idx (int): Index of the date in the atlas, starts at 0
        date_w (int, optional): Width of the date image.\
            Defaults to 900.
        date_h (int, optional): Height of one date entry. \
            Defaults to 170.
        OFFSET (int, optional): Offset before the start of the first date. \
            Defaults to 15.
        MAX_SIZE (int, optional): Maximum size for a cover (one dimension \
            given, aspect ratio is preserved). \
            Defaults to 500.

    Returns:
            Image.Image: Image with the text pasted on it
    """
    w, h = image.size
    new_image = image.copy()

    # Force cover to be at most MAX_SIZExMAX_SIZE (default 500x500)
    if w > MAX_SIZE or h > MAX_SIZE:
        if w == h:
            new_dims = (MAX_SIZE, MAX_SIZE)
        elif w > h:
            new_dims = (MAX_SIZE, int(MAX_SIZE / w * h))
        else:  # w < h
            new_dims = (int(MAX_SIZE / h * w), MAX_SIZE)
        new_image = new_image.resize(new_dims)
    w, h = new_image.size

    # Cropping the Date zone in the dates atlas
    box_up = OFFSET + date_h * date_idx
    box_down = box_up + date_h
    # Crop zone, order: Left, Up, Right, Down
    zone = (0, box_up, date_w, box_down)
    date_crop = dates.crop(zone)

    # Scaling text to image
    TEXT_RATIO = 0.6
    text_w = TEXT_RATIO * w
    text_h = text_w * date_h / date_w  # Keeps the text aspect ratio
    date_text = date_crop.resize([int(text_w), int(text_h)])

    # Pastes the date onto the original image
    text_x = int((w - text_w) / 2)
    text_y = int(0.8 * h)

    paste_zone = (text_x, text_y)
    new_image.paste(date_text, paste_zone, date_text)

    return new_image


def generate_oldge() -> None:
    format_logger(log_file=LOG_DIR / "thumbnails.log")
    t = time()
    # v1
    NUERO = Image_mod.open(IMAGES_BG / "nuero.png")
    # v2
    NWERO_V2 = Image_mod.open(IMAGES_BG / "nwero_v2.png")

    dates_old = pl.read_csv(DATES_OLD_CSV)
    N_COVERS = len(dates_old)
    os.makedirs(IMAGES_COVERS, exist_ok=True)
    os.makedirs(IMAGES_CUSTOM, exist_ok=True)

    DATES_MONTHS = Image_mod.open(IMAGES_DATES / "2023-dates-months.png").convert("RGBA")
    DATES_KARAOKES = Image_mod.open(IMAGES_DATES / "2023-dates-v12.png").convert("RGBA")
    i_m, i_k = 0, 0
    for stream in dates_old.iter_rows(named=True):
        date: str = stream["Date"]
        ver: str = stream["Voice"]
        if ver == "v1":
            base = NUERO
        else:
            base = NWERO_V2

        if date[5] in digits:
            date_img = DATES_KARAOKES
            apply_text(base, date_img, i_k).convert("RGB").save(IMAGES_COVERS / f"{date}.jpg")
            i_k += 1
        else:
            date_img = DATES_MONTHS
            apply_text(base, date_img, i_m, date_w=1250, date_h=215).convert("RGB").save(IMAGES_CUSTOM / f"{date}.jpg")
            i_m += 1

        index = i_m + i_k - 1
        logger.debug(f"[THUMB] [{index + 1:2d}/{N_COVERS}] Cover Pictures for {date} done")

    logger.success(f"[THUMB] {N_COVERS} successfully generated in {time_format(time() - t)}")


def main() -> None:
    format_logger(log_file=LOG_DIR / "thumbnails.log")

    # v3
    NWERO = Image_mod.open(IMAGES_BG / "nwero.png")
    # v3 Voice w/ v2 Model
    NEWERO = Image_mod.open(IMAGES_BG / "newero.png")

    # Eliv v1 Model
    ELIV = Image_mod.open(IMAGES_BG / "eliv.png")
    # Eliv v2 Model
    NEWELIV = Image_mod.open(IMAGES_BG / "neweliv.png")

    # Neuro v2, Evil v1
    SMOCUS = Image_mod.open(IMAGES_BG / "smocus.jpg")
    # Neuro v3, Evil v1
    SMOCUS_INTER = Image_mod.open(IMAGES_BG / "smocus_inter.png")
    # Neuro v3, Evil v2
    SMOCUS_NEW = Image_mod.open(IMAGES_BG / "smocus_new.png")

    DATES_2023 = Image_mod.open(IMAGES_DATES / "2023-dates.png").convert("RGBA")
    DATES_2024 = Image_mod.open(IMAGES_DATES / "2024-dates.png").convert("RGBA")
    DATES_2025 = Image_mod.open(IMAGES_DATES / "2025-dates.png").convert("RGBA")

    logger.info("[THUMB] Starting the generation of thumbnails")

    t = time()
    dates = pl.read_csv(DATES_CSV)

    N_COVERS = len(dates)

    os.makedirs(IMAGES_COVERS, exist_ok=True)
    i23, i24, i25 = 0, 0, 0
    for stream in dates.iter_rows(named=True):
        date = stream["Date"]
        who = stream["Singer"]
        version = stream["Duet Format"]
        match date[:4]:
            case "2023":
                i = i23
                i23 += 1
                date_img = DATES_2023
            case "2024":
                i = i24
                i24 += 1
                date_img = DATES_2024
            case "2025":
                i = i25
                i25 += 1
                date_img = DATES_2025
            case _:
                logger.error("Wrong year")
                raise ValueError
        match who:
            case "Neuro":
                base = NWERO
                if "v2" in version:
                    base = NEWERO
            case "Evil":
                base = NEWELIV
                if "v1" in version:
                    base = ELIV
            case _:
                logger.error("Wrong singer")
                raise ValueError
        match version:
            case "v1":
                duet = SMOCUS
            case "v2v1":
                duet = SMOCUS_INTER
            case "v2":
                duet = SMOCUS_NEW
            case _:
                logger.error("Wrong version")
                raise ValueError

        apply_text(base, date_img, i).convert("RGB").save(IMAGES_COVERS / f"{date}.jpg")
        apply_text(duet, date_img, i).convert("RGB").save(IMAGES_COVERS / f"duet-{date}.jpg")
        index = i23 + i24 + i25 - 1
        logger.debug(f"[THUMB] [{index + 1:2d}/{N_COVERS}] Cover Pictures for {date} done")

    logger.success(f"[THUMB] {N_COVERS} successfully generated in {time_format(time() - t)}")


if __name__ == "__main__":
    main()
