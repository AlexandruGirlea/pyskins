import glob
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import pyskins as ps  # noqa: E402
from pyskins.cli import main  # noqa: E402
from pyskins.engine import check_name  # noqa: E402
from pyskins.sample import SAMPLE  # noqa: E402
from pyskins.skins import BUILT_IN_FOLDER  # noqa: E402

EXAMPLE_SKINS = sorted(glob.glob(os.path.join(ROOT, "examples", "skins", "*.json")))
posix_only = unittest.skipUnless(os.name == "posix", "file permissions are POSIX-only")
needs_symlinks = unittest.skipUnless(hasattr(os, "symlink"), "no symlinks here")


def read_text(path, newline=""):
    with io.open(path, "r", encoding="utf-8", newline=newline) as handle:
        return handle.read()


def write_text(path, text):
    with io.open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    return path


class Base(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.saved_env = dict((key, os.environ.get(key)) for key in ("PYSKINS_HOME", "PYSKINS_PATH"))
        os.environ["PYSKINS_HOME"] = os.path.join(self.folder, "home")
        os.environ["PYSKINS_PATH"] = ""
        self.saved_out = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = io.StringIO(), io.StringIO()

    def tearDown(self):
        sys.stdout, sys.stderr = self.saved_out
        for key, value in self.saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(self.folder)

    def path(self, name):
        return os.path.join(self.folder, name)

    def write(self, name, text):
        return write_text(self.path(name), text)

    def read(self, name):
        return read_text(self.path(name))

    def write_skin(self, name, data):
        return self.write(name, json.dumps(data))

    def built_in_skins(self):
        return [ps.load_skin(name) for name in ps.list_skins()]


class EngineTests(Base):
    def test_there_are_35_keywords(self):
        self.assertEqual(len(ps.KEYWORDS), 35)
        self.assertEqual(len(set(ps.KEYWORDS)), 35)

    def test_two_skins_are_included(self):
        self.assertEqual(ps.list_skins(), ["christmas", "faces"])

    def test_every_keyword_is_swapped_and_comes_back(self):
        for skin in self.built_in_skins():
            dressed = ps.apply(SAMPLE, skin)
            for word in ps.KEYWORDS:
                self.assertIn(skin.words[word], dressed, "%s: %s was not swapped" % (skin.name, word))
            self.assertEqual(ps.undo(dressed, skin), SAMPLE)

    def test_strings_comments_and_f_strings_stay_the_same(self):
        faces = ps.load_skin("faces")
        source = u'x = "if"  # else\ny = f"{a if b else c}"\nz = a if b else c\n'
        expected = u'x = "if"  # else\ny = f"{a if b else c}"\nz = a \U0001F914 b \U0001F643 c\n'
        self.assertEqual(ps.apply(source, faces), expected)
        self.assertEqual(ps.undo(expected, faces), source)

    def test_emoji_that_was_already_in_the_file_survives(self):
        faces = ps.load_skin("faces")
        source = u'mood = "\U0001F914 hmm"  # \U0001F643\nif mood: pass\n'
        dressed = ps.apply(source, faces)
        self.assertIn(u'"\U0001F914 hmm"  # \U0001F643', dressed)
        self.assertEqual(ps.undo(dressed, faces), source)

    def test_emoji_earlier_on_the_same_line(self):
        christmas = ps.load_skin("christmas")
        source = u's = "\U0001F384\U0001F384"; t = 1 if s else 2\n'
        expected = u's = "\U0001F384\U0001F384"; t = 1 \U0001F385 s \U0001F98C 2\n'
        self.assertEqual(ps.apply(source, christmas), expected)
        self.assertEqual(ps.undo(expected, christmas), source)

    def test_line_endings_tabs_and_marks_are_kept(self):
        faces = ps.load_skin("faces")
        for source in (u"if True:\r\n\tpass\r\n", u"\ufeffif True:\n    pass\n", u"x = 1", u""):
            self.assertEqual(ps.undo(ps.apply(source, faces), faces), source)
        self.assertIn(u":\r\n\t", ps.apply(u"if True:\r\n\tpass\r\n", faces))

    def test_tricky_but_valid_python(self):
        sources = [
            u"x = 1 if a else 2  # if else\n",
            u'text = """\nif this:\n    return that\n"""\n',
            u"value = [\n    item for item in data\n    if item is not None\n]\n",
            u"total = first + \\\n    second if first else None\n",
            u"def f(a, *, b=None, **rest):\n    return lambda: (yield)\n",
            u"class A(B, metaclass=M):\n    pass\n",
            u"@decorator\nasync def f():\n    async with a as b:\n        async for c in d:\n            await c\n",
            u"if x:\n\tif y:\n\t\tpass\n",
            u"def_ = 1; class_ = 2; is_not = 3; import_me = 4; returned = 5\n",
            u"print(r'\\if', b'else', rb'for', u'while')\n",
            u"x = 0xFF if 1e3 else 0o7\n",
            u"lam = lambda x=(1 if True else 2): x\n",
        ]
        for skin in self.built_in_skins():
            for source in sources:
                self.assertEqual(ps.undo(ps.apply(source, skin), skin), source, source)
        faces = ps.load_skin("faces")
        self.assertEqual(ps.apply(sources[8], faces), sources[8])

    def test_broken_python_is_refused(self):
        faces = ps.load_skin("faces")
        self.assertRaises(ps.SkinError, ps.apply, u'x = """never closed\n', faces)

    def test_own_source_code_round_trips(self):
        paths = glob.glob(os.path.join(ROOT, "pyskins", "*.py")) + glob.glob(os.path.join(HERE, "*.py"))
        self.assertTrue(len(paths) >= 6)
        for path in paths:
            source = read_text(path)
            for skin in self.built_in_skins():
                self.assertEqual(ps.undo(ps.apply(source, skin, check=False), skin), source, path)

    def test_standard_library_round_trips(self):
        folder = os.path.dirname(os.__file__)
        paths = sorted(glob.glob(os.path.join(folder, "*.py")))[:80]
        done = 0
        for path in paths:
            try:
                source = read_text(path)
            except (UnicodeDecodeError, IOError, OSError):
                continue
            for skin in self.built_in_skins():
                self.assertEqual(ps.undo(ps.apply(source, skin, check=False), skin), source, path)
            done += 1
        self.assertTrue(done >= 40, "only %d standard library files were tested" % done)


class EverySkinTests(Base):

    def test_built_in_skins_are_complete_and_explained(self):
        for skin in self.built_in_skins():
            self.assertTrue(skin.title, "%s needs a title" % skin.name)
            self.assertTrue(skin.description, "%s needs a description" % skin.name)
            self.assertEqual(os.path.basename(skin.path), skin.name + ".json")
            if skin.kind() == "emoji":
                self.assertEqual(skin.missing_keywords(), [], "%s must cover every keyword" % skin.name)
            for word in skin.words:
                self.assertTrue(skin.why.get(word), "%s: say why for %r" % (skin.name, word))

    def test_the_two_main_skins_also_cover_everyday_names(self):
        self.assertEqual(len(ps.EVERYDAY_NAMES), 26)
        for name in ("faces", "christmas"):
            skin = ps.load_skin(name)
            missing = [word for word in ps.EVERYDAY_NAMES if word not in skin.words]
            self.assertEqual(missing, [], "%s is missing %s" % (name, missing))
            self.assertEqual(len(skin.words), 35 + 26)

    def test_built_in_and_example_skins_round_trip(self):
        paths = sorted(glob.glob(os.path.join(BUILT_IN_FOLDER, "*.json"))) + EXAMPLE_SKINS
        self.assertTrue(len(paths) >= 4)
        for path in paths:
            skin = ps.load_skin(path)
            dressed = ps.apply(SAMPLE, skin)
            self.assertNotEqual(dressed, SAMPLE, path)
            self.assertEqual(ps.undo(dressed, skin), SAMPLE, path)

    def test_agent_files_have_a_simple_header(self):
        for name in (os.path.join(".apm", "skills", "pyskins", "SKILL.md"),
                     os.path.join(".apm", "instructions", "pyskins.instructions.md")):
            text = read_text(os.path.join(ROOT, name), newline=None)
            self.assertTrue(text.startswith(u"---\n"), name)
            header = text.split(u"---\n")[1].strip().split(u"\n")
            self.assertTrue(len(header) >= 2, name)
            for line in header:
                key, _, value = line.partition(u": ")
                self.assertTrue(re.match(r"^[A-Za-z]+$", key), "%s: %r" % (name, line))
                if key == "applyTo":
                    continue
                self.assertNotIn(u": ", value, "%s: a second colon breaks the header: %r" % (name, line))
                self.assertNotIn(u'"', value, "%s: %r" % (name, line))
                self.assertNotIn(u"#", value, "%s: %r" % (name, line))

    def test_example_skins_in_the_docs_are_valid(self):
        for name in ("README.md", "CONTRIBUTING.md", os.path.join(".apm", "skills", "pyskins", "SKILL.md")):
            blocks = re.findall(r"```json\n(.*?)```", read_text(os.path.join(ROOT, name), newline=None), re.S)
            self.assertTrue(blocks, "no example skin found in %s" % name)
            for block in blocks:
                data = json.loads(block)
                data.pop("extends", None)
                skin = ps.skin_from_dict(data)
                source = u"class A:\n    def b(self):\n        return print\n"
                self.assertEqual(ps.undo(ps.apply(source, skin), skin), source)


def python_that_reads_skins(folder):
    write_text(os.path.join(folder, "sitecustomize.py"), u"import pyskins.codec\npyskins.codec.register()\n")
    return dict(os.environ, PYTHONPATH=ROOT + os.pathsep + folder, PYTHONIOENCODING="utf-8")


def run_python(arguments, env):
    import subprocess
    done = subprocess.Popen([sys.executable] + arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    out, err = done.communicate()
    return done.returncode, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")


class ExampleProgramTests(Base):
    def programs(self):
        return sorted(glob.glob(os.path.join(ROOT, "examples", "*.py")))

    def test_examples_are_what_the_tool_makes(self):
        self.assertTrue(len(self.programs()) >= 7)
        for program in self.programs():
            dressed = read_text(program)
            name = ps.read_header(dressed)
            self.assertIn(name, ("christmas", "faces"), "%s does not say which skin it wears" % program)
            skin = ps.load_skin(name)
            body, _ = ps.remove_header(dressed)
            plain = ps.undo(body, skin)
            compile(plain, program, "exec")
            self.assertEqual(ps.add_header(ps.apply(plain, skin), name), dressed, "%s was edited by hand" % program)

    def test_plain_python_runs_every_example(self):
        env = python_that_reads_skins(self.folder)
        for program in self.programs():
            code, out, err = run_python([program], env)
            self.assertEqual(code, 0, "python %s failed: %s" % (program, err))
            self.assertTrue(out.strip(), "%s printed nothing" % program)
            code, same, err = run_python(["-m", "pyskins", "run", program], dict(os.environ, PYTHONPATH=ROOT, PYTHONIOENCODING="utf-8"))
            self.assertEqual(code, 0, err)
            self.assertEqual(same, out, program)

    def test_without_pyskins_python_names_the_missing_skin(self):
        env = dict(os.environ, PYTHONPATH="", PYTHONIOENCODING="utf-8")
        code, out, err = run_python([self.programs()[0]], env)
        if code != 0:
            self.assertIn("pyskins", err)

    def test_skinned_files_can_import_each_other(self):
        christmas = ps.load_skin("christmas")
        helper = u"def greet(name):\n    return \"hello \" + name\n"
        program = u"from helper import greet\n\nfor name in [\"Ana\", \"Dan\"]:\n    print(greet(name))\n"
        self.write("helper.py", ps.add_header(ps.apply(helper, christmas), "christmas"))
        self.write("program.py", ps.add_header(ps.apply(program, christmas), "christmas"))
        self.assertNotIn("def", self.read("helper.py"))
        self.assertNotIn("import", self.read("program.py"))
        code, out, err = run_python([self.path("program.py")], python_that_reads_skins(self.folder))
        self.assertEqual((code, out.split()), (0, ["hello", "Ana", "hello", "Dan"]), err)

    def test_errors_point_at_the_right_line_of_the_skinned_file(self):
        faces = ps.load_skin("faces")
        self.write("oops.py", ps.add_header(ps.apply(u"x = 1\nif x:\n    y = x / 0\n", faces), "faces"))
        code, out, err = run_python([self.path("oops.py")], python_that_reads_skins(self.folder))
        self.assertEqual(code, 1)
        self.assertIn("ZeroDivisionError", err)
        self.assertIn("line 4", err)

    def test_readme_pictures_are_up_to_date(self):
        sys.path.insert(0, os.path.join(ROOT, "assets"))
        import build_cards
        readme = read_text(os.path.join(ROOT, "README.md"))
        for name, content in build_cards.cards().items():
            self.assertEqual(read_text(os.path.join(ROOT, "assets", name)), content,
                             "%s is out of date: run python assets/build_cards.py" % name)
            self.assertIn("assets/" + name, readme)

    def test_version_is_the_same_everywhere(self):
        found = re.search(r'^version = "([^"]+)"', read_text(os.path.join(ROOT, "pyproject.toml")), re.M)
        self.assertEqual(found.group(1), ps.__version__)

    def test_readme_links_point_to_real_files(self):
        text = read_text(os.path.join(ROOT, "README.md"))
        links = re.findall(r"github\.com/AlexandruGirlea/pyskins/blob/main/([^)\"#]+)", text)
        links += re.findall(r"raw\.githubusercontent\.com/AlexandruGirlea/pyskins/main/([^)\"#]+)", text)
        self.assertTrue(len(links) >= 15, "the README should link to the examples and pictures")
        for link in links:
            self.assertTrue(os.path.exists(os.path.join(ROOT, link)), "broken link in README: %s" % link)
        self.assertNotIn("](examples/", text)
        self.assertNotIn('src="assets/', text)


class FirstLineTests(Base):
    def test_add_read_remove(self):
        self.assertEqual(ps.add_header(u"x = 1\n", "faces"), u"# coding: pyskins-faces\nx = 1\n")
        self.assertEqual(ps.read_header(u"# coding: pyskins-faces\nx = 1\n"), "faces")
        self.assertEqual(ps.read_header(u"# -*- coding: pyskins_easter-eggs -*-\n"), "easter-eggs")
        self.assertEqual(ps.read_header(u"x = 1\n"), None)
        self.assertEqual(ps.read_header(u"# coding: utf-8\n"), None)
        self.assertEqual(ps.read_header(u"\n\n# coding: pyskins-faces\n"), None)
        for source in (u"x = 1\n", u"", u"x = 1", u"#!/usr/bin/env python3\nx = 1\n", u"#!/usr/bin/env python3",
                       u"x = 1\r\ny = 2\r\n", u"# a comment\nx = 1\n"):
            dressed = ps.add_header(source, "christmas")
            self.assertEqual(ps.read_header(dressed), "christmas", repr(source))
            self.assertEqual(ps.remove_header(dressed), (source, "christmas"), repr(source))
        self.assertTrue(ps.add_header(u"#!/usr/bin/env python3\nx = 1\n", "faces").startswith(u"#!/usr/bin/env python3\n# coding"))
        self.assertIn(u"faces\r\n", ps.add_header(u"x = 1\r\n", "faces"))

    def test_files_with_their_own_coding_line_are_refused(self):
        self.assertRaises(ps.SkinError, ps.add_header, u"# -*- coding: latin-1 -*-\nx = 1\n", "faces")
        self.assertRaises(ps.SkinError, ps.add_header, u"# coding: pyskins-faces\nx = 1\n", "christmas")
        self.assertRaises(ps.SkinError, ps.add_header, u"\ufeffx = 1\n", "faces")

    def test_python_can_read_a_skinned_file_in_this_very_process(self):
        import codecs
        from pyskins.codec import register
        register()
        christmas = ps.load_skin("christmas")
        dressed = ps.add_header(ps.apply(SAMPLE, christmas), "christmas")
        text = codecs.decode(dressed.encode("utf-8"), "pyskins-christmas")
        self.assertEqual(text, u"# coding: pyskins-christmas\n" + SAMPLE)
        compile(dressed.encode("utf-8"), "sample.py", "exec")
        self.assertRaises(LookupError, codecs.lookup, "pyskins-no-such-skin")
        path = self.write("sample.py", dressed)
        with io.open(path, "r", encoding="pyskins_christmas") as handle:
            self.assertEqual(handle.read(), u"# coding: pyskins-christmas\n" + SAMPLE)


class MakeYourOwnSkinTests(Base):
    def test_a_skin_can_swap_any_name(self):
        skin = ps.skin_from_dict({"words": {"print": u"\U0001F4E3", "def": [u"\U0001F527", "a tool"]}})
        source = u'def hi():\n    print("print this")\n'
        dressed = ps.apply(source, skin)
        self.assertEqual(dressed, u'\U0001F527 hi():\n    \U0001F4E3("print this")\n')
        self.assertEqual(ps.undo(dressed, skin), source)

    def test_a_skin_made_of_words(self):
        php = ps.skin_from_dict({"name": "php", "words": {"def": "function", "None": "null", "elif": "elseif"}})
        self.assertEqual(php.kind(), "words")
        source = u'def f(x):  # def None\n    if x is None:\n        return "None"\n    elif x:\n        return None\n'
        dressed = ps.apply(source, php)
        self.assertEqual(
            dressed,
            u'function f(x):  # def None\n    if x is null:\n        return "None"\n    elseif x:\n        return null\n',
        )
        self.assertEqual(ps.undo(dressed, php), source)

    def test_a_word_skin_refuses_a_file_that_already_uses_its_words(self):
        php = ps.skin_from_dict({"name": "php", "words": {"None": "null"}})
        try:
            ps.apply(u"null = 1\nx = None\n", php)
        except ps.SkinError as error:
            self.assertIn("'null'", str(error))
            self.assertIn("'None'", str(error))
        else:
            self.fail("a clash between the file and the skin was not noticed")
        self.assertEqual(ps.apply(u'x = "null" if y is None else 1\n', php), u'x = "null" if y is null else 1\n')

    def test_a_skin_can_swap_two_keywords(self):
        opposite = ps.skin_from_dict({"words": {"True": "False", "False": "True", "and": "or", "or": "and"}})
        source = u"x = True and False or True\n"
        dressed = ps.apply(source, opposite)
        self.assertEqual(dressed, u"x = False or True and False\n")
        self.assertEqual(ps.undo(dressed, opposite), source)

    def test_emoji_and_words_can_be_mixed_in_one_skin(self):
        skin = ps.skin_from_dict({"words": {"def": u"\U0001F527", "None": "nothing"}})
        self.assertEqual(skin.kind(), "mixed")
        source = u"def f():\n    return None\n"
        self.assertEqual(ps.undo(ps.apply(source, skin), skin), source)

    def test_empty_entries_are_skipped(self):
        skin = ps.skin_from_dict({"words": {"def": [u"\U0001F527", ""], "class": ["", ""], "if": ""}})
        self.assertEqual(sorted(skin.words), ["def"])
        self.assertEqual(len(skin.missing_keywords()), 34)

    def test_unsafe_skins_are_refused(self):
        bad = [
            {"words": {}},
            {"words": {"if": ""}},
            {"words": {"if": u"\U0001F914", "else": u"\U0001F914"}},
            {"words": {"if": "when", "elif": "when"}},
            {"words": {"if": u"\U0001F914 "}},
            {"words": {"if": "&&"}},
            {"words": {"if": u"x\U0001F914"}},
            {"words": {"self": "$this"}},
            {"words": {"not a word": u"\U0001F914"}},
            {"words": {"if": u"\U0001F914", "else": u"\U0001F914\U0001F643"}},
            {"words": {"if": "if"}},
            {"words": {"elif": "else"}},
            {"extends": 5, "words": {"if": u"\U0001F914"}},
            {"description": [], "words": {"if": u"\U0001F914"}},
            [],
        ]
        for data in bad:
            self.assertRaises(ps.SkinError, ps.skin_from_dict, data)

    def test_a_skin_can_build_on_another(self):
        path = self.write_skin("easter.json", {
            "extends": "faces",
            "words": {"class": [u"\U0001F9FA", "a basket"], "pass": ""},
        })
        easter = ps.load_skin(path)
        faces = ps.load_skin("faces")
        self.assertEqual(easter.words["class"], u"\U0001F9FA")
        self.assertEqual(easter.words["def"], faces.words["def"])
        self.assertEqual(easter.why["def"], faces.why["def"])
        self.assertNotIn("pass", easter.words)
        self.assertEqual(ps.undo(ps.apply(SAMPLE, easter), easter), SAMPLE)

    def test_building_on_a_file_next_to_it_and_no_loops(self):
        self.write_skin("base.json", {"words": {"def": u"\U0001F527"}})
        child = self.write_skin("child.json", {"extends": "base.json", "words": {"if": u"\U0001F914"}})
        self.assertEqual(sorted(ps.load_skin(child).words), ["def", "if"])
        self.write_skin("a.json", {"extends": "b.json", "words": {"if": u"\U0001F914"}})
        self.write_skin("b.json", {"extends": "a.json", "words": {"def": u"\U0001F527"}})
        self.assertRaises(ps.SkinError, ps.load_skin, self.path("a.json"))

    def test_your_own_folders_are_found_by_name(self):
        os.makedirs(self.path("team"))
        self.write_skin(os.path.join("team", "pizza.json"), {"description": "Team pizza", "words": {"def": u"\U0001F355"}})
        self.assertNotIn("pizza", ps.list_skins())
        os.environ["PYSKINS_PATH"] = self.path("team")
        self.assertEqual(ps.list_skins(), ["christmas", "faces", "pizza"])
        self.assertEqual(ps.load_skin("pizza").words, {"def": u"\U0001F355"})

    def test_custom_folders_cannot_override_builtin_skins(self):
        original = ps.load_skin("christmas").words.copy()
        folder = self.path("team")
        os.makedirs(folder)
        self.write_skin(os.path.join("team", "christmas.json"), {"words": {"eval": original["print"]}})
        os.environ["PYSKINS_PATH"] = folder
        os.environ["PYSKINS_HOME"] = folder
        self.assertEqual(ps.load_skin("christmas").words, original)
        self.assertEqual(ps.load_skin(os.path.join(folder, "christmas.json")).words, {"eval": original["print"]})

    def test_unknown_skin_name_gives_a_clear_message(self):
        try:
            ps.load_skin("no-such-skin")
        except ps.SkinError as error:
            self.assertIn("christmas, faces", str(error))
        else:
            self.fail("an unknown skin name was accepted")


class CommandLineTests(Base):
    def test_list_and_show(self):
        self.assertEqual(main(["list"]), 0)
        self.assertIn("faces", sys.stdout.getvalue())
        self.assertIn("christmas", sys.stdout.getvalue())
        self.assertEqual(main(["show", "christmas"]), 0)
        self.assertIn(u"\U0001F384  class", sys.stdout.getvalue())

    def test_apply_then_undo_gives_the_same_file(self):
        self.write("in.py", SAMPLE)
        self.assertEqual(main(["apply", "christmas", self.path("in.py"), "-o", self.path("dressed.py")]), 0)
        dressed = self.read("dressed.py")
        self.assertTrue(dressed.startswith(u"# coding: pyskins-christmas\n"))
        self.assertIn(u"\U0001F384 Shape:", dressed)
        self.assertEqual(main(["undo", self.path("dressed.py"), "-o", self.path("out.py")]), 0)
        self.assertEqual(self.read("out.py"), SAMPLE)
        self.assertEqual(main(["apply", "faces", self.path("dressed.py")]), 1)
        self.assertEqual(main(["apply", "christmas", self.path("in.py"), "--bare", "-o", self.path("bare.txt")]), 0)
        self.assertFalse(self.read("bare.txt").startswith(u"# coding"))
        self.assertEqual(main(["undo", self.path("bare.txt")]), 1)
        self.assertEqual(main(["undo", self.path("bare.txt"), "--skin", "christmas", "-o", self.path("out2.py")]), 0)
        self.assertEqual(self.read("out2.py"), SAMPLE)

    def test_your_own_skin_file(self):
        mine = self.write_skin("mine.json", {"title": "Mine", "words": {"def": u"\U0001F527"}})
        source = self.write("in.py", u"def hi(): pass\n")
        self.assertEqual(main(["apply", mine, source]), 0)
        self.assertEqual(self.read("in.py"), u"# coding: pyskins-mine\n\U0001F527 hi(): pass\n")
        self.assertIn("pyskins add", sys.stderr.getvalue())

    def test_skin_can_be_given_as_an_option_or_a_path(self):
        mine = self.write_skin("mine.json", {"title": "Mine", "words": {"def": u"\U0001F527"}})
        src = self.write("in.py", u"def hi(): pass\n")
        self.assertEqual(main(["apply", src, "-s", mine, "-o", self.path("out.py")]), 0)
        self.assertEqual(self.read("out.py"), u"# coding: pyskins-mine\n\U0001F527 hi(): pass\n")
        self.assertEqual(main(["apply", "faces", src, "-s", "christmas"]), 1)
        self.assertEqual(main(["apply", src]), 1)

    def test_run_a_skinned_file(self):
        source = u'import sys\n\n\ndef hello(name):\n    return "hello " + name\n\n\nif __name__ == "__main__":\n    print(hello("Zorp"), sys.argv[1:])\n'
        self.write("plain.py", source)
        self.assertEqual(main(["apply", "christmas", self.path("plain.py"), "-o", self.path("hi.py")]), 0)
        self.assertNotIn("def", self.read("hi.py"))
        saved_argv = list(sys.argv)
        self.assertEqual(main(["run", self.path("hi.py"), "one", "--two"]), 0)
        self.assertEqual(sys.stdout.getvalue(), u"hello Zorp ['one', '--two']\n")
        self.assertEqual(sys.argv, saved_argv)
        self.assertEqual(main(["apply", "christmas", self.path("plain.py"), "--bare", "-o", self.path("bare.txt")]), 0)
        self.assertEqual(main(["run", self.path("bare.txt")]), 1)
        sys.stdout = io.StringIO()
        self.assertEqual(main(["run", "--skin", "christmas", self.path("bare.txt")]), 0)
        self.assertIn("hello Zorp", sys.stdout.getvalue())

    def test_run_shows_errors_with_the_right_line(self):
        self.write("plain.py", u"x = 1\nif x:\n    y = x / 0\n")
        self.assertEqual(main(["apply", "faces", self.path("plain.py"), "-o", self.path("oops.py")]), 0)
        self.assertEqual(main(["run", self.path("oops.py")]), 1)
        shown = sys.stderr.getvalue()
        self.assertIn("ZeroDivisionError", shown)
        self.assertIn("oops.py", shown)
        self.assertIn("line 4", shown)
        self.write("bad.py", u"# coding: pyskins-faces\n\U0001F914 True\n    x = 1\n")
        self.assertEqual(main(["run", self.path("bad.py")]), 1)
        self.assertIn("pyskins:", sys.stderr.getvalue())

    def test_new_check_add_then_use_by_name(self):
        target = self.path("pizza.json")
        self.assertEqual(main(["new", "pizza", "-o", target]), 0)
        data = json.loads(read_text(target))
        self.assertEqual(list(data["words"]), ps.KEYWORDS + ps.EVERYDAY_NAMES)
        self.assertEqual(main(["new", "pizza", "-o", target]), 1)
        self.assertEqual(main(["check", target]), 1)

        data["words"]["class"] = [u"\U0001F355", "the whole pizza"]
        data["words"]["def"] = [u"\U0001F52A", "slice it"]
        self.write_skin("pizza.json", data)
        self.assertEqual(main(["check", target]), 0)
        self.assertIn("Keywords covered: 2 of 35", sys.stdout.getvalue())

        self.assertEqual(main(["add", target]), 0)
        self.assertEqual(main(["add", target]), 1)
        self.assertEqual(main(["add", target, "--replace"]), 0)
        self.assertEqual(ps.list_skins(), ["christmas", "faces", "pizza"])
        source = self.write("in.py", u"class A:\n    def b(self): pass\n")
        self.assertEqual(main(["apply", "pizza", source]), 0)
        self.assertEqual(self.read("in.py"), u"# coding: pyskins-pizza\n\U0001F355 A:\n    \U0001F52A b(self): pass\n")
        sys.stdout = io.StringIO()
        self.assertEqual(main(["list"]), 0)
        self.assertIn("[yours:", sys.stdout.getvalue())

    def test_new_like_another_skin(self):
        target = self.path("mine.json")
        self.assertEqual(main(["new", "mine", "--like", "faces", "-o", target]), 0)
        self.assertEqual(ps.load_skin(target).words, ps.load_skin("faces").words)
        self.assertEqual(main(["check", target]), 0)

    def test_problems_give_a_message_not_a_crash(self):
        self.assertEqual(main(["show", "no-such-skin"]), 1)
        self.assertEqual(main(["apply", "faces", self.path("missing.py")]), 1)
        self.write("bad.py", u'x = """never closed\n')
        self.assertEqual(main(["apply", "faces", self.path("bad.py")]), 1)
        self.write("broken.json", u"{not json")
        self.assertEqual(main(["check", self.path("broken.json")]), 1)
        self.assertEqual(main(["new", "bad name!"]), 1)
        self.assertEqual(sys.stderr.getvalue().count("pyskins:"), 5)

class ReviewFixTests(Base):
    def test_a_skin_name_with_capitals_or_hyphens_is_refused(self):
        for bad in ("Faces", "my-skin", "MiX_ed"):
            self.assertRaises(ps.SkinError, check_name, bad)
            path = self.write(bad + ".json", json.dumps(
                {"name": bad, "title": "t", "description": "d", "words": {"def": [u"\U0001F380", "d"]}}))
            self.assertEqual(main(["check", path]), 1)
            self.assertEqual(main(["add", path]), 1)

    def test_a_skin_name_with_a_trailing_newline_is_refused(self):
        for bad in ("faces\n", "faces\nx", " faces", "faces ", "faces\t"):
            self.assertRaises(ps.SkinError, check_name, bad)

    def test_a_broken_skin_stops_the_file_rather_than_running_wrong(self):
        env = python_that_reads_skins(self.folder)
        skin = {"name": "wordy", "title": "Wordy", "description": "plain words",
                "words": {"if": ["when", "w"], "else": ["otherwise", "o"], "True": ["yes", "y"]}}
        path = self.write("wordy.json", json.dumps(skin))
        self.assertEqual(main(["add", path]), 0)
        self.write("app.py", u"x = True\nprint('ok' if x else 'no')\n")
        out = self.path("app_skinned.py")
        self.assertEqual(main(["apply", "wordy", self.path("app.py"), "-o", out]), 0)
        code, printed, err = run_python([out], env)
        self.assertEqual((code, printed.strip()), (0, "ok"), err)
        self.write(os.path.join("home", "wordy.json"), u"{ this is not valid json")
        code2, printed2, err2 = run_python([out], env)
        self.assertNotEqual(code2, 0, printed2)

    @posix_only
    def test_add_keeps_a_private_key_private(self):
        key = self.write_skin("secret.json", {"name": "secret", "title": "s", "description": "d",
                                              "words": {"def": [u"\U0001F511", "k"]}})
        os.chmod(key, 0o600)
        self.assertEqual(main(["add", key]), 0)
        installed = os.path.join(self.folder, "home", "secret.json")
        self.assertEqual(os.stat(installed).st_mode & 0o777, 0o600)


class ObfuscateTests(Base):
    def robot(self):
        return (
            u"class Robot:\n"
            u"    def greet(self, tired):\n"
            u"        if tired:\n"
            u"            return 'zzz'\n"
            u"        return 'hi'\n\n\n"
            u"robot = Robot()\n"
            u"print(robot.greet(tired=False))\n"
        )

    def test_everything_is_hidden_but_the_shape_stays(self):
        for base in (None, ps.load_skin("christmas")):
            skin, data, pieces = ps.make_total(self.robot(), base_skin=base, name="secret")
            hidden = ps.apply_total(self.robot(), skin)
            for word in ("class", "def", "return", "greet", "tired", "self",
                         "Robot", "robot", "zzz", "'hi'", "print"):
                self.assertNotIn(word, hidden, word)
            self.assertEqual(hidden.count("\n"), self.robot().count("\n"))
            self.assertIn("\n            ", hidden)
            self.assertIn("(", hidden)
            self.assertEqual(ps.undo(hidden, skin), self.robot())

    def test_obfuscate_hides_comments_and_fstrings_and_still_runs(self):
        env = python_that_reads_skins(self.folder)
        program = (
            u"# a secret comment\n"
            u"def greet(who):\n"
            u"    # say hello to who\n"
            u"    message = f\"hello {who}!\"  # inline note\n"
            u"    return message\n\n\n"
            u"print(greet(\"world\"))\n"
        )
        src = self.write("app.py", program)
        self.assertEqual(main(["obfuscate", src]), 0)
        body = self.read("app.py")
        for leak in ("secret comment", "say hello", "inline note",
                     "hello {who}", "greet", "who", "message", "world"):
            self.assertNotIn(leak, body, leak)
        self.assertEqual(body.splitlines()[0], u"# coding: pyskins-app")
        key = self.path("app.json")
        self.assertEqual(main(["add", key]), 0)
        code, out, err = run_python([src], env)
        self.assertEqual((code, out.strip()), (0, "hello world!"), err)
        self.assertEqual(main(["undo", src, "--skin", key]), 0)
        self.assertEqual(self.read("app.py"), program)

    def test_obfuscate_keeps_a_shebang_readable(self):
        program = u"#!/usr/bin/env python\nprint('hi')\n"
        skin, data, pieces = ps.make_total(program, name="s")
        hidden = ps.apply_total(program, skin)
        self.assertTrue(hidden.startswith(u"#!/usr/bin/env python\n"))
        self.assertNotIn("'hi'", hidden)
        self.assertEqual(ps.undo(hidden, skin), program)

    def test_cli_obfuscate_in_place_runs_and_comes_back(self):
        env = python_that_reads_skins(self.folder)
        src = self.write("app.py", self.robot())
        self.assertEqual(main(["obfuscate", src, "--skin", "christmas"]), 0)
        body = self.read("app.py")
        self.assertTrue(body.startswith(u"# coding: pyskins-app\n"))
        for gone in ("greet", "Robot", "'zzz'", "tired"):
            self.assertNotIn(gone, body)
        key = self.path("app.json")
        self.assertTrue(os.path.exists(key))
        self.assertEqual(main(["add", key]), 0)
        code, out, err = run_python([src], env)
        self.assertEqual((code, out.strip()), (0, "hi"), err)
        self.assertEqual(main(["undo", src, "--skin", key]), 0)
        self.assertEqual(self.read("app.py"), self.robot())

    def test_obfuscate_folder_one_key_runs_and_comes_back(self):
        env = python_that_reads_skins(self.folder)
        src = self.path("src")
        os.makedirs(os.path.join(src, "pkg"))
        app = (u"from pkg.geo import area\n\n"
               u"def main():\n"
               u"    print('total', area(3, 4))\n\n"
               u"if __name__ == '__main__':\n"
               u"    main()\n")
        geo = u"def area(w, h):\n    scratch = w * h\n    return scratch\n"
        for name, text in (("app.py", app), ("pkg/__init__.py", u""), ("pkg/geo.py", geo)):
            write_text(os.path.join(src, name), text)
        out = self.path("obf")
        key = self.path("obf.json")
        self.assertEqual(main(["obfuscate", src, "-o", out]), 0)
        entry = read_text(os.path.join(out, "app.py"))
        self.assertTrue(entry.startswith(u"# coding: pyskins-obf\n"))
        self.assertNotIn("area", entry)
        self.assertEqual(main(["add", key]), 0)
        code, printed, err = run_python([os.path.join(out, "app.py")], env)
        self.assertEqual((code, printed.strip()), (0, "total 12"), err)

    def test_obfuscate_will_not_overwrite_the_input_with_the_key(self):
        program = u"def f():\n    return 1\n"
        src = self.write("mine.py", program)
        self.assertEqual(main(["obfuscate", src, "-o", self.path("out.py"), "--key", src]), 1)
        self.assertEqual(self.read("mine.py"), program)
        self.assertFalse(os.path.exists(self.path("out.py")))

    @posix_only
    def test_obfuscate_keeps_a_private_file_private(self):
        src = self.write("mine.py", u"def f():\n    return 1\n")
        os.chmod(src, 0o600)
        out, key = self.path("out.py"), self.path("out.json")
        self.assertEqual(main(["obfuscate", src, "-o", out, "--key", key]), 0)
        self.assertEqual(os.stat(out).st_mode & 0o777, 0o600)
        self.assertEqual(os.stat(key).st_mode & 0o777, 0o600)

    @needs_symlinks
    def test_obfuscate_folder_refuses_a_symlinked_output_into_the_source(self):
        src = self.path("src")
        os.makedirs(src)
        original = u"def helper():\n    return 1\n"
        write_text(os.path.join(src, "a.py"), original)
        link = self.path("outlink")
        os.symlink(src, link)
        self.assertEqual(main(["obfuscate", src, "-o", link]), 1)
        self.assertEqual(read_text(os.path.join(src, "a.py")), original)

    def test_obfuscate_will_not_overwrite_an_existing_key(self):
        self.write("other.json", u"{}")
        src = self.write("app.py", u"def f():\n    return 1\n")
        self.assertEqual(main(["obfuscate", src, "--key", self.path("other.json")]), 1)
        self.assertEqual(self.read("other.json"), u"{}")
        self.assertEqual(self.read("app.py"), u"def f():\n    return 1\n")

    def test_obfuscate_cannot_print_to_the_screen(self):
        src = self.write("app.py", u"def f():\n    return 1\n")
        self.assertEqual(main(["obfuscate", src, "-o", "-"]), 1)
        self.assertEqual(self.read("app.py"), u"def f():\n    return 1\n")

    def test_a_theme_that_eats_the_emoji_fails_instead_of_hanging(self):
        from pyskins.obfuscate import _tokens
        self.assertRaises(ps.SkinError, _tokens, 5, ["\U0001F384"])

    @posix_only
    def test_replacing_a_key_keeps_it_as_private_as_the_source(self):
        key = self.write_skin("secret.json", {"name": "secret", "title": "s", "description": "d",
                                              "words": {"def": [u"\U0001F511", "k"]}})
        self.assertEqual(main(["add", key]), 0)
        installed = os.path.join(self.folder, "home", "secret.json")
        os.chmod(installed, 0o644)
        os.chmod(key, 0o600)
        self.assertEqual(main(["add", key, "--replace"]), 0)
        self.assertEqual(os.stat(installed).st_mode & 0o777, 0o600)

    @needs_symlinks
    def test_folder_undo_refuses_a_symlinked_output(self):
        src = self.path("src")
        os.makedirs(src)
        write_text(os.path.join(src, "a.py"), u"def helper():\n    return 1\n")
        obf = self.path("obf")
        self.assertEqual(main(["obfuscate", src, "-o", obf]), 0)
        link = self.path("backlink")
        os.symlink(obf, link)
        self.assertEqual(main(["undo", obf, "-o", link, "--skin", self.path("obf.json")]), 1)

    @needs_symlinks
    def test_obfuscate_folder_refuses_a_directory_in_the_way_of_a_copied_file(self):
        src = self.path("src")
        os.makedirs(src)
        write_text(os.path.join(src, "a.py"), u"def f():\n    return 1\n")
        write_text(os.path.join(src, "notes.txt"), u"hello\n")
        original = u"secret data\n"
        victim = self.path("victim.txt")
        write_text(victim, original)
        out = self.path("out")
        os.makedirs(os.path.join(out, "notes.txt"))
        os.symlink(victim, os.path.join(out, "notes.txt", "notes.txt"))
        self.assertEqual(main(["obfuscate", src, "-o", out]), 1)
        self.assertEqual(read_text(victim), original)

    @posix_only
    def test_folder_key_is_no_more_open_than_the_strictest_source(self):
        src = self.path("src")
        os.makedirs(src)
        a, b = os.path.join(src, "a.py"), os.path.join(src, "b.py")
        for path in (a, b):
            write_text(path, u"def f():\n    return 1\n")
        os.chmod(a, 0o640)
        os.chmod(b, 0o604)
        self.assertEqual(main(["obfuscate", src, "-o", self.path("out"), "--key", self.path("k.json")]), 0)
        mode = os.stat(self.path("k.json")).st_mode & 0o777
        self.assertEqual(mode & 0o070, 0)
        self.assertEqual(mode & 0o007, 0)
        self.assertEqual(mode, 0o600)


class SafetyTests(Base):
    def test_a_skin_name_cannot_smuggle_a_second_line(self):
        evil = u"faces\n__import__('os').system('echo hi')"
        self.assertRaises(ps.SkinError, ps.skin_from_dict, {"name": evil, "extends": "faces", "words": {"if": u"\U0001F9E8"}})
        self.assertRaises(ps.SkinError, ps.add_header, u"x = 1\n", evil)
        self.write_skin("cute.json", {"name": evil, "extends": "faces", "words": {"if": u"\U0001F9E8"}})
        self.write("p.py", u"x = 1\n")
        self.assertEqual(main(["apply", self.path("cute.json"), self.path("p.py"), "-o", self.path("out.py")]), 0)
        result = self.read("out.py")
        self.assertTrue(result.startswith(u"# coding: pyskins-cute\n"))
        self.assertNotIn("__import__", result)

    def test_a_skin_file_cannot_pretend_to_be_an_installed_skin(self):
        faces = ps.load_skin("faces")
        swapped = {w: [e, "x"] for w, e in faces.words.items()}
        swapped["True"], swapped["False"] = [faces.words["False"], "x"], [faces.words["True"], "x"]
        self.write_skin("faces.json", {"words": swapped})
        self.write("p.py", u"print(True)\n")
        self.assertEqual(main(["apply", self.path("faces.json"), self.path("p.py"), "-o", self.path("out.py")]), 1)

    def test_apply_refuses_code_that_is_not_valid_python(self):
        faces = ps.load_skin("faces")
        self.assertRaises(ps.SkinError, ps.apply, u"x = = 1\n", faces)
        self.assertRaises(ps.SkinError, ps.apply, u"if True\n    pass\n", faces)

    def test_apply_and_undo_in_place_is_the_default(self):
        self.write("same.py", u"if True:\n    pass\n")
        self.assertEqual(main(["apply", "faces", self.path("same.py")]), 0)
        self.assertTrue(self.read("same.py").startswith(u"# coding: pyskins-faces\n"))
        self.assertNotIn("if True", self.read("same.py"))
        self.assertEqual(main(["undo", self.path("same.py")]), 0)
        self.assertEqual(self.read("same.py"), u"if True:\n    pass\n")

    def test_a_new_output_file_is_not_private(self):
        import stat
        self.write("in.py", u"if True:\n    pass\n")
        out = self.path("out.py")
        self.assertEqual(main(["apply", "faces", self.path("in.py"), "-o", out]), 0)
        self.assertTrue(stat.S_IMODE(os.stat(out).st_mode) & 0o044)


if __name__ == "__main__":
    unittest.main()
