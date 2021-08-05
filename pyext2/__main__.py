from __future__ import annotations

from argparse import ArgumentParser
import sys
import logging

from .ext2reader import Ext2Reader


def main() -> Ext2Reader:
    parser = ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("-v", "--verbose", choices=["DEBUG", "INFO", "NONE"], default="NONE")

    args = parser.parse_args(sys.argv[1:])

    logging_level = {
        "NONE": None,
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
    }[args.verbose]

    if logging_level:
        logging.basicConfig(level=logging.DEBUG)

    with open(args.file, "rb") as _f:
        reader = Ext2Reader(_f)

        reader.parse()

        return reader


if __name__ == "__main__":
    r = main()
