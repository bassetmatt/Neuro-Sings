"""Applies all metadata tags on music files"""

import os
import shutil
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional

from loguru import logger
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3
from mutagen.id3._frames import APIC
from PIL import Image

from neuro import IMAGES_COVERS_DIR, IMAGES_CUSTOM_DIR, LOG_DIR, ROOT_DIR
from neuro.detection import SongEntry
from neuro.utils import file_check, format_logger


class Song:
    @dataclass
    class Flags:
        v1: bool
        v2: bool
        evil: bool
        duet: bool
        duplicate: bool
        """Duplicate song, file doesn't exist in drive, but song was sung that day"""
        as_drive: bool
        """Use the same naming convention as drive files for filename"""
        as_custom: bool
        """Use the same naming convention as custom files for filename"""

    def init_flags(self, flags: Optional[str]) -> None:
        # flag is false if song has no flags of if it has flags but not the selected one
        def flag_check(flag: str, flag_field: Optional[str]) -> bool:
            if flag_field is None:
                return False
            return flag in flag_field

        # Strange code, but just expands into `"v1": flags_check("v1", flags)`...
        # for all flags. It uses the fact that Flags fields are exactly the same
        # strings as the flags
        self.flags = self.Flags(**{flag: flag_check(flag, flags) for flag in self.Flags.__dataclass_fields__.keys()})

    def __init__(self, song_dict: SongEntry, karaoke_dict: dict = {}) -> None:
        assert song_dict["Song"] is not None
        assert song_dict["Song_ASCII"] is not None
        self.title: str = song_dict["Song"]
        self.title_ascii: str = song_dict["Song_ASCII"]

        assert song_dict["Artist"] is not None
        assert song_dict["Artist_ASCII"] is not None
        self.artist: str = song_dict["Artist"]
        self.artist_ascii: str = song_dict["Artist_ASCII"]

        assert song_dict["File_IN"] is not None
        self.file: Path = ROOT_DIR / Path(song_dict["File_IN"])
        file_check(self.file)

        assert song_dict["Album_ID"] is not None
        self.track_n: str = song_dict["Album_ID"]

        assert song_dict["Date"] is not None
        self.date: str = song_dict["Date"]

        assert song_dict["Album"] is not None
        self.album: str = song_dict["Album"]

        self.image: Optional[str] = song_dict["Image"]
        self.outfile: Optional[Path] = None

        self.d: SongEntry = song_dict
        self.k: SongEntry = karaoke_dict

        self.init_flags(song_dict["Flags"])

    def create_out_file(self) -> None:
        raise NotImplementedError

    def id3_pic(self, cover: Path) -> APIC:
        img = APIC(
            encoding=3,  # 3 is for utf-8
            mime="image/jpeg",  # image/jpeg or image/png
            type=18,  # 3 is for the cover image
            desc="Cover",
            data=open(cover, "rb").read(),
        )
        return img

    def get_common_tags(self) -> dict[str, str]:
        return {
            "Title": self.title,
            "Artist": self.artist,
            "Album": self.album,
            "Tracknumber": f"{self.track_n}",
            "Date": self.date,
        }

    @property
    def album_artist(self) -> str:
        # They are mutually exclusive so it's okay
        if self.flags.v1:
            return "Neuro [v1]"
        if self.flags.v2:
            return "Neuro [v2]"
        if self.flags.evil:
            return "Evil Neuro"
        return "Neuro-Sama"

    @property
    def name_tag(self) -> str:
        if self.flags.v1:
            return "Neuro v1"
        if self.flags.v2:
            return "Neuro v2"
        if self.title == "Chinatown Blues":
            return "Neuro + Vedal"
        # A song can have both evil and duet tags, but the duet tag is prioritized
        if self.flags.duet:
            return "Duet"
        if self.flags.evil:
            return "Evil"
        return "Neuro"

    def file_name(self, custom: bool) -> str:
        if custom:
            return f"{self.artist_ascii} - {self.title_ascii}"
        else:
            return f"{self.artist_ascii} - {self.title_ascii} [{self.name_tag}] [{self.date}]"


class DriveSong(Song):
    def __init__(self, song_dict: dict, karaoke_dict: dict) -> None:
        super().__init__(song_dict, karaoke_dict)

    def create_out_file(self, *, out_dir: Path = Path("out"), create: bool = True) -> None:
        file = self.file
        os.makedirs(ROOT_DIR / out_dir, exist_ok=True)
        name = self.file_name(self.flags.as_custom)
        self.outfile = ROOT_DIR / out_dir / f"{name}.mp3"

        if create or (not self.outfile.exists()):
            shutil.copy2(file, self.outfile)

    def apply_tags(self) -> None:
        # Text tags
        ez_id3 = EasyID3(self.outfile)

        common_props = self.get_common_tags()
        for k, v in common_props.items():
            ez_id3[k] = v

        ez_id3["Albumartist"] = self.album_artist
        ez_id3.save()

        # Cover Image
        id3 = ID3(self.outfile)
        if self.image is None:
            if self.flags.duet:
                cover = IMAGES_COVERS_DIR / Path(f"duet-{self.date}.jpg")
            else:
                cover = IMAGES_COVERS_DIR / Path(f"{self.date}.jpg")
        else:
            cover = IMAGES_CUSTOM_DIR / f"{self.image}.jpg"
        file_check(cover)
        id3.delall("APIC")
        id3.add(self.id3_pic(cover))
        id3.save()


class CustomSong(Song):
    def __init__(self, song_dict: dict, karaoke_dict: dict = {}) -> None:
        super().__init__(song_dict, karaoke_dict)

    def create_out_file(self, *, out_dir: Path, create: bool = True) -> None:
        file = self.file
        ext = file.suffix

        name = self.file_name(not self.flags.as_drive)
        self.outfile = ROOT_DIR / out_dir / f"{name}{ext}"

        if create or (not self.outfile.exists()):
            shutil.copy2(file, self.outfile)

    def apply_tags(self) -> None:
        ext = self.file.suffix
        if self.image is None:
            logger.error(f"Image can't be None for custom song {self.file}")

        self.cover = IMAGES_CUSTOM_DIR / f"{self.image}.jpg"
        file_check(self.cover)

        match ext:
            case ".mp3":
                self.apply_id3()
            case ".flac":
                self.apply_tags_vorbis()
            case _:
                logger.error(f"Wrong file suffix for {self.file}")
                raise ValueError

    def apply_id3(self) -> None:
        ez_id3 = EasyID3(self.outfile)

        common_props = self.get_common_tags()
        for k, v in common_props.items():
            ez_id3[k] = v
        ez_id3.save()

        # Cover Image
        id3 = ID3(self.outfile)

        id3.delall("APIC")
        id3.add(self.id3_pic(self.cover))
        id3.save()

    def get_flac_pic(self) -> Picture:
        img = Image.open(self.cover)
        if img.mode == "RGBA":
            img = img.convert("RGB")

        buffer = BytesIO()
        img.save(
            buffer,
            format="JPEG",
            quality=85,
            optimize=True,
            progressive=False,
        )
        image_file = buffer.getvalue()
        img.close()

        image = Picture()
        image.type = 3
        image.mime = "image/jpeg"
        image.desc = "Cover"
        image.data = image_file
        return image

    def apply_tags_vorbis(self) -> None:
        # Based on https://exiftool.org/TagNames/Vorbis.html tags descriptions
        file = FLAC(self.outfile)
        if file.tags is None:
            logger.error(f"File {self.file} has no tags header.")
            raise ValueError

        common = self.get_common_tags()
        for k, v in common.items():
            file.tags[k.upper()] = v  # type: ignore

        # Cover
        image = self.get_flac_pic()

        file.clear_pictures()
        file.add_picture(image)
        file.save()


if __name__ == "__main__":
    format_logger(log_file=LOG_DIR / "tags.log")
