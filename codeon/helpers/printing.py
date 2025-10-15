"""
hlp_printing.py
"""
import os, re, time
from datetime import datetime as dt
from colorama import Fore, Back, Style
import codeon.settings as sts
from textwrap import wrap as tw
from tabulate import tabulate as tb


# After the existing imports at the top of the file
try:
    import winsound
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False

def wrap_text(text:str, *args, max_chars:int=sts.table_max_chars, **kwargs):
    max_chars = normalize_max_chars(max_chars, text, *args, **kwargs)
    if type(text) == str and len(text) > max_chars:
        wrapped = ''
        for line in text.split('\n'):
            if len(line) > max_chars:
                line = '\n'.join(tw(line, max_chars))
            wrapped += f"\n{line}"               
        return wrapped.strip()
    return text

def pretty_prompt(prompt:str, *args, verbose:int=0, **kwargs) -> str:
    prompt = re.sub(r'<user_comment>\s*</user_comment>', '', prompt, flags=re.MULTILINE)
        # we replace the <tags> in prompt with colorized tags
    p = (
            prompt.replace('deliverable>', f"{Back.MAGENTA}deliverable{Style.RESET_ALL}>")
                .replace('rag_db_matches>', f"{Back.GREEN}rag_db_matches{Style.RESET_ALL}>")
                .replace('user_comment>', f"{Back.YELLOW}user_comment{Style.RESET_ALL}>")
                .replace('previous_responses>', f"{Back.CYAN}previous_responses{Style.RESET_ALL}>")
                .replace('sample>', f"{Back.CYAN}sample{Style.RESET_ALL}>")
                .replace('io_template>', f"{Back.CYAN}io_template{Style.RESET_ALL}>")
                .replace('INST>', f"{Back.CYAN}INST{Style.RESET_ALL}>")
                .replace('poluted_text>', f"{Back.CYAN}poluted_text{Style.RESET_ALL}>")
                .replace('__SAMPLE', f"__{Style.DIM}{Fore.WHITE}SAMPLE{Style.RESET_ALL}{Style.RESET_ALL}")
                .replace('__RESPONSE SAMPLE', f"__{Style.DIM}{Fore.WHITE}RESPONSE SAMPLE{Style.RESET_ALL}{Style.RESET_ALL}")
                .replace('__TEXT SAMPLE', f"__{Style.DIM}{Fore.WHITE}TEXT SAMPLE{Style.RESET_ALL}{Style.RESET_ALL}")
                .replace('Strategy Prompt', f"{Fore.YELLOW}Strategy Prompt{Style.RESET_ALL}")
        )
    # we color markdown headers level 1 and 2 ('# Some Text' and '## Some Text') with BLUE
    p = re.sub(r'^# (.+)$', f"{Fore.BLUE}# \\1{Fore.RESET}", p, flags=re.MULTILINE)
    p = re.sub(r'^## (.+)$', f"{Fore.BLUE}## \\1{Fore.RESET}", p, flags=re.MULTILINE)
    p = re.sub(r'^.?```(\w+)?$', f"{Fore.MAGENTA}``` \\1{Fore.RESET}", p, flags=re.MULTILINE)
    p = re.sub(r'(.*)(https?://[^\s\'_\"]+)(.*)', f"\\1{Fore.MAGENTA}\\2{Fore.RESET}\\3", p)
    if verbose >= 1:
        print(f"{p.strip()}")
    return p

def pretty_dict(name:str, d:dict, *args, **kwargs):
    print(f"\n{Fore.CYAN}{name} {Fore.RESET}\n{'*' * len(name)}")
    for k, v in d.items():
        print(f"{Fore.CYAN}{k}: {Fore.RESET}{v}")

def dict_to_table(name:str, d:dict, *args, **kwargs):
    tbl_dict = wrap_table(d, *args, **kwargs)
    tbl_dict[name] = tbl_dict.keys()
    tbl = tb(tbl_dict.items(), headers=[f'name: {name}', 'value'], tablefmt='simple')
    colored_table_underline(tbl, *args, **kwargs)


def records_to_table(name:str, records:list, *args, **kwargs):
    # Extract headers from the keys of the first result
    wrapped_records = []
    for record in records:
        wrapped_records.append(wrap_table(record, *args, **kwargs))
    headers = records[0].keys()
    # Convert d to a list of values for tabulation
    table = [key.values() for key in wrapped_records]

    # Print the table using tabulate
    colored_table_underline(tb(table, headers=headers), *args, **kwargs)

def colored_table_underline(tbl, *args, up_to:int=0, color=Fore.CYAN, **kwargs):
    print('\n')
    for i, line in enumerate(tbl.split('\n')):
        if i <= up_to:
            print(f"{color}{line}{Fore.RESET}")
        else:
            print(line)

def dict_to_table_v(name:str, d: dict, *args, **kwargs):
    """
    Prints the dictionary with keys as column headers and values as rows.
    Wraps long text using wrap_text function.
    """
    headers = list(d.keys())  # Extract keys for column headers
    row = []  # The row of values
    for key, value in d.items():
        if isinstance(value, str):
            row.append(wrap_text(value, *args, **kwargs))
        elif isinstance(value, dict):
            # If the value is another dictionary, format it for display
            row.append(
                wrap_text(
                    '\n'.join([f"{Fore.CYAN}{k}{Fore.RESET}: {str(v)}" for k, v in value.items()]),
                    **kwargs,
                )
            )
        elif isinstance(value, list):
            # If the value is a list, join the list into a string
            row.append(
                wrap_text(
                    '\n'.join([str(v) for v in value]),
                    **kwargs,
                )
            )
        else:
            # Handle any other data types (e.g., numbers, bools)
            row.append(str(value))
    # Use tabulate to create the table
    tbl = tb([row], headers=headers, tablefmt='simple')
    colored_table_underline(tbl, *args, **kwargs)

def wrap_table(d:dict, *args, **kwargs):
    tbl_dict = dict(**d)
    for kk, vs in d.items():
        if type(vs) == str:
            tbl_dict[kk] = wrap_text(vs, *args, **kwargs)
        elif type(vs) == dict:
            tbl_dict[kk] = wrap_text('\n'.join([f"{Fore.CYAN}{k}{Fore.RESET}: {str(v)}" for k, v in vs.items()]))
        elif type(vs) == list:
            tbl_dict[kk] = wrap_text('\n'.join([str(v) for v in vs]))
    return tbl_dict

def normalize_max_chars(max_chars:int, text, *args, **kwargs):
    """
    some strings contain very short texts
    those texts can use a shorter max_chars than longer texts
    so we re-compute max_chars to result in a minimum of 3 lines
    """
    if len(text) <= 50:
        return max_chars // 5
    elif len(text) <= 128:
        return max_chars // 4
    elif len(text) <= 400:
        return max_chars // 3
    elif len(text) <= 1200:
        return max_chars // 2
    else:
        return int(max_chars * 2)

def unroll_print_dict(d:dict, unroll_key:str='prompts', *args, **kwargs):
    for k, vs in d.items():
        if k == 'service_endpoint':
            print(f"\t{k = }: {Fore.MAGENTA}{vs}{Fore.RESET}")
        elif k == unroll_key:
            print(f"\t{k = }: {len(vs)}")
            for i, prompt in enumerate(vs):
                start = '\n' if i != 0 else ''
                prompt = '\n\t\t'.join(prompt[:200].split('\n'))
                print(f"{start}\t\t{Fore.MAGENTA}{i}{Fore.RESET}: {prompt[:150]}")
        else:
            print(f"\t{k = }: {vs}")

def pretty_print_df(df, *args, color:object=Fore.MAGENTA, sum_color:object=None, **kwargs):
    """
    Takes a datafram and prints it in a colored pretty format
    df.columns will be the collumns of the table
    """
    tbl = tb(df, headers='keys', tablefmt='simple')
    len_tbl = len(tbl.split('\n'))
    for i, line in enumerate(tbl.split('\n')):
        if i <= 1:
            print(f"{color}{line}{Fore.RESET}")
        elif sum_color and i == len_tbl - 1:
            print(f"{sum_color}{'_ ' * (len(line) // 2)}{Style.RESET_ALL}")
            print(f"{line}")
        else:
            print(line)

# After other functions and before main(), define play_sound
def play_sound(status: str):
    """
    Plays a short acoustic signal based on the given status.
    Args:
        status: (str) One of ["LOADED", "START", "STOP"].
    """
    if SOUND_AVAILABLE:
        if status == "PROMPT":
            winsound.Beep(600, 150)   # Lower pitch
            winsound.Beep(1000, 150)  # Higher pitch
        if status == "PROMPT0":
            winsound.Beep(600, 150)   # Lower pitch
        if status == "PROMPT1":
            winsound.Beep(1000, 150)  # Higher pitch
        if status == "PROMPT2":
            winsound.Beep(1300, 150)  # Higher pitch
        elif status == "RESPONSE":
            winsound.Beep(1000, 150)  # Higher pitch
            winsound.Beep(800, 150)   # Lower pitch
            winsound.Beep(600, 150)   # Lower pitch
        elif status == "RESPONSE0":
            winsound.Beep(1000, 100)  # Higher pitch
        elif status == "RESPONSE1":
            winsound.Beep(1200, 100)  # Higher pitch
        elif status == "RESPONSE2":
            winsound.Beep(1600, 100)  # Higher pitch
        elif status == "HAPPY":
            winsound.Beep(1400, 100)  # Higher pitch
            winsound.Beep(1600, 100)  # Higher pitch
            winsound.Beep(2000, 100)  # Higher pitch
            time.sleep(.1)
        elif status == "ERROR":
            winsound.Beep(200, 150)
            winsound.Beep(100, 550)
