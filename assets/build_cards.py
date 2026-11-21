import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["PYSKINS_HOME"] = os.path.join(HERE, "no-such-folder")
os.environ["PYSKINS_PATH"] = ""

import pyskins as ps  # noqa: E402

PROGRAM = u'''class Gift:
    def __init__(self, name):
        self.name = name

    def unwrap(self, nice):
        if nice:
            return "a " + self.name
        else:
            return None


for gift in [Gift("sleigh"), Gift("teddy")]:
    print(gift.unwrap(True))
'''

FONT = "SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', 'Liberation Mono', monospace"
SIZE = 24
STEP = 38
CHAR = 14.4
WIDTH = 820
PAD = 36
BAR = 58

LOOKS = {
    "python": {"back": "#1f2430", "bar": "#2b3245", "text": "#e6edf3", "title": "#9aa7bd", "snow": False},
    "christmas": {"back": "#0f3d2e", "bar": "#b3202a", "text": "#fff8e7", "title": "#ffe9b0", "snow": True},
    "faces": {"back": "#2a2140", "bar": "#3a2f5b", "text": "#f5f0ff", "title": "#cbbcf6", "snow": False},
}


def escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def card(title, code, look):
    lines = code.rstrip("\n").split("\n")
    height = BAR + PAD + STEP * len(lines) + PAD - 12
    out = [
        u'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="%s">'
        % (WIDTH, height, WIDTH, height, escape(title)),
        u'  <rect width="%d" height="%d" rx="18" fill="%s"/>' % (WIDTH, height, look["back"]),
        u'  <path d="M0 18a18 18 0 0 1 18-18h%d a18 18 0 0 1 18 18v%d H0z" fill="%s"/>'
        % (WIDTH - 36, BAR - 18, look["bar"]),
    ]
    if look["snow"]:
        for index in range(26):
            x = (index * 173 + 60) % (WIDTH - 40) + 20
            y = BAR + 14 + (index * 97) % (height - BAR - 28)
            out.append(u'  <circle cx="%d" cy="%d" r="%.1f" fill="#ffffff" opacity="0.%d"/>'
                       % (x, y, 2 + index % 3, 12 + (index * 7) % 20))
    for index, colour in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        out.append(u'  <circle cx="%d" cy="%d" r="8" fill="%s"/>' % (30 + index * 26, BAR // 2, colour))
    out.append(u'  <text x="%d" y="%d" text-anchor="middle" font-family="%s" font-size="19" fill="%s">%s</text>'
               % (WIDTH // 2, BAR // 2 + 7, FONT, look["title"], escape(title)))
    for index, line in enumerate(lines):
        text = line.lstrip(" ")
        if not text:
            continue
        x = PAD + (len(line) - len(text)) * CHAR
        y = BAR + PAD + STEP * index + 8
        out.append(u'  <text x="%.1f" y="%d" font-family="%s" font-size="%d" fill="%s">%s</text>'
                   % (x, y, FONT, SIZE, look["text"], escape(text)))
    out.append(u"</svg>")
    return u"\n".join(out) + u"\n"


def button(label, colour, text_colour="#ffffff"):
    width = int(46 + len(label) * 11.6)
    return (
        u'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d 48" width="%d" height="48" role="img" aria-label="%s">\n'
        u'  <rect width="%d" height="48" rx="24" fill="%s"/>\n'
        u'  <text x="%d" y="31" text-anchor="middle" font-family="-apple-system, \'Segoe UI\', Helvetica, Arial, sans-serif" '
        u'font-size="20" font-weight="700" fill="%s">%s</text>\n'
        u"</svg>\n" % (width, width, escape(label), width, colour, width // 2, text_colour, escape(label))
    )


def dressed(skin_name):
    return ps.add_header(ps.apply(PROGRAM, ps.load_skin(skin_name)), skin_name)


def cards():
    return {
        "card-python.svg": card(u"the same program without the skin", PROGRAM, LOOKS["python"]),
        "card-christmas.svg": card(u"gift.py", dressed("christmas"), LOOKS["christmas"]),
        "card-faces.svg": card(u"gift.py", dressed("faces"), LOOKS["faces"]),
        "button-demo.svg": button(u"Try it live", "#ff651c"),
        "button-install.svg": button(u"Install pyskins", "#137346"),
        "button-examples.svg": button(u"See fun examples", "#0f3d2e"),
        "button-ai.svg": button(u"Use it with your AI", "#3a2f5b"),
        "button-hide.svg": button(u"Hide what it does", "#1f2430"),
    }


def main():
    for name, content in sorted(cards().items()):
        with io.open(os.path.join(HERE, name), "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        print(name)


if __name__ == "__main__":
    main()
