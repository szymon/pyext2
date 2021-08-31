from __future__ import annotations

import argparse
from argparse import ArgumentParser
import sys
import logging

from .ext2reader import Ext2Reader


def main() -> Ext2Reader:
    parser = ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("-v", "--verbose", choices=["DEBUG", "INFO", "NONE"], default="NONE")

    parsers = parser.add_subparsers(title="command", dest="command_name")
    ls_parser = parsers.add_parser("ls")
    ls_parser.add_argument("path", type=str)

    cat_parser = parsers.add_parser("cat")
    cat_parser.add_argument("path", type=str)

    inode_info_parser = parsers.add_parser("inode_info")
    inode_info_parser.add_argument("--path", type=str)
    inode_info_parser.add_argument("--index", type=int)

    args = parser.parse_args(sys.argv[1:])

    logging_level = {
        "NONE": None,
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
    }[args.verbose]

    if logging_level:
        logging.basicConfig(level=logging.DEBUG)

    reader = Ext2Reader(args.file)

    if args.command_name == "ls":
        reader.ls_command(args.path)

    if args.command_name == "cat":
        reader.cat_command(args.path)

    if args.command_name == "inode_info":
        if args.path is None and args.index is None:
            raise argparse.ArgumentError(
                argument=None, message="either --path or --index needs to be provided"
            )

        reader.inode_info_command(path=args.path, index=args.index)

    return reader


if __name__ == "__main__":
    r = main()
