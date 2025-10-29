# codeon\helpers\string_parser.py
import re
import json
from colorama import Fore, Style

import codeon.settings as sts
from codeon.headers import PackageCrHeads


class JsonParser:
    """
    Progressive JSON recovery: try strict first, then minimal safe repairs.
    WHY: tolerate LLM/paste noise while converging to valid JSON deterministically.
    """

    def __init__(self, *args, json_string: str, **kwargs) -> None:
        self.raw_string = json_string
        # Use dict instead of Optional[Dict]
        self.data: dict = None
        self.strategies = [
            self._strategy_strict_parse,
            self._strategy_find_json_block,
            self._strategy_fix_trailing_commas,
            self._strategy_fix_quotes_and_commas,
        ]

    def __call__(self, *args, **kwargs) -> dict | None:
        if not self.raw_string:
            return None
        self.parse(*args, **kwargs)
        return self.data

    def parse(self, *args, **kwargs) -> None:
        """Applies parsing strategies sequentially until one succeeds."""
        for s in self.strategies:
            d = s(*args, **kwargs)
            if d is not None and d.get(sts.json_target):
                self.data = d
                break

    def _strategy_strict_parse(self, *args, **kwargs) -> dict | None:
        """Try standard JSON decoding."""
        try:
            return json.loads(self.raw_string)
        except json.JSONDecodeError:
            return None

    def _strategy_find_json_block(self, *args, **kwargs) -> dict | None:
        """Find the outermost JSON block in the string."""
        m = re.search(r"\{[\s\S]*\}", self.raw_string)
        if not m:
            return None
        prev_string = self.raw_string
        self.raw_string = m.group(0)
        d = self._strategy_strict_parse(*args, **kwargs)
        # Restore original if parsing failed
        self.raw_string = self.raw_string if d is not None else prev_string
        return d

    def _strategy_fix_trailing_commas(self, *args, **kwargs) -> dict | None:
        """Remove trailing commas before closing braces/brackets."""
        cleaned = re.sub(r",\s*([\}\]])", r"\1", self.raw_string)
        if cleaned == self.raw_string:
            return None
        prev_string = self.raw_string
        self.raw_string = cleaned
        d = self._strategy_strict_parse(*args, **kwargs)
        # Restore original if parsing failed
        self.raw_string = self.raw_string if d is not None else prev_string
        return d

    def _strategy_fix_quotes_and_commas(self, *args, **kwargs) -> dict | None:
        """Fix missing commas between objects and replace single quotes."""
        s = re.sub(r'(["\]\}])\s*\n\s*(["\[\{])', r"\1,\n\2", self.raw_string)
        s = s.replace("'", '"')
        prev_string = self.raw_string
        self.raw_string = s
        d = self._strategy_strict_parse(*args, **kwargs)
        # Restore original if parsing failed
        self.raw_string = self.raw_string if d is not None else prev_string
        return d


class MdParser:
    """
    Parses a markdown string (e.g., from an LLM response) to extract the
    __cr_integration_file__ content and validates the package header.
    """

    def __init__(self, *args, md_string: str, **kwargs) -> None:
        self.raw_string: str = md_string
        self.cleaned_content: str | None = None
        self.is_valid: bool = False

    def __call__(self, *args, **kwargs) -> str | None:
        """Entry point for parsing and validation."""
        if not self.raw_string:
            return None
        self.cleaned_content = self.parse(*args, **kwargs)
        self.is_valid = self.cleaned_content is not None
        return self.cleaned_content

    def parse(self, *args, **kwargs) -> str | None:
        """Applies cleaning and then validates the package header."""
        cleaned = self._clean_content(*args, **kwargs)
        if not cleaned:
            return None
        return cleaned if self._validate_package_header(cleaned) else None

    def _clean_content(self, *args, **kwargs) -> str | None:
        """Removes pre-header text and markdown fences."""
        match = re.compile(sts.pg_header_regex, re.DOTALL).search(self.raw_string)
        content = self.raw_string[match.start() :] if match else self.raw_string
        content = re.compile(sts.md_fence_regex, re.MULTILINE).sub("", content)
        return content.strip()

    def _validate_package_header(self, content: str, *args, **kwargs) -> bool:
        """Checks for and structurally validates the package header."""
        header_match = re.compile(sts.pg_header_regex, re.MULTILINE).search(content)
        if not header_match:
            print(f"{Fore.RED}MdParser Error:{Fore.RESET} Missing package header.\n{content = }")
            return False

        try:
            op = PackageCrHeads()
            op(head=header_match.group(0).strip(), verbose=0)
            return True
        except (ValueError, AssertionError) as e:
            print(f"{Fore.RED}MdParser Error:{Fore.RESET} Invalid header syntax: {e}")
            return False