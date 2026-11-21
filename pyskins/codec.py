import codecs
import io

from .engine import SkinError, undo
from .skins import find_skins, load_skin

_registered = []


def search(encoding):
    name = encoding.lower().replace("-", "_")
    if not name.startswith("pyskins_"):
        return None
    skin_name = name[len("pyskins_"):]
    if skin_name not in find_skins():
        return None

    utf8 = codecs.lookup("utf-8")

    def decode(data, errors="strict"):
        raw = bytes(data)
        text, length = utf8.decode(raw, errors)
        try:
            text = undo(text, load_skin(skin_name))
        except SkinError as error:
            raise UnicodeDecodeError(
                "pyskins", raw, 0, len(raw),
                "could not take off the %r skin: %s" % (skin_name, error),
            )
        return text, length

    class IncrementalDecoder(codecs.BufferedIncrementalDecoder):
        def _buffer_decode(self, data, errors, final):
            if not final:
                return u"", 0
            return decode(data, errors)

    class StreamReader(utf8.streamreader):
        def __init__(self, stream, *args, **kwargs):
            text, _ = decode(stream.read())
            utf8.streamreader.__init__(self, io.BytesIO(text.encode("utf-8")), *args, **kwargs)

    return codecs.CodecInfo(
        name=encoding,
        encode=utf8.encode,
        decode=decode,
        incrementalencoder=utf8.incrementalencoder,
        incrementaldecoder=IncrementalDecoder,
        streamreader=StreamReader,
        streamwriter=utf8.streamwriter,
    )


def register():
    if not _registered:
        codecs.register(search)
        _registered.append(True)
