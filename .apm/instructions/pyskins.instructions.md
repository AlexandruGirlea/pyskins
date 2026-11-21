---
description: How to handle Python files that wear an emoji skin, which start with a coding line that names a pyskins skin
applyTo: "**/*.py"
---

# Python files that wear a skin

If a `.py` file starts with a line such as `# coding: pyskins-christmas`, its keywords and names such as `print` are shown as emoji. It is a normal Python program wearing a skin from the `pyskins` tool. Files without that line are not affected by anything below.

- Run it like any Python file: `python robot.py`. This needs `pip install pyskins`. If that is missing, `pyskins run robot.py` works.
- Do not edit the emoji by hand, and do not write a skinned file by hand. One wrong emoji makes a file that does not run.
- To change it: `pyskins undo robot.py -o robot_plain.py`, edit and test the plain file, then `pyskins apply christmas robot_plain.py -o robot.py`.
- Keep the first line where it is. It tells Python which skin the file wears.
- Lint, format and type-check the plain file, not the skinned one. The editor underlining the emoji is expected.
