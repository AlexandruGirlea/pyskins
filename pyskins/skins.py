import json
import os

from .engine import SkinError, check_name, is_word

BUILT_IN_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skins")

KEYWORDS = (
    "class def return if elif else for while break continue pass try except finally raise "
    "assert True False None and or not in is import from as with lambda yield del global "
    "nonlocal async await"
).split()


EVERYDAY_NAMES = (
    "print input len range enumerate open sorted sum min max zip any all type isinstance "
    "super self str int float bool list dict set tuple Exception"
).split()


class Skin:
    def __init__(self, name, title, description, words, why, path=None, total=False):
        self.name = name
        self.title = title
        self.description = description
        self.words = words
        self.why = why
        self.path = path
        self.total = total

    def missing_keywords(self):
        return [word for word in KEYWORDS if word not in self.words]

    def kind(self):
        made_of = set("words" if is_word(new) else "emoji" for new in self.words.values())
        return made_of.pop() if len(made_of) == 1 else "mixed"

    def __repr__(self):
        return f"Skin({self.name!r}, {len(self.words)} words)"


def user_folder():
    return os.environ.get("PYSKINS_HOME") or os.path.join(os.path.expanduser("~"), ".pyskins")


def skin_folders():
    folders = [BUILT_IN_FOLDER]
    folders.extend(part for part in os.environ.get("PYSKINS_PATH", "").split(os.pathsep) if part)
    folders.append(user_folder())
    return folders


def find_skins():
    found = {}
    for folder in skin_folders():
        if not os.path.isdir(folder):
            continue
        for filename in sorted(os.listdir(folder)):
            name = filename[:-len(".json")]
            if filename.endswith(".json") and name and name not in found:
                found[name] = os.path.join(folder, filename)
    return found


def list_skins():
    return sorted(find_skins())


def is_built_in(path):
    return os.path.dirname(os.path.abspath(path)) == BUILT_IN_FOLDER


def _check_replacement(word, new, words):
    for character in new:
        if character.isspace():
            raise SkinError(f"The replacement for {word!r} contains a space.")
    if is_word(new):
        if new == word:
            raise SkinError(f"{word!r} is replaced by itself. Leave it out of the skin.")
        if new in KEYWORDS and new not in words:
            raise SkinError(
                f"{word!r} is replaced by {new!r}, which is a Python keyword. That is only possible "
                f"if the skin also replaces {new!r} with something else."
            )
        return
    for character in new:
        if ord(character) < 128 or character.isalnum():
            raise SkinError(
                f"The replacement for {word!r} is {new!r}. Use emoji only, or one plain word made of letters. "
                "A mix, or signs such as # or &, could be mistaken for code."
            )


def skin_from_dict(data, name=None, path=None, _loading=()):
    if not isinstance(data, dict) or not isinstance(data.get("words", {}), dict):
        raise SkinError('A skin is a JSON object with a "words" section.')
    for field in ("name", "title", "description", "extends"):
        if field in data and not isinstance(data[field], str):
            raise SkinError(f"The {field!r} field must be text.")

    total = bool(data.get("total"))

    words = {}
    why = {}
    if data.get("extends"):
        folder = os.path.dirname(path) if path else None
        base = load_skin(data["extends"], _folder=folder, _loading=_loading)
        words.update(base.words)
        why.update(base.why)

    for word, value in data.get("words", {}).items():
        if isinstance(value, (list, tuple)):
            new = value[0] if value else ""
            reason = value[1] if len(value) > 1 else ""
        else:
            new, reason = value, ""
        if not isinstance(new, str) or not isinstance(reason, str):
            raise SkinError(f"The entry for {word!r} must be text.")
        if not total and not word.isidentifier():
            raise SkinError(f"{word!r} is not a Python word.")
        if not new:
            words.pop(word, None)
            why.pop(word, None)
            continue
        words[word] = new
        why[word] = reason

    if not words:
        raise SkinError("This skin does not replace any word yet. Fill in at least one.")
    for word, new in words.items():
        _check_replacement(word, new, words)

    seen = {}
    for word, new in words.items():
        if new in seen:
            raise SkinError(f"{seen[new]!r} and {word!r} use the same replacement {new}.")
        seen[new] = word
    emoji = [new for new in seen if not is_word(new)]
    for one in emoji:
        for other in emoji:
            if one != other and one in other:
                raise SkinError(
                    f"The emoji for {seen[one]!r} is part of the emoji for {seen[other]!r}. They could be confused."
                )

    return Skin(
        name=check_name(name or data.get("name") or "custom"),
        title=data.get("title") or "",
        description=data.get("description") or "",
        words=words,
        why=why,
        path=path,
        total=total,
    )


def load_skin(name_or_path, _folder=None, _loading=()):
    looks_like_path = name_or_path.endswith(".json") or os.sep in name_or_path or "/" in name_or_path
    if looks_like_path:
        path = name_or_path
        if _folder and not os.path.isabs(path):
            path = os.path.join(_folder, path)
        name = os.path.splitext(os.path.basename(path))[0]
    else:
        name = name_or_path
        path = find_skins().get(name)
        if path is None:
            raise SkinError(
                "There is no skin called {!r}. Skins you can use: {}. "
                "Or give the path to your own .json file.".format(name, ", ".join(list_skins()))
            )
    key = os.path.abspath(path)
    if key in _loading:
        raise SkinError(f"The skin {name!r} extends itself, directly or through another skin.")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as error:
        raise SkinError(f"Could not open the skin file {path}: {error}")
    except ValueError as error:
        raise SkinError(f"The skin file {path} is not valid JSON: {error}")
    return skin_from_dict(data, name=name, path=path, _loading=_loading + (key,))


def new_skin_text(name, like=None):
    lines = [
        "{",
        f'  "name": {json.dumps(name)},',
        f'  "title": {json.dumps(name.capitalize())},',
        '  "description": "Say in one line what this skin is.",',
        '  "words": {',
    ]
    entries = []
    listed = KEYWORDS + EVERYDAY_NAMES
    if like:
        listed = listed + [word for word in sorted(like.words) if word not in listed]
    for word in listed:
        new = like.words.get(word, "") if like else ""
        reason = like.why.get(word, "") if like else ""
        entries.append(f"    {json.dumps(word)}: [{json.dumps(new, ensure_ascii=False)}, {json.dumps(reason, ensure_ascii=False)}]")
    lines.append(",\n".join(entries))
    lines.extend(["  }", "}", ""])
    return "\n".join(lines)
