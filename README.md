# Neuro-sing-DB

## Setup
### tl;dr
[Install pipx](https://pipx.pypa.io/stable/installation/)
```bash
pipx install pdm
pdm install
```
### More details
TODO

### Windows
TODO?

## New batch
Latest: 25-06-2025
### For me
- [x] Get the new song names + order
- [x] Download new drive songs `rclone copy -v gdrive:Neuro songs/drive`
- [x] Generate json `update-json`
- [x] Sanitize json
  - [x] Check Artists name, check coherency with database with queries
  - [x] Set track number
  - [x] ASCII check
- [x] Update the csv database `update-csv`
- [x] Check for errors again
- [x] Run all checks `db-check`
- [x] Generate new thumbnails `thumbnails-generate`
  - [x] If not in the date png, add the new date
- [x] Generate songs `songs-generate`
- [x] Profit

*Note*: Create manually the "Song ASCII" or "Artist ASCII" key in JSON if needed, they are fields for a sanitized name for filenames e.g. `"Artist": "DECO*27"`, `"Artist ASCII": "DECO 27"`

*Another Note*: Yes calling this "ASCII" isn't really correct, as "*" for example is an ASCII character. It means sanitized, but it was longer and less clear imo. The goal with this field is firstly to make titles/artists compatible with a filename, and also to ease search for songs e.g. P!NK -> PINK

### For someone using this project
Wait for me to do all this work and upload it properly (pls be patient, I try to be fast)
TODO: Detail drives maybe?


## Repo organization
- images
- data
- Song List.md
- Notes.md
- Duplicates.md
- config.yml
### Code files
- checks
- json_to_csv
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
