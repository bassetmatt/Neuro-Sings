# Neuro-sing-DB

## Setup
tl;dr\
[Install pipx](https://pipx.pypa.io/stable/installation/)
```bash
pipx install pdm
pdm install
```



## Songs Download
rclone command:
```bash
rclone copy -v gdrive:Neuro songs/drive
```

## New batch
- Create manually the "Song ASCII" or "Artist ASCII" key in JSON if needed, they are fields for a sanitized name for filenames e.g. `"Artist": "DECO*27"`, `"Artist ASCII": "DECO 27"`

## Repo organization
- images
- data
- Song List
- Notes
### Code files
- checks
- json_to_csv
- new_batch
- run
- song_detect
- song_tags
- thumbnails
- utils

## License

<sup>
Licensed under either of <a href="LICENSE-APACHE">Apache License, Version
2.0</a> or <a href="LICENSE-MIT">MIT license</a> at your option.
</sup>

<br>

<sub>
Unless you explicitly state otherwise, any contribution intentionally submitted
for inclusion by you, as defined in the Apache-2.0 license, shall be
dual licensed as above, without any additional terms or conditions.
</sub>
