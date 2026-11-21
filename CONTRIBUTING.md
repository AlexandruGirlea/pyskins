# Add your own skin

You do not need to know how the engine works. A skin is one small text file, and the tool tells you when something is wrong. Ten minutes is enough.

## The short way

```sh
pyskins new pizza            # 1. makes pizza.json with every word listed, empty
# 2. open pizza.json and fill in an emoji and a few words for each word
pyskins check pizza.json     # 3. shows what is missing and tests the skin
pyskins undo examples/robot.py -o - | pyskins apply pizza.json -   # 4. see it on real code
```

When `check` is happy, move the file to `pyskins/skins/` and open a pull request. That is all.

A finished entry looks like this:

```json
{
  "name": "pizza",
  "title": "Pizza",
  "description": "Python with extra cheese.",
  "words": {
    "class": ["🍕", "the whole pizza"],
    "def": ["🔪", "slice and prepare"],
    "return": ["🛵", "the delivery scooter"]
  }
}
```

## What makes a good skin

- **A reader can guess the word.** A thinking face for `if`. A gift for `def` at Christmas. The few words after the emoji say why, and `pyskins show` prints them.
- **It has a theme.** Food, a holiday, a sport, a film style, your city.
- **It makes someone smile.** `raise` as a raised glass. `None` as an empty stocking.
- **It is kind.** A child may read this. Nothing rude, nothing scary.

## The rules

The tool checks all of these for you. Each one exists so that a skin can always be taken off again.

1. Each word gets one replacement, and no replacement is used twice.
2. A replacement is either emoji only, or one plain word made of letters. No spaces, and no signs such as `#`, `&` or `$`.
3. No emoji may be part of another emoji in the same skin.
4. A skin made of emoji that lives in this repository covers all 35 keywords, and every word has its few words of "why". The 26 everyday names such as `print` and `len` are a bonus: cover as many as you have good ideas for.
5. A skin made of words (like the PHP example) covers what makes sense.

## Two more tricks

**Build on another skin.** Start from `faces` and change only a few words:

```json
{
  "name": "easter",
  "extends": "faces",
  "words": {
    "class": ["🧺", "the basket that holds everything"],
    "def": ["🥚", "an egg with something inside"]
  }
}
```

**Use words, not emoji.** `examples/skins/php.json` makes Python look a little like PHP: `def` becomes `function` and `None` becomes `null`. A skin like this can also make Python read like another human language.

## Before you open a pull request

```sh
python -m unittest discover -s tests
```

The tests pick up every file in `pyskins/skins/` by themselves. You do not write a test for your skin.

If you changed Python code, also run `ruff check .` (`pip install ruff`). Both checks run on every pull request.

## Skins we would love to see

Pizza. A full Easter. Halloween. Space. Pirates. The ocean. Football. Cats. Music. Wizards. Python in your own language.

Or something nobody has thought of. Surprise us.

## Add a fun program

The `examples/` folder is a small gallery: short programs, each one a `.py` file in emoji that runs. A new one is welcome too.

1. Write a short program in normal Python. Make it print something, and do not ask the user to type.
2. Put a skin on it: `pyskins apply christmas your_program.py -o examples/your_program.py`.
3. Run it: `python examples/your_program.py`.
4. Add a row to the table in the README.

## Other help

Found a file that does not come back the same after `apply` and `undo`? That is the one bug this project must never have. Please open an issue and attach the file.

Everything here is under the MIT licence, and so is what you add.
