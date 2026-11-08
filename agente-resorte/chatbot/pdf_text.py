"""Extractor de texto PDF sin dependencias externas.

Implementa el subconjunto necesario para los PDF de Bibliografía:
- objetos indirectos clasicos (sin object streams ni xref streams),
- streams FlateDecode y ASCII85Decode,
- arbol de paginas,
- fuentes simples y Type0 con ToUnicode,
- operadores de texto Tj, TJ, ' y ".

No intenta reconstruir formulas, tablas ni layout complejo. El objetivo es
obtener texto con referencias de pagina para indexacion y detectar paginas que
necesitan OCR.
"""

from __future__ import annotations

import base64
import re
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator


class PDFError(RuntimeError):
    pass


_WS = b"\x00\t\n\f\r "
_DELIMS = b"()<>[]{}/%"
_OBJ_RE = re.compile(rb"(\d+)\s+(\d+)\s+obj\b")
_REF_RE = re.compile(rb"(\d+)\s+(\d+)\s+R")
_HEX_RE = re.compile(rb"<([0-9A-Fa-f\s]*)>")


@dataclass
class PDFObject:
    number: int
    generation: int
    body: bytes
    stream_raw: bytes | None = None
    _stream_cache: bytes | None = field(default=None, repr=False)

    def dict_bytes(self) -> bytes:
        pos = self.body.find(b"stream")
        return self.body[:pos] if pos >= 0 else self.body


@dataclass
class FontInfo:
    subtype: str
    base_font: str
    to_unicode: dict[int, str]
    encoding: str
    is_type0: bool


@dataclass
class PageInfo:
    number: int
    text: str
    char_count: int
    needs_ocr: bool
    error: str | None = None


@dataclass
class TextPiece:
    text: str
    x: float
    y: float
    size: float


def _decode_pdf_name(raw: bytes) -> str:
    raw = raw.strip()
    if raw.startswith(b"/"):
        raw = raw[1:]
    out = bytearray()
    i = 0
    while i < len(raw):
        if raw[i] == 0x23 and i + 2 < len(raw):
            try:
                out.append(int(raw[i + 1:i + 3], 16))
                i += 3
                continue
            except ValueError:
                pass
        out.append(raw[i])
        i += 1
    return out.decode("latin-1", "replace")


def _parse_literal_string(data: bytes, start: int) -> tuple[bytes, int]:
    assert data[start] == 0x28
    out = bytearray()
    depth = 1
    i = start + 1
    while i < len(data):
        c = data[i]
        if c == 0x5C:  # backslash
            i += 1
            if i >= len(data):
                break
            c2 = data[i]
            if c2 in b"nrtbf":
                out.append({0x6E: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12}[c2])
                i += 1
            elif c2 in b"()\\":
                out.append(c2)
                i += 1
            elif c2 == 0x0D:
                i += 1
                if i < len(data) and data[i] == 0x0A:
                    i += 1
            elif c2 == 0x0A:
                i += 1
            elif 0x30 <= c2 <= 0x37:
                oct_digits = bytearray([c2])
                i += 1
                for _ in range(2):
                    if i < len(data) and 0x30 <= data[i] <= 0x37:
                        oct_digits.append(data[i])
                        i += 1
                    else:
                        break
                out.append(int(oct_digits, 8) & 0xFF)
            else:
                out.append(c2)
                i += 1
        elif c == 0x28:
            depth += 1
            out.append(c)
            i += 1
        elif c == 0x29:
            depth -= 1
            if depth == 0:
                return bytes(out), i + 1
            out.append(c)
            i += 1
        else:
            out.append(c)
            i += 1
    return bytes(out), i


def _parse_hex_string(data: bytes, start: int) -> tuple[bytes, int]:
    end = data.find(b">", start + 1)
    if end < 0:
        end = len(data)
    raw = re.sub(rb"\s+", b"", data[start + 1:end])
    if len(raw) % 2:
        raw += b"0"
    try:
        return bytes.fromhex(raw.decode("ascii")), end + 1
    except ValueError:
        return b"", end + 1


def _tokenize_content(data: bytes) -> Iterator[tuple[str, object]]:
    """Genera tokens suficientes para interpretar operadores de texto."""
    i = 0
    n = len(data)
    while i < n:
        c = data[i]
        if c in _WS:
            i += 1
            continue
        if c == 0x25:  # %
            while i < n and data[i] not in b"\r\n":
                i += 1
            continue
        if c == 0x28:
            s, i = _parse_literal_string(data, i)
            yield ("string", s)
            continue
        if c == 0x3C:
            if i + 1 < n and data[i + 1] == 0x3C:
                yield ("dict_start", None)
                i += 2
            else:
                s, i = _parse_hex_string(data, i)
                yield ("string", s)
            continue
        if c == 0x3E and i + 1 < n and data[i + 1] == 0x3E:
            yield ("dict_end", None)
            i += 2
            continue
        if c == 0x5B:
            yield ("array_start", None)
            i += 1
            continue
        if c == 0x5D:
            yield ("array_end", None)
            i += 1
            continue
        if c == 0x2F:
            j = i + 1
            while j < n and data[j] not in _WS and data[j] not in _DELIMS:
                j += 1
            yield ("name", _decode_pdf_name(data[i:j]))
            i = j
            continue
        if c in b"+-.0123456789":
            j = i
            while j < n and data[j] in b"+-.0123456789eE":
                j += 1
            raw = data[i:j]
            try:
                value = float(raw)
                if value.is_integer() and b"." not in raw and b"e" not in raw.lower():
                    value = int(value)
            except ValueError:
                value = 0
            yield ("number", value)
            i = j
            continue
        if c == 0x7B or c == 0x7D:
            yield ("delim", chr(c))
            i += 1
            continue
        j = i
        while j < n and data[j] not in _WS and data[j] not in _DELIMS:
            j += 1
        if j == i:
            i += 1
            continue
        word = data[i:j].decode("latin-1", "replace")
        if word == "BI":
            # Saltar imagen inline hasta un EI delimitado.
            k = j
            while k < n - 1:
                if data[k:k + 2] == b"EI" and (k == 0 or data[k - 1] in _WS) and (
                    k + 2 >= n or data[k + 2] in _WS
                ):
                    k += 2
                    break
                k += 1
            i = k
            continue
        yield ("op", word)
        i = j


def _mat_mul(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, ...]:
    a0, a1, a2, a3, a4, a5 = a
    b0, b1, b2, b3, b4, b5 = b
    return (
        a0 * b0 + a1 * b2,
        a0 * b1 + a1 * b3,
        a2 * b0 + a3 * b2,
        a2 * b1 + a3 * b3,
        a4 * b0 + a5 * b2 + b4,
        a4 * b1 + a5 * b3 + b5,
    )


def _apply(m: tuple[float, ...], x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = m
    return a * x + c * y + e, b * x + d * y + f


def _decode_utf16_hex(hex_text: str) -> str:
    try:
        raw = bytes.fromhex(re.sub(r"\s+", "", hex_text))
    except ValueError:
        return ""
    if len(raw) % 2:
        raw += b"\x00"
    try:
        return raw.decode("utf-16-be", "replace")
    except Exception:
        return ""


def _parse_tounicode(data: bytes) -> dict[int, str]:
    mapping: dict[int, str] = {}
    text = data
    for block in re.findall(rb"beginbfchar(.*?)endbfchar", text, re.S):
        for m in re.finditer(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>", block):
            try:
                code = int(m.group(1), 16)
            except ValueError:
                continue
            mapping[code] = _decode_utf16_hex(m.group(2).decode("ascii", "ignore"))
    for block in re.findall(rb"beginbfrange(.*?)endbfrange", text, re.S):
        # Formato <inicio> <fin> <destino>
        for m in re.finditer(
            rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block
        ):
            try:
                start, end = int(m.group(1), 16), int(m.group(2), 16)
                base = int(m.group(3), 16)
            except ValueError:
                continue
            if end < start or end - start > 0xFFFF:
                continue
            width = max(2, len(m.group(3)) // 2)
            for offset, code in enumerate(range(start, end + 1)):
                value = base + offset
                raw = value.to_bytes(width, "big", signed=False)
                mapping[code] = raw.decode("utf-16-be", "replace")
        # Formato <inicio> <fin> [<destino1> <destino2> ...]
        for m in re.finditer(
            rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]", block, re.S
        ):
            try:
                start, end = int(m.group(1), 16), int(m.group(2), 16)
            except ValueError:
                continue
            dests = re.findall(rb"<([0-9A-Fa-f]*)>", m.group(3))
            for offset, dest in enumerate(dests):
                code = start + offset
                if code > end:
                    break
                mapping[code] = _decode_utf16_hex(dest.decode("ascii", "ignore"))
    return mapping


class PDFDocument:
    def __init__(self, data: bytes):
        self.data = data
        self.objects: dict[int, PDFObject] = {}
        self._parse_objects()
        self.root = self._find_root()
        self.page_refs = self._collect_page_refs()

    def _parse_objects(self) -> None:
        for match in _OBJ_RE.finditer(self.data):
            number = int(match.group(1))
            generation = int(match.group(2))
            start = match.end()
            next_endobj = self.data.find(b"endobj", start)
            if next_endobj < 0:
                next_endobj = len(self.data)
            stream_pos = self.data.find(b"stream", start, next_endobj)
            stream_raw = None
            if stream_pos >= 0:
                # El cuerpo incluye el diccionario y el stream; se recorta en endobj
                # posterior a endstream.
                endstream = self.data.find(b"endstream", stream_pos)
                if endstream < 0:
                    endstream = next_endobj
                endobj = self.data.find(b"endobj", endstream)
                if endobj < 0:
                    endobj = len(self.data)
                body = self.data[start:endobj]
                raw_start = stream_pos + len(b"stream")
                if self.data[raw_start:raw_start + 2] == b"\r\n":
                    raw_start += 2
                elif self.data[raw_start:raw_start + 1] in (b"\r", b"\n"):
                    raw_start += 1
                stream_raw = self.data[raw_start:endstream]
            else:
                body = self.data[start:next_endobj]
            self.objects[number] = PDFObject(
                number=number,
                generation=generation,
                body=body,
                stream_raw=stream_raw,
            )

    def _find_root(self) -> int:
        for number, obj in self.objects.items():
            if re.search(rb"/Type\s*/Catalog\b", obj.body):
                return number
        # Fallback: buscar /Root en el trailer.
        for m in re.finditer(rb"/Root\s+(\d+)\s+(\d+)\s+R", self.data):
            return int(m.group(1))
        raise PDFError("No se encontro /Root ni /Catalog")

    def obj(self, number: int) -> PDFObject:
        if number not in self.objects:
            raise PDFError(f"Objeto {number} no encontrado")
        return self.objects[number]

    def ref(self, body: bytes, key: str) -> int | None:
        m = re.search(rb"/" + key.encode("ascii") + rb"\s+(\d+)\s+(\d+)\s+R", body)
        return int(m.group(1)) if m else None

    def refs(self, body: bytes, key: str) -> list[int]:
        m = re.search(rb"/" + key.encode("ascii") + rb"\s*\[(.*?)\]", body, re.S)
        if m:
            return [int(x.group(1)) for x in _REF_RE.finditer(m.group(1))]
        one = self.ref(body, key)
        return [one] if one is not None else []

    def stream(self, number: int) -> bytes:
        obj = self.obj(number)
        if obj._stream_cache is not None:
            return obj._stream_cache
        raw = obj.stream_raw or b""
        d = obj.dict_bytes()
        filters = []
        m = re.search(rb"/Filter\s*(\[[^\]]*\]|/\w+)", d, re.S)
        if m:
            filters = [x.decode("latin-1").lstrip("/") for x in re.findall(rb"/(\w+)", m.group(1))]
        out = raw
        for filt in filters:
            if filt in ("FlateDecode", "Fl"):
                try:
                    out = zlib.decompress(out)
                except zlib.error:
                    try:
                        out = zlib.decompressobj().decompress(out)
                    except zlib.error as exc:
                        raise PDFError(f"FlateDecode fallo en objeto {number}: {exc}") from exc
            elif filt in ("ASCII85Decode", "A85"):
                try:
                    out = base64.a85decode(out, adobe=True)
                except Exception as exc:
                    raise PDFError(f"ASCII85Decode fallo en objeto {number}: {exc}") from exc
            elif filt in ("ASCIIHexDecode", "AHx"):
                raw_hex = re.sub(rb"\s+", b"", out).rstrip(b">")
                if len(raw_hex) % 2:
                    raw_hex += b"0"
                out = bytes.fromhex(raw_hex.decode("ascii"))
            else:
                raise PDFError(f"Filtro PDF no soportado: {filt}")
        obj._stream_cache = out
        return out

    def _collect_page_refs(self) -> list[int]:
        root_body = self.obj(self.root).body
        pages_root = self.ref(root_body, "Pages")
        if pages_root is None:
            raise PDFError("El catalogo no tiene /Pages")
        pages: list[int] = []
        seen: set[int] = set()

        def walk(number: int) -> None:
            if number in seen:
                return
            seen.add(number)
            body = self.obj(number).body
            if re.search(rb"/Type\s*/Page\b", body):
                pages.append(number)
                return
            for kid in self.refs(body, "Kids"):
                walk(kid)

        walk(pages_root)
        if not pages:
            # Fallback para PDFs con arbol atipico.
            pages = [
                n for n, o in sorted(self.objects.items())
                if re.search(rb"/Type\s*/Page\b", o.body)
            ]
        return pages

    def _dict_value(self, body: bytes, key: str) -> bytes | None:
        """Devuelve el contenido de /Key <<...>> o el cuerpo del objeto referido."""
        m = re.search(rb"/" + key.encode("ascii") + rb"\s*", body)
        if not m:
            return None
        pos = m.end()
        ref = re.match(rb"(\d+)\s+(\d+)\s+R", body[pos:])
        if ref:
            return self.obj(int(ref.group(1))).body
        if body[pos:pos + 2] == b"<<":
            depth = 0
            i = pos
            while i < len(body) - 1:
                pair = body[i:i + 2]
                if pair == b"<<":
                    depth += 1
                    i += 2
                    continue
                if pair == b">>":
                    depth -= 1
                    if depth == 0:
                        return body[pos + 2:i]
                    i += 2
                    continue
                i += 1
        return None

    def _page_resources_body(self, page_number: int) -> bytes | None:
        body = self.obj(page_number).body
        resources = self._dict_value(body, "Resources")
        if resources is not None:
            return resources
        # Recorrer padres hasta encontrar Resources heredados.
        parent = self.ref(body, "Parent")
        seen: set[int] = set()
        while parent is not None and parent not in seen:
            seen.add(parent)
            pbody = self.obj(parent).body
            resources = self._dict_value(pbody, "Resources")
            if resources is not None:
                return resources
            parent = self.ref(pbody, "Parent")
        return None

    def _font_map(self, page_number: int) -> dict[str, FontInfo]:
        rbody = self._page_resources_body(page_number)
        if rbody is None:
            return {}
        fbody = self._dict_value(rbody, "Font")
        if fbody is None:
            return {}
        fonts: dict[str, FontInfo] = {}
        for m in re.finditer(rb"/([^\s/<>\[\]()]+)\s+(\d+)\s+(\d+)\s+R", fbody):
            name = _decode_pdf_name(b"/" + m.group(1))
            ref = int(m.group(2))
            try:
                fonts[name] = self._parse_font(ref)
            except Exception:
                fonts[name] = FontInfo("", "", {}, "cp1252", False)
        return fonts

    def _parse_font(self, number: int) -> FontInfo:
        body = self.obj(number).body
        subtype = ""
        m = re.search(rb"/Subtype\s*/([A-Za-z0-9]+)", body)
        if m:
            subtype = m.group(1).decode("latin-1")
        base_font = ""
        m = re.search(rb"/BaseFont\s*/([^\s/<>\[\]()]+)", body)
        if m:
            base_font = _decode_pdf_name(m.group(1))
        to_unicode: dict[int, str] = {}
        tu = self.ref(body, "ToUnicode")
        if tu is not None:
            try:
                to_unicode = _parse_tounicode(self.stream(tu))
            except Exception:
                to_unicode = {}
        encoding = "cp1252"
        enc = re.search(rb"/Encoding\s*/([A-Za-z0-9]+)", body)
        if enc:
            name = enc.group(1).decode("latin-1")
            if "MacRoman" in name:
                encoding = "mac_roman"
            elif "WinAnsi" in name:
                encoding = "cp1252"
        else:
            enc_ref = self.ref(body, "Encoding")
            if enc_ref is not None:
                ebody = self.obj(enc_ref).body
                if b"MacRomanEncoding" in ebody:
                    encoding = "mac_roman"
        return FontInfo(
            subtype=subtype,
            base_font=base_font,
            to_unicode=to_unicode,
            encoding=encoding,
            is_type0=subtype == "Type0",
        )

    @staticmethod
    def _decode_with_font(font: FontInfo, raw: bytes) -> str:
        if font.to_unicode:
            out = []
            if font.is_type0:
                for i in range(0, len(raw) - 1, 2):
                    code = (raw[i] << 8) | raw[i + 1]
                    out.append(font.to_unicode.get(code, "\ufffd"))
            else:
                for b in raw:
                    out.append(font.to_unicode.get(b, chr(b)))
            return "".join(out)
        if font.is_type0:
            # Sin ToUnicode no se puede recuperar el Unicode real de Identity-H.
            return raw.decode("utf-16-be", "replace")
        try:
            return raw.decode(font.encoding, "replace")
        except LookupError:
            return raw.decode("latin-1", "replace")

    def _page_text(self, page_number: int) -> str:
        page_body = self.obj(page_number).body
        contents = self.refs(page_body, "Contents")
        if not contents:
            return ""
        chunks = []
        for ref in contents:
            try:
                chunks.append(self.stream(ref))
            except Exception:
                continue
        data = b"\n".join(chunks)
        fonts = self._font_map(page_number)
        pieces: list[TextPiece] = []

        ctm: tuple[float, ...] = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        ctm_stack: list[tuple[float, ...]] = []
        tm: tuple[float, ...] = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        tlm: tuple[float, ...] = tm
        font = FontInfo("", "", {}, "cp1252", False)
        font_size = 10.0
        leading = 0.0
        hscale = 1.0
        char_spacing = 0.0
        word_spacing = 0.0
        rise = 0.0

        def show_text(text: str) -> None:
            nonlocal tm
            if not text:
                return
            m = _mat_mul(ctm, tm)
            x, y = _apply(m, 0.0, rise)
            pieces.append(TextPiece(text=text, x=x, y=y, size=font_size))
            # Avance aproximado para separar textos consecutivos.
            width = len(text) * font_size * 0.5 * hscale
            tm = _mat_mul((1.0, 0.0, 0.0, 1.0, width, 0.0), tm)

        def show(raw: bytes) -> None:
            show_text(self._decode_with_font(font, raw))

        stack: list[object] = []
        for kind, value in _tokenize_content(data):
            if kind == "array_start":
                stack.append([])
                continue
            if kind == "array_end":
                arr = stack.pop() if stack and isinstance(stack[-1], list) else []
                if stack and isinstance(stack[-1], list):
                    stack[-1].append(arr)
                continue
            if stack and isinstance(stack[-1], list):
                stack[-1].append(value)
                continue
            if kind == "op":
                op = str(value)
                if op == "q":
                    ctm_stack.append(ctm)
                elif op == "Q":
                    if ctm_stack:
                        ctm = ctm_stack.pop()
                elif op == "cm" and len(stack) >= 6:
                    vals = [float(x) for x in stack[-6:] if isinstance(x, (int, float))]
                    if len(vals) == 6:
                        ctm = _mat_mul(tuple(vals), ctm)
                elif op == "BT":
                    tm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
                    tlm = tm
                elif op == "Tf" and len(stack) >= 2:
                    name = stack[-2]
                    size = stack[-1]
                    if isinstance(name, str):
                        font = fonts.get(name, FontInfo("", "", {}, "cp1252", False))
                    if isinstance(size, (int, float)):
                        font_size = float(size)
                elif op == "Tm" and len(stack) >= 6:
                    vals = [float(x) for x in stack[-6:] if isinstance(x, (int, float))]
                    if len(vals) == 6:
                        tm = tuple(vals)
                        tlm = tm
                elif op in ("Td", "TD") and len(stack) >= 2:
                    tx = float(stack[-2]) if isinstance(stack[-2], (int, float)) else 0.0
                    ty = float(stack[-1]) if isinstance(stack[-1], (int, float)) else 0.0
                    if op == "TD":
                        leading = -ty
                    tlm = _mat_mul((1.0, 0.0, 0.0, 1.0, tx, ty), tlm)
                    tm = tlm
                elif op == "T*":
                    tlm = _mat_mul((1.0, 0.0, 0.0, 1.0, 0.0, -leading), tlm)
                    tm = tlm
                elif op == "TL" and stack and isinstance(stack[-1], (int, float)):
                    leading = float(stack[-1])
                elif op == "Tz" and stack and isinstance(stack[-1], (int, float)):
                    hscale = float(stack[-1]) / 100.0
                elif op == "Tc" and stack and isinstance(stack[-1], (int, float)):
                    char_spacing = float(stack[-1])
                elif op == "Tw" and stack and isinstance(stack[-1], (int, float)):
                    word_spacing = float(stack[-1])
                elif op == "Ts" and stack and isinstance(stack[-1], (int, float)):
                    rise = float(stack[-1])
                elif op == "Tj" and stack and isinstance(stack[-1], bytes):
                    show(stack[-1])
                elif op == "TJ" and stack and isinstance(stack[-1], list):
                    parts = []
                    for item in stack[-1]:
                        if isinstance(item, bytes):
                            parts.append(self._decode_with_font(font, item))
                        elif isinstance(item, (int, float)) and item < -150:
                            parts.append(" ")
                    if parts:
                        show_text("".join(parts))
                elif op == "'" and stack and isinstance(stack[-1], bytes):
                    tlm = _mat_mul((1.0, 0.0, 0.0, 1.0, 0.0, -leading), tlm)
                    tm = tlm
                    show(stack[-1])
                elif op == '"' and len(stack) >= 3 and isinstance(stack[-1], bytes):
                    if isinstance(stack[-3], (int, float)):
                        word_spacing = float(stack[-3])
                    if isinstance(stack[-2], (int, float)):
                        char_spacing = float(stack[-2])
                    tlm = _mat_mul((1.0, 0.0, 0.0, 1.0, 0.0, -leading), tlm)
                    tm = tlm
                    show(stack[-1])
                stack = []
            else:
                stack.append(value)

        # Reconstruir lineas en orden de contenido. Se ordena por x dentro de
        # cada linea; el orden de contenido suele respetar columnas y secciones.
        lines: list[list[TextPiece]] = []
        current: list[TextPiece] = []
        last_y: float | None = None
        for piece in pieces:
            if last_y is None or abs(piece.y - last_y) <= max(2.0, piece.size * 0.35):
                current.append(piece)
            else:
                if current:
                    lines.append(current)
                current = [piece]
            last_y = piece.y
        if current:
            lines.append(current)

        rendered: list[str] = []
        for line in lines:
            line = sorted(line, key=lambda p: p.x)
            out = ""
            prev_end: float | None = None
            prev_size = 10.0
            for p in line:
                if prev_end is not None:
                    gap = p.x - prev_end
                    if gap > max(2.0, prev_size * 0.8) and not out.endswith(" ") and not p.text.startswith(" "):
                        out += " "
                out += p.text
                prev_end = p.x + len(p.text) * p.size * 0.5
                prev_size = p.size
            rendered.append(out)
        text = "\n".join(rendered)
        text = text.replace("\x00", "")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def pages(self) -> list[PageInfo]:
        out: list[PageInfo] = []
        for index, ref in enumerate(self.page_refs, start=1):
            error = None
            try:
                text = self._page_text(ref)
            except Exception as exc:
                text = ""
                error = f"{type(exc).__name__}: {exc}"
            char_count = len(text.strip())
            out.append(
                PageInfo(
                    number=index,
                    text=text,
                    char_count=char_count,
                    needs_ocr=char_count < 80,
                    error=error,
                )
            )
        return out


def extract_pdf_bytes(data: bytes) -> list[PageInfo]:
    return PDFDocument(data).pages()


def extract_pdf(path: str | Path) -> list[PageInfo]:
    return extract_pdf_bytes(Path(path).read_bytes())
