import argparse
import io
import json
import os
import re
import shutil
import sys
import tempfile
import traceback
import types

from . import __version__
from .engine import SkinError, add_header, apply, check_name, read_header, remove_header, undo
from .obfuscate import apply_total, make_total, make_total_multi
from .sample import SAMPLE
from .skins import (
    EVERYDAY_NAMES, KEYWORDS, find_skins, is_built_in, load_skin, new_skin_text, user_folder,
)


def _read(path):
    if path == "-":
        data = sys.stdin.buffer.read() if hasattr(sys.stdin, "buffer") else sys.stdin.read()
        return data.decode("utf-8") if isinstance(data, bytes) else data
    with io.open(path, "r", encoding="utf-8", newline="") as handle:
        return handle.read()


def _umask_mode():
    current = os.umask(0)
    os.umask(current)
    return 0o666 & ~current


def _common_mode(paths):
    mode = 0o777
    for path in paths:
        mode &= os.stat(path).st_mode
    return mode


def _target_mode(path, like=None):
    paths = [name for name in (path, like) if name and name != "-" and os.path.isfile(name)]
    return _common_mode(paths) if paths else _umask_mode()


def _stage(path, text, like=None, mode=None):
    if os.path.islink(path):
        raise SkinError("%s is a symbolic link. Choose a regular output file." % (path,))
    if os.path.exists(path) and not os.path.isfile(path):
        raise SkinError("%s is not a regular output file." % (path,))
    mode = mode if mode is not None else _target_mode(path, like)
    descriptor, temporary = tempfile.mkstemp(prefix=".pyskins-", dir=os.path.dirname(os.path.abspath(path)))
    try:
        with io.open(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.chmod(temporary, mode)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise
    return temporary, path


def _write_all(items):
    staged = []
    try:
        for item in items:
            path, text, like = item[0], item[1], item[2]
            mode = item[3] if len(item) > 3 else None
            staged.append(_stage(path, text, like, mode))
    except BaseException:
        for temporary, _ in staged:
            if os.path.exists(temporary):
                os.unlink(temporary)
        raise
    for index, (temporary, path) in enumerate(staged):
        try:
            os.replace(temporary, path)
        except BaseException:
            for leftover, _ in staged[index:]:
                if os.path.exists(leftover):
                    os.unlink(leftover)
            raise


def _write(text, path=None, like=None, mode=None):
    if path:
        _write_all([(path, text, like, mode)])
        return
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.flush()
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
    else:
        sys.stdout.write(text)


def _say(lines):
    _write(u"\n".join(lines).rstrip() + u"\n")


def _tell(message):
    sys.stderr.write("pyskins: %s\n" % (message,))


def _count(number, word):
    return "%d %s%s" % (number, word, "" if number == 1 else "s")


def _json(data):
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _command_list(args):
    lines = []
    for name, path in sorted(find_skins().items()):
        try:
            text = load_skin(name).description
        except SkinError as error:
            text = "(broken: %s)" % (error,)
        where = "" if is_built_in(path) else "  [yours: %s]" % (path,)
        lines.append("%-12s %s%s" % (name, text, where))
    _say(lines)


def _command_show(args):
    skin = load_skin(args.skin)
    lines = ["%s: %s" % (skin.title or skin.name, skin.description), ""]
    width = max(len(new) for new in skin.words.values()) if skin.kind() != "emoji" else 0
    for word in sorted(skin.words, key=lambda item: item.lower()):
        lines.append("%s  %-9s %s" % (skin.words[word].ljust(width), word, skin.why.get(word, "")))
    _say(lines)


def _same_file(a, b):
    if a in ("-", None) or b in ("-", None):
        return False
    if os.path.abspath(a) == os.path.abspath(b):
        return True
    if os.path.realpath(a) == os.path.realpath(b):
        return True
    if os.path.exists(a) and os.path.exists(b):
        try:
            return os.path.samefile(a, b)
        except OSError:
            return False
    return False


def _dest(args):
    output = getattr(args, "output", None)
    if output == "-":
        return None
    if output:
        return output
    if args.file == "-":
        return None
    return args.file


def _report_dest(verb, args, dest):
    if dest and _same_file(dest, args.file):
        _tell("%s %s in place." % (verb, args.file))


def _skin_ref(args):
    positional = getattr(args, "skin_pos", None)
    if args.skin and positional:
        raise SkinError("Give the skin once: either before the file, or with --skin, not both.")
    ref = args.skin or positional
    if not ref:
        raise SkinError("Which skin? Give a name or a .json path, for example: pyskins apply christmas app.py")
    return ref


def _command_apply(args):
    ref = _skin_ref(args)
    skin = load_skin(ref)
    source = _read(args.file)
    wearing = read_header(source)
    if wearing:
        raise SkinError("This file already wears the %r skin. Take it off first: pyskins undo %s" % (wearing, args.file))
    dressed = apply(source, skin)
    if not args.bare:
        installed = _guard_installed_name(skin.name, skin)
        dressed = add_header(dressed, skin.name)
        if not installed:
            _tell("note: Python can only run this file after you add the skin: pyskins add %s" % (ref,))
    dest = _dest(args)
    _write(dressed, dest, like=args.file)
    _report_dest("dressed", args, dest)


def _skin_for(text, path, skin_name=None):
    name = skin_name or read_header(text)
    if not name:
        raise SkinError(
            "Which skin does %s wear? Its first line does not say. Tell me with --skin, for example --skin christmas."
            % (path,)
        )
    return load_skin(name)


def _folders(args, verb):
    root = os.path.realpath(args.file)
    if not args.output:
        raise SkinError("To %s a folder, give -o OUT, a new folder for the result." % (verb,))
    out = os.path.realpath(args.output)
    if _inside(out, root) or _inside(root, out):
        raise SkinError("The output folder must be separate from the folder you %s." % (verb,))
    return root, out


def _undo_suite(args):
    root, out = _folders(args, "undo")
    skin =load_skin(args.skin) if args.skin else None
    if skin is None:
        for path in _iter_py_files(root):
            header = read_header(_read(path))
            if header:
                skin = load_skin(header)
                break
        if skin is None:
            raise SkinError(
                "No skinned .py files under %s, and no --skin given." % (args.file,)
            )

    def change(src, text):
        if not read_header(text):
            return None
        body, _ = remove_header(text)
        return undo(body, skin)

    changed, _ = _mirror_tree(root, out, change)
    _tell("restored %s to %s." % (_count(changed, "file"), args.output))


def _command_undo(args):
    if os.path.isdir(args.file):
        return _undo_suite(args)
    text = _read(args.file)
    skin = _skin_for(text, args.file, args.skin)
    body, _ = remove_header(text)
    dest = _dest(args)
    _write(undo(body, skin), dest, like=args.file)
    _report_dest("took the skin off", args, dest)


def _command_run(args):
    path = args.file
    text = _read(path)
    source = undo(text, _skin_for(text, path, args.skin))
    try:
        code = compile(source, path, "exec", dont_inherit=True)
    except SyntaxError as error:
        raise SkinError("%s has a mistake on line %s: %s" % (path, error.lineno, error.msg))

    main_module = types.ModuleType("__main__")
    main_module.__file__ = path
    saved = sys.argv, sys.modules.get("__main__"), list(sys.path)
    sys.argv = [path] + list(args.arguments)
    sys.modules["__main__"] = main_module
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    try:
        from .codec import register
        register()
        exec(code, main_module.__dict__)
    except SystemExit:
        raise
    except BaseException:
        kind, value, trace = sys.exc_info()
        traceback.print_exception(kind, value, trace.tb_next)
        return 1
    finally:
        sys.argv, old_main, sys.path[:] = saved
        if old_main is not None:
            sys.modules["__main__"] = old_main
    return 0


def _command_new(args):
    name = check_name(args.name)
    path = args.output or (name + ".json")
    if os.path.exists(path):
        raise SkinError("%s already exists. I will not overwrite it." % (path,))
    like = load_skin(args.like) if args.like else None
    _write(new_skin_text(name, like), path)
    _say([
        "Created %s with all %d Python keywords and %d everyday names such as print and len."
        % (path, len(KEYWORDS), len(EVERYDAY_NAMES)),
        "",
        "Next:",
        "  1. Open it and put an emoji (and a few words why) next to each word.",
        "     The keywords come first. The everyday names are a bonus: leave any of them empty.",
        "  2. pyskins check %s        see what is still missing, and test it" % (path,),
        "  3. pyskins apply %s app.py  try it on real code" % (path,),
        "  4. pyskins add %s          then you can use it by name" % (path,),
    ])


def _command_check(args):
    skin = load_skin(args.skin)
    missing = skin.missing_keywords()
    everyday = [word for word in EVERYDAY_NAMES if word in skin.words]
    extra = [word for word in sorted(skin.words) if word not in KEYWORDS and word not in EVERYDAY_NAMES]
    lines = [
        "Skin %r is valid. It is made of %s." % (skin.name, skin.kind()),
        "Keywords covered: %d of %d." % (len(KEYWORDS) - len(missing), len(KEYWORDS)),
    ]
    if missing:
        lines.append("Not covered yet: %s" % (" ".join(missing),))
    lines.append("Everyday names covered (a bonus): %d of %d." % (len(everyday), len(EVERYDAY_NAMES)))
    if extra:
        lines.append("Also replaces these names: %s" % (" ".join(extra),))
    no_reason = [word for word in sorted(skin.words) if not skin.why.get(word)]
    if no_reason:
        lines.append("No explanation yet for: %s" % (" ".join(no_reason),))
    dressed = apply(SAMPLE, skin)
    lines.append("Test: a file with every keyword was skinned and came back exactly the same.")
    lines.extend(["", "A taste:", ""])
    lines.extend(dressed.splitlines()[6:14])
    _say(lines)


def _command_add(args):
    skin = load_skin(args.file)
    name = skin.name
    existing = find_skins().get(name)
    if existing and is_built_in(existing):
        raise SkinError("%r is a built-in skin. Give your custom skin file a different name." % (name,))
    folder = user_folder()
    if not os.path.isdir(folder):
        os.makedirs(folder)
    target = os.path.join(folder, name + ".json")
    if os.path.exists(target) and not args.replace:
        raise SkinError("You already have a skin called %r in %s. Use --replace to overwrite it." % (name, folder))
    # Save the resolved mapping: a relative "extends" would not resolve from the user folder.
    data = {
        "name": name, "title": skin.title, "description": skin.description,
        "words": {word: [new, skin.why.get(word, "")] for word, new in skin.words.items()},
    }
    if skin.total:
        data["total"] = True
    _write(_json(data), target, like=args.file)
    _say([
        "Added %r (%d words) to %s" % (name, len(skin.words), folder),
        "Use it by name:  pyskins apply %s app.py -o app_%s.py" % (name, name),
        "Then run it:     python app_%s.py" % (name,),
    ])


def _safe_stem(text):
    return re.sub(r"[^a-z0-9_]", "_", text.lower()).strip("_") or "secret"


def _guard_installed_name(name, skin):
    known = find_skins()
    if name in known and load_skin(name).words != skin.words:
        raise SkinError(
            "A different skin called %r is already installed. Use another file name, "
            "so the file cannot run with the wrong skin." % (name,)
        )
    return name in known


def _check_new_key(key_path):
    if os.path.exists(key_path):
        raise SkinError(
            "A key already exists at %s. I will not overwrite it: it may be the way back to other files. "
            "Choose another --key path, or remove it yourself." % (key_path,)
        )


_SKIP_DIRS = ("__pycache__", "node_modules", "venv", "env", "site-packages")


def _walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in sorted(dirnames) if not name.startswith(".") and name not in _SKIP_DIRS]
        yield dirpath, sorted(filenames)


def _iter_py_files(root):
    return (os.path.join(dirpath, name) for dirpath, names in _walk(root) for name in names if name.endswith(".py"))


def _inside(path, folder):
    real = os.path.realpath(path)
    return real == folder or real.startswith(folder + os.sep)


def _mirror_tree(root, out, change_py):
    out = os.path.realpath(out)
    changed = copied = 0
    for dirpath, filenames in _walk(root):
        rel = os.path.relpath(dirpath, root)
        target_dir = out if rel == os.curdir else os.path.join(out, rel)
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)
        if not _inside(target_dir, out):
            raise SkinError("%s leads outside the output folder (a symbolic link?). Stopping." % (target_dir,))
        for filename in filenames:
            src = os.path.join(dirpath, filename)
            dst = os.path.join(target_dir, filename)
            if os.path.islink(dst):
                raise SkinError("%s is a symbolic link. Stopping rather than write through it." % (dst,))
            if os.path.exists(dst) and not os.path.isfile(dst):
                raise SkinError("%s is not a regular file. Stopping rather than write through it." % (dst,))
            new_text = change_py(src, _read(src)) if filename.endswith(".py") else None
            if new_text is None:
                shutil.copy2(src, dst)
                copied += 1
            else:
                _write(new_text, dst, like=src)
                changed += 1
    return changed, copied


def _obfuscate_suite(args, base):
    root, out = _folders(args, "obfuscate")
    sources = {}
    total_py = already = 0
    for path in _iter_py_files(root):
        total_py += 1
        text = _read(path)
        if read_header(text):
            already += 1
        else:
            sources[path] = text
    if total_py == 0:
        raise SkinError("No .py files found under %s." % (args.file,))
    if not sources:
        raise SkinError("Every .py file under %s already wears a skin." % (args.file,))

    name = _safe_stem(os.path.basename(out) or os.path.basename(root))
    skin, data, pieces = make_total_multi(sources.values(), base_skin=base, name=name)
    _guard_installed_name(name, skin)

    key_path = args.key or os.path.join(os.path.dirname(out) or os.curdir, name + ".json")
    if _inside(key_path, root) or _inside(key_path, out):
        raise SkinError(
            "The key must be saved outside both folders, or it could overwrite your code "
            "(not under %s or %s)." % (args.file, args.output)
        )
    _check_new_key(key_path)

    def change(src, text):
        return add_header(apply_total(sources[src], skin), name) if src in sources else None

    changed, copied = _mirror_tree(root, out, change)
    mode = _common_mode(sources)
    _write(_json(data), key_path, mode=mode if mode & 0o400 else 0o600)

    _tell("obfuscated %s%s." % (_count(changed, "file"), " (%d already done, copied as they were)" % already if already else ""))
    if copied:
        _tell("copied %s so the folder still runs." % (_count(copied, "other file"),))
    _tell("your originals under %s were not changed." % (args.file,))
    _tell("key saved to %s -- keep it, it is the only way back." % (key_path,))
    _tell("install the key once:  pyskins add %s" % (key_path,))
    _tell("then run as usual:     python %s" % (os.path.join(args.output, "<your entry file>.py"),))
    _tell("get it all back:       pyskins undo %s -o %s --skin %s" % (args.output, args.file.rstrip("/\\") + "_plain", key_path))


def _command_obfuscate(args):
    base = load_skin(args.skin) if args.skin else None
    if os.path.isdir(args.file):
        return _obfuscate_suite(args, base)
    if args.file == "-":
        raise SkinError("Obfuscation needs a file to work on, not text piped in.")
    source = _read(args.file)
    if read_header(source):
        raise SkinError("This file already wears a skin. Take it off first: pyskins undo %s" % (args.file,))
    if args.output == "-":
        raise SkinError("Obfuscation also writes a key, so it cannot print to the screen. "
                        "Give a file with -o, or leave -o off to change the file in place.")

    out = args.output or args.file
    name = _safe_stem(os.path.splitext(os.path.basename(out))[0])
    skin, data, pieces = make_total(source, base_skin=base, name=name)
    _guard_installed_name(name, skin)

    key_path = args.key or os.path.join(os.path.dirname(os.path.abspath(out)), name + ".json")
    if _same_file(args.file, key_path) or _same_file(out, key_path):
        raise SkinError("The key would overwrite your code. Choose another --key path.")
    _check_new_key(key_path)

    obfuscated = add_header(apply_total(source, skin), name)
    # Key first: if the code write fails, the source is never left hidden without a key.
    _write_all([(key_path, _json(data), args.file), (out, obfuscated, args.file)])

    _tell("hid %s of your file%s." % (_count(len(pieces), "piece"), " (keywords themed)" if base else ""))
    _report_dest("obfuscated", args, out)
    _tell("key saved to %s -- keep it, it is the only way back." % (key_path,))
    _tell("run it with:   pyskins run --skin %s %s" % (key_path, out))
    _tell("get it back:   pyskins undo %s --skin %s" % (out, key_path))


def build_parser():
    parser = argparse.ArgumentParser(
        prog="pyskins",
        description="Dress your Python code in emoji, take the skin off again, "
        "or run it with the skin on. Same Python underneath.",
    )
    parser.add_argument("--version", action="version", version="pyskins " + __version__)
    commands = parser.add_subparsers(dest="command", title="commands")
    skin_help = 'a skin name such as "faces", or the path to your own .json file'
    output_help = "write a copy here and keep the original (default: change the file in place; use '-' for the screen)"

    sub = commands.add_parser("list", help="show the skins you can use")
    sub.set_defaults(run=_command_list)

    sub = commands.add_parser("show", help="show what stands for which word")
    sub.add_argument("skin", help=skin_help)
    sub.set_defaults(run=_command_show)

    sub = commands.add_parser("apply", help="put a skin on a Python file")
    sub.add_argument("skin_pos", nargs="?", metavar="SKIN", help=skin_help)
    sub.add_argument("file", help='the file to change, or "-" to read what you type or pipe in')
    sub.add_argument("-s", "--skin", help="the skin, given as an option instead of before the file (a name or a .json path)")
    sub.add_argument("-o", "--output", help=output_help)
    sub.add_argument("--bare", action="store_true", help="leave out the first line that names the skin")
    sub.set_defaults(run=_command_apply)

    sub = commands.add_parser("undo", help="take the skin off and get normal Python back")
    sub.add_argument("file", help='the skinned file, a folder of them, or "-" to read what you type or pipe in')
    sub.add_argument("-s", "--skin", help="the skin the file wears, a name or a .json path (only needed if its first line does not say)")
    sub.add_argument("-o", "--output", help=output_help)
    sub.set_defaults(run=_command_undo)

    sub = commands.add_parser("run", help="run a skinned file (plain python can do it too, once pyskins is installed)")
    sub.add_argument("--skin", help="the skin the file wears (only needed if its first line does not say)")
    sub.add_argument("file", help="the skinned file to run")
    sub.add_argument("arguments", nargs=argparse.REMAINDER, help="anything after the file goes to your program")
    sub.set_defaults(run=_command_run)

    sub = commands.add_parser("new", help="start a new skin: a file with every word listed, ready to fill in")
    sub.add_argument("name", help="the name of your skin, such as pizza")
    sub.add_argument("--like", metavar="SKIN", help="start from a copy of this skin")
    sub.add_argument("-o", "--output", help="where to write the file (default: NAME.json in this folder)")
    sub.set_defaults(run=_command_new)

    sub = commands.add_parser("check", help="check a skin: rules, missing keywords, and a real test")
    sub.add_argument("skin", help=skin_help)
    sub.set_defaults(run=_command_check)

    sub = commands.add_parser("add", help="add your skin file to your own skins, so you can use it by name")
    sub.add_argument("file", help="the .json file of your skin")
    sub.add_argument("--replace", action="store_true", help="overwrite a skin of yours with the same name")
    sub.set_defaults(run=_command_add)

    sub = commands.add_parser("obfuscate", help="hide everything in emoji but keep the Python shape. undo brings it back")
    sub.add_argument("file", help="the Python file, or a whole folder of them, to obfuscate")
    sub.add_argument("-s", "--skin", help="flavour the keywords with a theme, such as christmas")
    sub.add_argument("-o", "--output", help="write a copy here (default: obfuscate the file in place); for a folder, a new folder")
    sub.add_argument("--key", help="where to save the key (default: next to the output)")
    sub.set_defaults(run=_command_obfuscate)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "run", None):
        parser.print_help()
        return 2
    try:
        return args.run(args) or 0
    except SkinError as error:
        _tell(error)
    except UnicodeError:
        _tell("files must contain valid UTF-8 text.")
    except (IOError, OSError) as error:
        _tell("could not read or write the file: %s" % (error,))
    return 1


if __name__ == "__main__":
    sys.exit(main())
