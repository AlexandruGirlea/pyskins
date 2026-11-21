import itertools

from .engine import SkinError, _spans, _splice, _undo_total
from .skins import skin_from_dict

_POOL = list(dict.fromkeys(
    u"\U0001F7E5\U0001F7E7\U0001F7E8\U0001F7E9\U0001F7E6\U0001F7EA\U0001F7EB"
    u"\U00002B1B\U00002B1C\U0001F536\U0001F537\U0001F538\U0001F539\U0001F53A"
    u"\U0001F53B\U0001F4A0\U0001F518\U0001F7E0\U0001F7E1\U0001F7E2\U0001F535"
    u"\U0001F7E3\U0001F7E4\U000026AB\U000026AA"
    u"\U0001F34F\U0001F34E\U0001F34A\U0001F34B\U0001F34C\U0001F349\U0001F347"
    u"\U0001F353\U0001FAD0\U0001F348\U0001F352\U0001F351\U0001F96D\U0001F34D"
    u"\U0001F965\U0001F95D\U0001F345\U0001F346\U0001F951\U0001F966\U0001F952"
    u"\U0001F336\U0001F955\U0001F33D\U0001F360\U0001F950\U0001F956\U0001F968"
    u"\U0001F9C0\U0001F95A\U0001F373\U0001F9C7\U0001F95E\U0001F9C8\U0001F953"
    u"\U0001F436\U0001F431\U0001F42D\U0001F439\U0001F430\U0001F98A\U0001F43B"
    u"\U0001F43C\U0001F428\U0001F42F\U0001F981\U0001F42E\U0001F437\U0001F438"
    u"\U0001F435\U0001F414\U0001F427\U0001F426\U0001F424\U0001F986\U0001F985"
    u"\U0001F989\U0001F987\U0001F43A\U0001F417\U0001F434\U0001F984\U0001F41D"
    u"\U0001F41B\U0001F98B\U0001F40C\U0001F41E\U0001F41C\U0001FAB2\U0001F422"
    u"\U0001F40D\U0001F98E\U0001F996\U0001F995\U0001F419\U0001F991\U0001F990"
    u"\U0001F99E\U0001F980\U0001F421\U0001F420\U0001F41F\U0001F42C\U0001F433"
    u"\U0001F40B\U0001F988"
))


def _tokens(count, pool):
    if count <= len(pool):
        return list(pool[:count])
    if len(pool) < 2:
        raise SkinError("Not enough emoji left to obfuscate this file: the theme uses too many.")
    width = 2
    while len(pool) ** width < count:
        width += 1
        if width > 4:
            raise SkinError("This file has too many pieces to obfuscate at once (%d)." % (count,))
    out = []
    for combo in itertools.product(pool, repeat=width):
        out.append(u"".join(combo))
        if len(out) == count:
            break
    return out


def apply_total(source, skin):
    edits = []
    for (start, end), text in _spans(source, total=True).items():
        if text in skin.words:
            edits.append((start, end, skin.words[text]))
    return _splice(source, edits)


def _pieces(sources):
    return list(dict.fromkeys(text for source in sources for _, text in sorted(_spans(source, total=True).items())))


def _build_skin(pieces, base_skin, name, title):
    base_words = base_skin.words if base_skin is not None else {}
    taken = set(base_words.values())
    pool = [emoji for emoji in _POOL if emoji not in taken]

    need = [text for text in pieces if text not in base_words]
    tokens = _tokens(len(need), pool)

    mapping = {}
    for text in pieces:
        if text in base_words:
            mapping[text] = base_words[text]
    for text, token in zip(need, tokens):
        mapping[text] = token

    data = {
        "name": name,
        "title": title or "Obfuscated",
        "total": True,
        "description": "A key made for your file(s). Keep it: you need it to read them again.",
        "words": dict((text, [emoji, "obfuscated"]) for text, emoji in mapping.items()),
    }
    return skin_from_dict(data, name=name), data


def make_total(source, base_skin=None, name="secret", title=None):
    return make_total_multi([source], base_skin, name, title)


def make_total_multi(sources, base_skin=None, name="secret", title=None):
    sources = list(sources)
    pieces = _pieces(sources)
    skin, data = _build_skin(pieces, base_skin, name, title)
    for source in sources:
        if _undo_total(apply_total(source, skin), skin) != source:
            raise SkinError("A file could not be obfuscated reversibly. Nothing was changed.")
    return skin, data, pieces
