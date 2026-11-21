import io
import re
import tokenize
import warnings


class SkinError(Exception):
    pass


# Python lowercases coding names and turns '-' into '_', so only this form names exactly one skin.
NAME_OK = re.compile(r"[a-z0-9_]+")


def check_name(name):
    if not isinstance(name, str) or not NAME_OK.fullmatch(name):
        raise SkinError(
            f"A skin name may only use lowercase letters, digits and '_' (got {name!r})."
        )
    return name


def is_python(source):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            compile(source, "<pyskins>", "exec", dont_inherit=True)
    except (SyntaxError, ValueError):
        return False
    return True


def _token_types(*names):
    return set(getattr(tokenize, name) for name in names if hasattr(tokenize, name))


_NAME_TYPES = _token_types("NAME", "ASYNC", "AWAIT")

_INSIDE_START = _token_types("FSTRING_START", "TSTRING_START")
_INSIDE_END = _token_types("FSTRING_END", "TSTRING_END")

_COMMENT = _token_types("COMMENT")

_BOM = "﻿"


def is_word(replacement):
    return replacement.isidentifier()


def _spans(source, total=False):
    line_starts = [0]
    for line in source.split("\n")[:-1]:
        line_starts.append(line_starts[-1] + len(line) + 1)

    def offset(pos):
        return line_starts[pos[0] - 1] + pos[1]

    kinds = _NAME_TYPES | _COMMENT | {tokenize.STRING} if total else _NAME_TYPES
    spans = {}
    depth = 0
    fstring_at = None
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            kind, text, start, end = token[0], token[1], token[2], token[3]
            if kind in _INSIDE_START:
                if depth == 0:
                    fstring_at = start
                depth += 1
            elif kind in _INSIDE_END:
                depth -= 1
                if total and depth == 0 and fstring_at is not None:
                    first, last = offset(fstring_at), offset(end)
                    spans[(first, last)] = source[first:last]
                    fstring_at = None
            elif depth == 0 and kind in kinds:
                if kind in _COMMENT and start == (1, 0) and text.startswith("#!"):
                    continue
                first, last = offset(start), offset(end)
                if source[first:last] != text:
                    raise SkinError("Could not find my place in this file. It may use unusual line endings.")
                spans[(first, last)] = text
    except (tokenize.TokenError, SyntaxError, IndexError) as error:
        raise SkinError(f"This does not look like Python code that I can read: {error}")
    return spans


def _splice(text, edits):
    pieces = []
    position = 0
    for start, end, new in sorted(edits):
        pieces.append(text[position:start])
        pieces.append(new)
        position = end
    pieces.append(text[position:])
    return "".join(pieces)


def _undo_total(text, skin):
    bom, body = _split_bom(text)
    reverse = dict((new, word) for word, new in skin.words.items())
    if not reverse:
        return text
    return bom + _pattern(reverse).sub(lambda match: reverse[match.group()], body)


def _pattern(texts):
    return re.compile("|".join(re.escape(text) for text in sorted(texts, key=len, reverse=True)))


def _split_bom(text):
    if text.startswith(_BOM):
        return _BOM, text[len(_BOM):]
    return "", text


def apply(source, skin, check=True):
    bom, body = _split_bom(source)
    if not is_python(body):
        raise SkinError("This does not look like Python code that this Python version can read.")
    words = skin.words
    taken = dict((new, word) for word, new in words.items() if is_word(new))
    edits = []
    for (start, end), name in _spans(body).items():
        if name in words:
            edits.append((start, end, words[name]))
        elif name in taken:
            raise SkinError(
                f"This file already uses the name {name!r}. The skin {skin.name!r} needs that word to stand for {taken[name]!r}, "
                "so it could not be taken off again. Rename it in your code, or use another skin."
            )
    result = bom + _splice(body, edits)
    if check and undo(result, skin) != source:
        raise SkinError("Safety check failed: this file would not come back the same. Nothing was changed.")
    return result


def undo(text, skin):
    if getattr(skin, "total", False):
        return _undo_total(text, skin)
    bom, body = _split_bom(text)
    emoji_to_word = {}
    name_to_word = {}
    for word, new in skin.words.items():
        if is_word(new):
            name_to_word[new] = word
        else:
            emoji_to_word[new] = word
    if not emoji_to_word and not name_to_word:
        return text

    candidate = body
    placed = []
    if emoji_to_word:
        pieces = []
        position = 0
        length = 0
        for match in _pattern(emoji_to_word).finditer(body):
            before = body[position:match.start()]
            word = emoji_to_word[match.group()]
            pieces.append(before)
            length += len(before)
            placed.append((length, length + len(word), match.group()))
            pieces.append(word)
            length += len(word)
            position = match.end()
        pieces.append(body[position:])
        candidate = "".join(pieces)

    # Emoji that land outside a name were literal text in strings or comments: put them back.
    spans = _spans(candidate)
    edits = [(start, end, emoji) for start, end, emoji in placed if (start, end) not in spans]

    if name_to_word:
        from_emoji = set((start, end) for start, end, emoji in placed)
        for (start, end), name in spans.items():
            if name in name_to_word and (start, end) not in from_emoji:
                edits.append((start, end, name_to_word[name]))

    return bom + _splice(candidate, edits)


_ANY_CODING = re.compile(r"^[ \t\f]*#.*?coding[:=][ \t]*([-\w.]+)")
_PREFIX = "pyskins-"


def _header_text(skin_name):
    return "# coding: " + _PREFIX + skin_name


def header_line(skin_name):
    return _header_text(check_name(skin_name))


def _first_lines(text):
    return [line.rstrip("\r") for line in text.split("\n", 2)[:2]]


def read_header(text):
    for line in _first_lines(text):
        found = _ANY_CODING.match(line)
        if found:
            name = found.group(1)
            for prefix in (_PREFIX, _PREFIX.replace("-", "_")):
                if name.lower().startswith(prefix):
                    return name[len(prefix):]
            return None
    return None


def add_header(text, skin_name):
    if text.startswith(_BOM):
        raise SkinError("This file starts with a hidden byte-order mark. Save it as plain UTF-8 first.")
    for line in _first_lines(text):
        if _ANY_CODING.match(line):
            raise SkinError(
                f"This file already has a 'coding' line near the top ({line.strip()}). Remove that line first."
            )
    newline = "\r\n" if "\r\n" in text else "\n"
    header = header_line(skin_name)
    if text.startswith("#!"):
        end = text.find("\n") + 1
        if end == 0:
            return text + newline + header
        return text[:end] + header + newline + text[end:]
    return header + newline + text


def remove_header(text):
    name = read_header(text)
    if name is None:
        return text, None
    position = 0
    for line in text.split("\n", 2)[:2]:
        if line.rstrip("\r") == _header_text(name):
            end = position + len(line) + 1
            if end > len(text) and position > 0:
                position -= 2 if text[:position].endswith("\r\n") else 1
            return text[:position] + text[end:], name
        position += len(line) + 1
    return text, name
