---
name: pyskins
description: Write and run Python files that are written in emoji, using the pyskins command to put a skin on normal Python or take it off. Use when the user asks for a program in a skin such as faces or christmas, when a Python file starts with a coding line that names a pyskins skin or shows emoji where keywords should be (for example 🧐 instead of class), or when they want a new skin made.
---

# Python skins

A skinned Python file is a normal `.py` file in which the keywords, and everyday names such as `print` and `len`, are shown as emoji. `class Robot:` is `🧐 Robot:` in the `faces` skin and `🎄 Robot:` in the `christmas` skin.

The file starts with a line that names its skin:

```text
# coding: pyskins-christmas
```

With `pyskins` installed, Python reads that line and runs the file like any other: `python robot.py`. It is only a skin. Underneath it is the same Python, and it behaves exactly the same.

The people who use this are coding with an AI assistant, which is you. Nobody types these emoji on a keyboard. The user says what they want, and you produce the skinned program with the tool.

## The one rule

Write the program as normal Python, and let `pyskins` put the skin on.

Do not write or edit emoji code yourself, not even one line. A skin maps about 60 words to 60 emoji, and nobody, person or model, recalls all of them reliably. One wrong emoji gives a file that does not run. The tool does not make that mistake: before it returns a skinned file, it takes the skin off again and checks that the result equals the original.

## When the user wants a program in a skin

1. Write the program as normal Python, in a working file such as `robot_plain.py`. Run it and test it as you always would.
2. Put the skin on. The result is the file the user asked for:

   ```sh
   pyskins apply christmas robot_plain.py -o robot.py
   ```

3. Run the skinned file, to show that it works:

   ```sh
   python robot.py
   ```

   If Python stops with an error that names `pyskins-christmas` (it says `unknown encoding` or `encoding problem`), then `pyskins` is not installed for that Python. Use `pyskins run robot.py`, which always works, and tell the user that `pip install pyskins` makes plain `python` work too.

4. Show the user the skinned code and what it printed.
5. Ask whether they want to keep the plain working file. Most users want only the skinned one, because the skin is the point. Deleting the plain file loses nothing: `pyskins undo robot.py` brings it back at any time.

## When the user wants a change to a skinned program

Take the skin off, change the Python, put the skin back on:

```sh
pyskins undo robot.py -o robot_plain.py
# edit and test robot_plain.py
pyskins apply christmas robot_plain.py -o robot.py
python robot.py
```

`pyskins undo` reads the skin from the first line of the file. `pyskins apply` refuses a file that already wears a skin, so you cannot skin a file twice by accident.

## Commands

```sh
pyskins list                           # the skins that are installed
pyskins show faces                     # every word of a skin, its emoji, and why
pyskins apply SKIN app.py              # skin on, in place (adds the first line that names the skin)
pyskins apply -s ./my.json app.py      # SKIN may be a built-in name or a path to a .json skin
python app.py                          # run it
pyskins run app.py [arguments]         # run it, when pyskins is not installed into that Python
pyskins undo app.py                    # skin off, in place
```

`apply`, `undo` and `obfuscate` change the file in place by default; `-o FILE` writes a copy and keeps the original. For `apply` and `undo`, `-o -` prints to the screen (`obfuscate` cannot print, because it also writes a key). `SKIN` is a built-in name such as `faces` or `christmas`, **or a path to the user's own `.json` skin** — users are never limited to the built-ins, and need no library update to use their own.

Use `-` as the file to read from a pipe. `python -m pyskins` works the same as `pyskins`.

If `pyskins` is not installed, say so and ask before you install it:

```sh
pip install pyskins
```

It has no dependencies and runs on Python 3.8 or newer.

## What to expect

- A skin swaps a word only where Python reads it as a name. Strings, comments and f-strings are left alone, so `"if"` in a string stays `"if"`.
- Spacing, line endings and blank lines stay exactly as they were. The skinned file has one line more than the plain one: the first line.
- The first line must stay the first line (or the second, after a `#!` line). Python only looks there.
- Skinned files can import each other, and can import normal Python files.
- The editor underlines the emoji, because it does not know about skins. That is expected. Tell the user if they ask.
- Linters, formatters, type checkers and most test runners need normal Python. Take the skin off for those.
- `apply` refuses a file that is not valid Python. Fix the syntax error in the plain file first.
- If Python or `pyskins` reports a mistake in a skinned file, it was probably edited by hand. Take the skin off and fix the Python. Do not repair the emoji yourself.

When you show skinned code in a chat, put it in a `text` code block, not a `python` one.

## Hiding what the code does (obfuscation)

A theme skin keeps the code readable. To hide it, `pyskins obfuscate` turns *everything* — every name the user invented, every keyword, every string — into emoji, while keeping the Python shape (indentation, punctuation, line breaks). It still runs, because the file carries a first line that names its key and pyskins turns it back before Python runs it.

```sh
pyskins obfuscate app.py --skin christmas
```

This changes `app.py` in place and writes `app.json` (the key) beside it; add `-o secret.py` to keep the original instead. The key is the only way back and the only way to run it, so tell the user to keep it.

- Run it: after `pyskins add app.json`, plain `python app.py` works; or `pyskins run --skin app.json app.py` without installing.
- Undo it: `pyskins undo app.py --skin app.json` gives the exact original.
- `-s/--skin SKIN` is optional: it flavours the keywords with a theme (christmas, faces). Without it they take plain emoji. Everything is hidden either way — names like `greet` and keyword arguments like `tired=` included.

To obfuscate a whole project, give `obfuscate` a folder and a `-o` output folder. It hides every `.py` file through all subfolders with one shared key, copies other files so the tree still runs, and leaves the originals untouched:

```sh
pyskins obfuscate myapp/ -o myapp_secret/                # whole tree, one key: myapp_secret.json
pyskins add myapp_secret.json                            # install the key once
python myapp_secret/app.py                                # runs like the original
pyskins undo myapp_secret/ -o myapp_back/ --skin myapp_secret.json   # restore the whole tree
```

Be honest with the user: this is not a secret keeper. The key `.json` is plaintext — it lists the original names and strings next to their emoji — so anyone with the key reads everything; tell the user to keep keys out of version control. Inside a `.py` everything is hidden — names, keywords, strings, f-strings and comments all become emoji (a `#!` shebang on the first line is kept, since the OS reads it before Python). A string or f-string that spans several lines collapses to one emoji (`undo` restores it exactly); and obfuscating a folder copies non-`.py` files (a `.env`, a config) across unchanged. It hides code from a reader, not from anyone who has the key. Say so if the user expects real protection.

## Making a new skin

Let the tool do the set-up and the checking:

```sh
pyskins new pizza            # writes pizza.json with every keyword and everyday name, empty
pyskins check pizza.json     # reports broken rules and missing keywords, and tests the skin
pyskins add pizza.json       # saves it to the user's own skins, so "pizza" works by name
```

A skin is one JSON file. Each word gets a replacement and a few words that say why:

```json
{
  "name": "space",
  "title": "Space",
  "description": "Python among the stars.",
  "words": {
    "def": ["🚀", "launch something"],
    "return": ["🛸", "beam it back"],
    "class": ["🪐", "a whole planet"]
  }
}
```

`pyskins check` validates the mapping:

- One replacement per word, and no replacement used twice.
- A replacement is emoji only, or one plain word made of letters. No spaces, and no signs such as `#`, `&` or `$`.
- No emoji may be part of another one in the same skin.

Three things a skin may do:

- Cover only some keywords. An empty entry means the word keeps its normal look.
- Use words in place of emoji, for example `"def": ["function", "PHP says function"]`. With a word skin, `apply` refuses a file that already uses one of those words as a name, and says which one.
- Build on another skin with `"extends": "faces"`, then list only the words that change.

Bundled skin names cannot be overridden. Choose a different name for a custom skin. `pyskins add` saves the resolved mapping, including inherited words.

It may also rename ordinary names such as `print` or `self`.

Choose replacements for meaning, so a reader can guess the word: a thinking face for `if`, a gift for `def` in a Christmas skin. Show the finished mapping to the user before you use it. Keep skins friendly: a child may read them.
