import unicodedata
import re

def normalize_llm_text(text: str) -> str:
    """
    Normalize punctuation produced by LLMs into plain ASCII punctuation.

    Converts:
    - em dash (—), en dash (–), minus (−) -> hyphen (-)
    - curly quotes -> straight quotes
    - curly apostrophes -> '
    - ellipsis (…) -> ...
    - non-breaking spaces -> normal spaces
    - full-width punctuation -> ASCII where possible
    """
    if not text:
        return text

    # Unicode compatibility normalization
    text = unicodedata.normalize("NFKC", text)

    replacements = {
        "\u2014": "-",   # em dash
        "\u2013": "-",   # en dash
        "\u2212": "-",   # minus sign
        "\u2010": "-",   # hyphen
        "\u2011": "-",   # non-breaking hyphen

        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201B": "'",   # single high-reversed quote
        "\u2032": "'",   # prime

        "\u201C": '"',   # left double quote
        "\u201D": '"',   # right double quote
        "\u2033": '"',   # double prime

        "\u2026": "...", # ellipsis

        "\u00A0": " ",   # non-breaking space
        "\u2002": " ",
        "\u2003": " ",
        "\u2009": " ",
        "\u202F": " ",

        "\uFF0C": ",",   # full-width comma
        "\uFF0E": ".",   # full-width period
        "\uFF1A": ":",   # full-width colon
        "\uFF1B": ";",   # full-width semicolon
        "\uFF01": "!",   # full-width exclamation
        "\uFF1F": "?",   # full-width question
        "\uFF08": "(",
        "\uFF09": ")",
        "\uFF3B": "[",
        "\uFF3D": "]",
        "\uFF5B": "{",
        "\uFF5D": "}",
    }

    for src, dst in replacements.items():
        text = text.replace(src, dst)

    # Remove excessive spaces
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()





def normalize_json_strings(obj):

    """

    Recursively normalize every string inside a JSON object.

    """

    if isinstance(obj, dict):

        return {k: normalize_json_strings(v) for k, v in obj.items()}

    if isinstance(obj, list):

        return [normalize_json_strings(v) for v in obj]

    if isinstance(obj, str):

        return normalize_llm_text(obj)

    return obj