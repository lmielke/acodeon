"""
parses codeon arguments and keyword arguments
args are provided by a function call to mk_args()

RUN like:
import codeon.arguments
kwargs.update(arguments.mk_args().__dict__)
"""
import argparse
from typing import Dict


def mk_args():
    parser = argparse.ArgumentParser(description="run: python -m codeon <api> [options]")
    parser.add_argument(
        "api",
        metavar="api",
        help="API to run (e.g., info, update, server).",
    )

    # --- API-specific arguments ---
    # For 'update' API
    parser.add_argument(
        "-cr",
        "--cr_id",
        type=str,
        help="Id of change request to process. (i.e. 2025-10-09-12-32-22)",
    )
    parser.add_argument(
        "-s",
        "--source_path",
        type=str,
        help="path to the source file to update.",
    )
    parser.add_argument(
        "-c",
        "--cr_integration_path",
        type=str,
        help="path to the update/cr_integration_file.",
    )
    parser.add_argument(
        "-j",
        "--json-string",
        type=str,
        help="JSON string with 'target' and 'code' keys (used with 'create').",
    )
    parser.add_argument(
        "--hard",
        action="store_true",
        help="Overwrite the source file directly (used with 'update').",
    )
    parser.add_argument(
        "-b",
        "--black",
        action="store_true",
        help="Format the output file using 'black' (used with 'update').",
    )
    parser.add_argument(
        "-t",
        "--testing",
        action="store_true",
        help="Run tests on the output file to veryfy correct syntax.",
    )

    # For 'server' API
    parser.add_argument(
        "--port",
        type=str,
        help="Port for the server to run on (e.g., 9007).",
    )

    # For 'info' API
    parser.add_argument(
        "-i",
        "--infos",
        nargs="+",
        type=str,
        help="List of infos to retrieve (used with 'info').",
    )

    parser.add_argument(
        "-pi",
        "--prompt_info",
        action="store_true",
        help="Runs info as part of a prompt generation",
    )
    # --- General arguments ---
    parser.add_argument(
        "-v",
        "--verbose",
        nargs="?",
        const=1,
        type=int,
        default=0,
        help="Set verbosity level: 0=silent, 1=user, 2=debug.",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Run without confirmation (not currently used).",
    )

    return parser.parse_args()


def get_required_flags(parser: argparse.ArgumentParser) -> Dict[str, bool]:
    """
    Extracts the 'required' flag for each argument from an argparse.ArgumentParser object.
    """
    required_flags = {}
    for action in parser._actions:
        if action.dest in ("help", "version"):
            continue
        # Positional arguments are required by default (no option_strings).
        is_required = action.required or not action.option_strings
        for option_string in action.option_strings:
            required_flags[option_string] = is_required
        if not action.option_strings:  # For positional arguments
            required_flags[action.dest] = is_required
    return required_flags


if __name__ == "__main__":
    # Note: Running this file directly will cause an error
    # because the 'api' argument is required.
    # Use 'python -m codeon -h' to test.
    parser = mk_args()
    required_flags = get_required_flags(parser)
    print(required_flags)