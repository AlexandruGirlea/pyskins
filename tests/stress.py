import glob
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["PYSKINS_HOME"] = os.path.join(ROOT, "no-such-folder")
os.environ["PYSKINS_PATH"] = ""

import pyskins as ps  # noqa: E402


def read(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


def all_skins():
    skins = [ps.load_skin(name) for name in ps.list_skins()]
    for path in sorted(glob.glob(os.path.join(ROOT, "examples", "skins", "*.json"))):
        skins.append(ps.load_skin(path))
    return skins


def python_files(folder):
    for base, folders, files in os.walk(folder):
        folders[:] = sorted(name for name in folders if name not in ("site-packages", "__pycache__"))
        for name in sorted(files):
            if name.endswith(".py"):
                yield os.path.join(base, name)


def saved_name(out, path, skin):
    digest = hashlib.sha1(path.encode("utf-8")).hexdigest()[:16]
    return os.path.join(out, f"{digest}.{skin.name}.pyskin")


def main(argv):
    save = verify = None
    folders = []
    arguments = list(argv)
    while arguments:
        argument = arguments.pop(0)
        if argument == "--save":
            save = arguments.pop(0)
        elif argument == "--verify":
            verify = arguments.pop(0)
        else:
            folders.append(argument)
    if not folders:
        folders = [os.path.dirname(os.__file__)]
    if save and not os.path.isdir(save):
        os.makedirs(save)

    skins = all_skins()
    counts = {"files": 0, "unreadable": 0, "not python": 0, "word clash": 0, "round trips": 0,
              "with extra emoji": 0, "verified": 0, "FAILED": 0}
    failures = []

    for folder in folders:
        for path in python_files(folder):
            try:
                source = read(path)
            except (UnicodeDecodeError, OSError):
                counts["unreadable"] += 1
                continue
            counts["files"] += 1
            for skin in skins:
                try:
                    dressed = ps.apply(source, skin, check=False)
                except ps.SkinError as error:
                    counts["word clash" if "already uses the name" in str(error) else "not python"] += 1
                    continue
                if ps.undo(dressed, skin) != source:
                    failures.append(f"{path} [{skin.name}] round trip")
                    continue
                counts["round trips"] += 1

                emoji = "".join(new for new in skin.words.values() if not ps.engine.is_word(new))
                if emoji:
                    extra = source + "\n# " + emoji + "\n_skin_test = \"" + emoji + " if else\"\n"
                    try:
                        if ps.undo(ps.apply(extra, skin, check=False), skin) != extra:
                            failures.append(f"{path} [{skin.name}] with extra emoji")
                        else:
                            counts["with extra emoji"] += 1
                    except ps.SkinError:
                        pass

                if save:
                    with open(saved_name(save, path, skin), "w", encoding="utf-8", newline="") as handle:
                        handle.write(dressed)
                if verify:
                    name = saved_name(verify, path, skin)
                    if os.path.isfile(name):
                        other = read(name)
                        if other != dressed or ps.undo(other, skin) != source:
                            failures.append(f"{path} [{skin.name}] differs from the other Python")
                        else:
                            counts["verified"] += 1

    counts["FAILED"] = len(failures)
    print(f"Python {sys.version.split()[0]}, {len(skins)} skins: {', '.join(skin.name for skin in skins)}")
    for key in counts:
        print(f"  {key:<17} {counts[key]}")
    for line in failures[:20]:
        print("  FAILED: " + line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
