# collections.py
import json, os, pyttsx3, re, shutil, subprocess, sys, textwrap, time, yaml
from contextlib import contextmanager
from pathlib import Path
from tabulate import tabulate as tb
from datetime import datetime as dt

import codeon.settings as sts

def _speak_message(message: str, *args, **kwargs):
    """Uses pyttsx3 to speak a given message."""
    try:
        engine = pyttsx3.init()
        engine.say(message)
        engine.runAndWait()
    except Exception as e:
        logging.error(f"Text-to-speech failed: {e}")


def unalias_path(work_path: str) -> str:
    """
    repplaces path aliasse such as . ~ with path text
    """
    if not any([e in work_path for e in [".", "~", "%"]]):
        return work_path
    work_path = work_path.replace(r"%USERPROFILE%", "~")
    work_path = work_path.replace("~", os.path.expanduser("~"))
    if work_path.startswith(".."):
        work_path = os.path.join(os.path.dirname(os.getcwd()), work_path[3:])
    elif work_path.startswith("."):
        work_path = os.path.join(os.getcwd(), work_path[2:])
    work_path = os.path.normpath(os.path.abspath(work_path))
    return work_path


def _handle_integer_keys(self, intDict) -> dict:
    """
    helper function for api calls
    api endpoint calls are called by providing the relevant api api index
    as an integer. During serialization its converted to string and therefore
    has to be reconverted to int here
    """
    intDict = {int(k) if str(k).isnumeric() else k: vs for k, vs in intDict.items()}
    return intDict

def prep_path(work_path: str, file_prefix=None) -> str:
    work_path = unalias_path(work_path)
    if os.path.exists(work_path):
        return work_path
    # check for extensions
    extensions = ["", sts.eext, sts.fext]
    name, extension = os.path.splitext(os.path.basename(work_path))
    for ext in extensions:
        work_path = unalias_path(f"{name}{ext}")
        if os.path.isfile(work_path):
            return work_path
    return f"{name}{extension}"

def get_sec_entry(d, matcher, ret="key", current_key=None) -> str:
    if isinstance(d, dict):
        for key, value in d.items():
            if key == matcher:
                return current_key if ret == "key" else d[key]
            elif isinstance(value, dict):
                result = get_sec_entry(value, matcher, ret, current_key=key)
                if result is not None:
                    return result
    return None

def group_text(text, charLen, *args, **kwargs):
    # performs a conditional group by charLen depending on type(text, list)
    if not text:
        return "None"
    elif type(text) is str:
        text = handle_existing_linebreaks(text, *args, **kwargs)
        # print(f"0: {text = }")
        text = '\n'.join(textwrap.wrap(text, width=charLen))
        # print(f"1: {text = }")
        text = restore_existing_linebreaks(text, *args, **kwargs)
        # print(f"2: {text = }")
        # text = text.replace(' <lb> ', '\n').replace('<lb>', '\n')
        # text = text.replace('<tab>', '\t')
    elif type(text) is list:
        text = "\n".join(textwrap.wrap("\n".join([t for t in text]), width=charLen))
    else:
        print(type(text), text)
    return '\n' + text

def collect_ignored_dirs(source, ignore_dirs, *args, **kwargs):
    """
    Uses os.walk and regular expressions to collect directories to be ignored.

    Args:
        source (str): The root directory to start searching from.
        ignore_dirs (list of str): Regular expressions for directory paths to ignore.

    Returns:
        set: A set of directories to be ignored.
    """
    ignored = set()
    regexs = [re.compile(d) for d in ignore_dirs]

    for root, dirs, _ in os.walk(source, topdown=True):
        for dir in dirs:
            dir_path = os.path.join(root, dir).replace(os.sep, '/')
            if any(regex.search(dir_path) for regex in regexs):
                ignored.add(os.path.normpath(dir_path))
    return ignored

@contextmanager
def temp_chdir(target_dir: str) -> None:
    """
    Context manager for temporarily changing the current working directory.

    Parameters:
    target_dir (str): The target directory to change to.

    Yields:
    None
    """
    original_dir = os.getcwd()
    try:
        os.chdir(target_dir)
        yield
    finally:
        os.chdir(original_dir)

def ppm(msg, *args, **kwargs):
    """
    Pretty print messages
    """
    # contents a printed without headers and table borders
    tbl_params = {'tablefmt': 'plain', 'headers': ''}
    msg["content"] = pretty_print_messages([msg["content"]], *args, **tbl_params, **kwargs)
    return pretty_print_messages([msg], *args, **kwargs)

def pretty_print_messages(messages, *args, verbose:int=0, clear=True, save=True, **kwargs):
    """
    Takes self.messages and prints them as a tabulate table with two columns 
    (role, content)
    """
    tbl = to_tbl(messages, *args, verbose=verbose, **kwargs)
    # use subprocess to clear the terminal
    if clear: subprocess.run(["cmd.exe", "/c", "cls"])
    # print(printable)
    if save: save_table(tbl, *args, **kwargs)
    return tbl

def to_tbl(data, *args, verbose:int=0, headers=['EXPERT', 'MESSAGE'], tablefmt='simple', **kwargs):
    tbl = []
    for m in data:
        name, content = m.get('name'), m.get('content', m.get('text'))
        role, mId = m.get('role'), m.get('mId')
        # content = hide_tags(content, *args, verbose=verbose, **kwargs)
        tbl.append((f"{color_expert(name, role)}\n{mId}", content))
    return tb(tbl, headers=headers, tablefmt=tablefmt)

def save_table(tbl, *args, **kwargs):
    table_path = os.path.join(sts.chat_logs_dir, f"{sts.session_time_stamp}_chat.log")
    tbl = '\n'.join([_decolorize(l) for l in tbl.split('\n')])
    with open(table_path, 'w', encoding='utf-8') as f:
        f.write(tbl)

def strip_ansi_codes(text: str) -> str:
    """
    Strip ANSI escape sequences from a text string.
    Args:
        text (str): Text containing ANSI escape codes.
    Returns:
        str: Text with ANSI codes removed.
    """
    ansi_escape = re.compile(r'\x1b\[([0-9]+)(;[0-9]+)*m')
    return ansi_escape.sub('', text)
