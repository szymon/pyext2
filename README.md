# cmd application for interacting with ext2 image

Very lacking implementation of ext2 filesystem "driver"

# Installation

Can't install with `poetry install` on macos, you need to run `poetry run python -m pip install regex` first
and only then run `poetry install`.
From what I understand poetry can't build legacy projects (without pyproject.toml) and fails to build regex.

# TODO:

- [x] list directory
- [x] cat file
- [ ] respect links
- [ ] create new directory/file
- [ ] copy 
