"""ordered-json for Python: JSON document order at every depth.

Strict JSON with associative objects that preserve document key order
recursively. Repeated keys retain the first position and the last value.
Parse errors report UTF-8 byte offsets and the rejection kind that every
implementation shares.
"""

from collections.abc import Iterable, Mapping
from types import MappingProxyType

__all__ = ['MAX_DEPTH', 'ParseError', 'ParseOptions', 'Value', 'parse', 'parse_bytes', 'stringify']

MAX_DEPTH = 256

_MESSAGES = {
    'expected_value': 'Expected JSON value',
    'expected_digit': 'Expected digit',
    'expected_colon': 'Expected colon',
    'expected_delimiter': 'Expected comma or closing delimiter',
    'expected_object_key': 'Expected string',
    'invalid_escape': 'Invalid escape',
    'invalid_unicode_escape': 'Invalid Unicode escape',
    'unfinished_escape': 'Unfinished escape',
    'unterminated_string': 'Unterminated string',
    'unescaped_control_character': 'Unescaped control character',
    'unescaped_lone_surrogate': 'Unescaped unpaired surrogate',
    'invalid_utf8': 'Invalid UTF-8',
    'maximum_depth_exceeded': 'Maximum nesting depth exceeded',
    'trailing_input': 'Unexpected trailing input',
    'duplicate_object_key': 'Duplicate object key',
}

_ESCAPED_UNITS = {0x62: 8, 0x66: 12, 0x6e: 10, 0x72: 13, 0x74: 9,
                  0x22: 34, 0x5c: 92, 0x2f: 47}
_WHITESPACE = b' \t\n\r'
_DIGITS = b'0123456789'
_HEX_DIGITS = b'0123456789abcdefABCDEF'
_SIMPLE_ESCAPES = b'"/\\bfnrt'
_INTERNAL = object()


class ParseError(ValueError):
    """A rejected input document.

    `kind` names the reason with the identifier every implementation
    shares, and `offset` is the byte position of the first byte that
    makes the document invalid.
    """

    __slots__ = ('kind', 'offset', 'unit')

    def __init__(self, kind: str, offset: int):
        super().__init__(f'{_MESSAGES[kind]} at byte {offset}')
        self.kind = kind
        self.offset = offset
        self.unit = 'byte'


class ParseOptions:
    """The options of a parse: the depth limit and the duplicate-key rule."""

    __slots__ = ('max_depth', 'reject_duplicates')

    def __init__(self, max_depth: int = MAX_DEPTH, reject_duplicates: bool = False):
        if isinstance(max_depth, bool) or not isinstance(max_depth, int):
            raise TypeError('max_depth must be an integer')
        if not 0 <= max_depth <= MAX_DEPTH:
            raise ValueError(f'max_depth must be between 0 and {MAX_DEPTH}')
        if not isinstance(reject_duplicates, bool):
            raise TypeError('reject_duplicates must be a boolean')
        self.max_depth = max_depth
        self.reject_duplicates = reject_duplicates

    def __repr__(self) -> str:
        return (f'ParseOptions(max_depth={self.max_depth}, '
                f'reject_duplicates={self.reject_duplicates})')


def _expand(text: str) -> list[int]:
    """The UTF-16 code units of `text`; a character above the basic
    multilingual plane becomes its surrogate pair."""
    units: list[int] = []
    for character in text:
        point = ord(character)
        if point > 0xffff:
            point -= 0x10000
            units.append(0xd800 | (point >> 10))
            units.append(0xdc00 | (point & 0x3ff))
        else:
            units.append(point)
    return units


def _combine(units: Iterable[int]) -> str:
    """The text of UTF-16 code units; a surrogate pair becomes one
    character and an unpaired surrogate stays as its own character."""
    characters: list[str] = []
    items = list(units)
    index = 0
    while index < len(items):
        unit = items[index]
        if (0xd800 <= unit <= 0xdbff and index + 1 < len(items)
                and 0xdc00 <= items[index + 1] <= 0xdfff):
            characters.append(chr(0x10000 + ((unit - 0xd800) << 10) + items[index + 1] - 0xdc00))
            index += 2
        else:
            characters.append(chr(unit))
            index += 1
    return ''.join(characters)


def _validated_units(units: Iterable[int]) -> list[int]:
    items = list(units)
    for unit in items:
        if isinstance(unit, bool) or not isinstance(unit, int) or not 0 <= unit <= 0xffff:
            raise ValueError('Expected UTF-16 code units')
    return items


def _quote_units(units: Iterable[int]) -> bytes:
    """The string token of the units with the constructor spelling."""
    out = [b'"']
    for unit in _validated_units(units):
        if unit == 34:
            out.append(b'\\"')
        elif unit == 92:
            out.append(b'\\\\')
        elif unit == 8:
            out.append(b'\\b')
        elif unit == 12:
            out.append(b'\\f')
        elif unit == 10:
            out.append(b'\\n')
        elif unit == 13:
            out.append(b'\\r')
        elif unit == 9:
            out.append(b'\\t')
        elif 0x20 <= unit <= 0x7e:
            out.append(bytes((unit,)))
        else:
            out.append(b'\\u%04x' % unit)
    out.append(b'"')
    return b''.join(out)


def _token_units(content: bytes) -> list[int]:
    """The UTF-16 code units of a validated string token's contents; an
    escape contributes its unit without combining a pair."""
    units: list[int] = []
    offset = 0
    while True:
        slash = content.find(b'\\', offset)
        if slash < 0:
            break
        if slash > offset:
            units.extend(_expand(content[offset:slash].decode('utf-8')))
        escape = content[slash + 1]
        if escape == 0x75:
            units.append(int(content[slash + 2:slash + 6], 16))
            offset = slash + 6
        else:
            units.append(_ESCAPED_UNITS[escape])
            offset = slash + 2
    if offset < len(content):
        units.extend(_expand(content[offset:].decode('utf-8')))
    return units


def _invalid_utf8_offset(data: bytes) -> int | None:
    """The offset of the first byte of the first invalid UTF-8 sequence,
    or None when every byte is valid."""
    length = len(data)
    index = 0
    while index < length:
        start = index
        first = data[index]
        index += 1
        if first < 0x80:
            continue
        if 0xc2 <= first <= 0xdf:
            need, point = 1, first & 0x1f
        elif 0xe0 <= first <= 0xef:
            need, point = 2, first & 0x0f
        elif 0xf0 <= first <= 0xf4:
            need, point = 3, first & 0x07
        else:
            return start
        if index + need > length:
            return start
        for _ in range(need):
            following = data[index]
            index += 1
            if following & 0xc0 != 0x80:
                return start
            point = point << 6 | (following & 0x3f)
        if ((need == 1 and point < 0x80) or (need == 2 and point < 0x800)
                or (need == 3 and point < 0x10000) or point > 0x10ffff
                or 0xd800 <= point <= 0xdfff):
            return start
    return None


class Value:
    """An immutable JSON value. Objects keep the first position of each
    key with its last value; factories validate through the parser."""

    __slots__ = ('_source', '_start', '_end', '_kind', '_root', '_compact',
                 '_members', '_key_spans', '_items')

    def __init__(self, token=None):
        if token is not _INTERNAL:
            raise TypeError('Use parse(), parse_bytes() or the Value factories')

    @property
    def kind(self) -> str:
        """'object', 'array', 'string', 'number', 'boolean' or 'null'."""
        return self._kind

    @property
    def raw(self) -> str:
        """The source text of the value; the root keeps surrounding whitespace."""
        if self._root:
            return self._source.decode('utf-8')
        return self._source[self._start:self._end].decode('utf-8')

    def members(self) -> Mapping[str, 'Value']:
        """A read-only copy of the members keyed by decoded name, in the
        order of each key's first occurrence."""
        self._expect('object')
        return MappingProxyType(dict(self._members))

    def items(self) -> tuple['Value', ...]:
        """The array elements in document order."""
        self._expect('array')
        return self._items

    def string_value(self) -> str:
        """The decoded text; a surrogate pair is one character and an
        unpaired surrogate stays as its own character."""
        self._expect('string')
        return _combine(_token_units(self._content()))

    def string_units(self) -> list[int]:
        """The UTF-16 code units, including escaped unpaired surrogates."""
        self._expect('string')
        return _token_units(self._content())

    def number_literal(self) -> str:
        """The number token text without surrounding whitespace."""
        self._expect('number')
        return self._source[self._start:self._end].decode('utf-8')

    def boolean_value(self) -> bool:
        self._expect('boolean')
        return self._source[self._start:self._start + 1] == b't'

    def get(self, key: str) -> 'Value | None':
        """The member of the decoded key, or None on a miss."""
        if not isinstance(key, str):
            raise TypeError('Key must be a string')
        self._expect('object')
        return self._members.get(_combine(_expand(key)))

    def get_units(self, units: Iterable[int]) -> 'Value | None':
        """The member of the key spelled by UTF-16 code units, or None."""
        self._expect('object')
        return self._members.get(_combine(_validated_units(units)))

    def compact(self) -> str:
        """The serialization without insignificant whitespace; scalar
        tokens and the first spelling of each key are preserved."""
        return _write(self).decode('utf-8')

    @staticmethod
    def string(text: str) -> 'Value':
        if not isinstance(text, str):
            raise TypeError('Expected string')
        return parse_bytes(_quote_units(_expand(text)))

    @staticmethod
    def from_units(units: Iterable[int]) -> 'Value':
        token = b'"' + b''.join(b'\\u%04x' % unit for unit in _validated_units(units)) + b'"'
        return parse_bytes(token)

    @staticmethod
    def number(literal: str) -> 'Value':
        if not isinstance(literal, str):
            raise TypeError('Pass a number literal as a string')
        value = parse(literal)
        value._expect('number')
        if literal.strip() != literal:
            raise ValueError('Number literal cannot contain whitespace')
        return value

    @staticmethod
    def boolean(flag: bool) -> 'Value':
        if not isinstance(flag, bool):
            raise TypeError('Expected boolean')
        return parse_bytes(b'true' if flag else b'false')

    @staticmethod
    def null() -> 'Value':
        return parse_bytes(b'null')

    @staticmethod
    def array(items: Iterable['Value']) -> 'Value':
        values = list(items)
        for item in values:
            _expect_value(item)
        return parse_bytes(b'[' + b','.join(_write(value) for value in values) + b']')

    @staticmethod
    def object(entries) -> 'Value':
        pairs = entries.items() if isinstance(entries, Mapping) else entries
        parts = []
        for key, value in pairs:
            _expect_value(value)
            if isinstance(key, Value):
                key._expect('string')
                token = _write(key)
            elif isinstance(key, str):
                token = _quote_units(_expand(key))
            else:
                raise TypeError('Expected a string key')
            parts.append(token + b':' + _write(value))
        return parse_bytes(b'{' + b','.join(parts) + b'}')

    def _content(self) -> bytes:
        return self._source[self._start + 1:self._end - 1]

    def _expect(self, kind: str) -> None:
        if self._kind != kind:
            raise TypeError(f'Expected {kind}, got {self._kind}')


def _expect_value(value: object) -> None:
    if not isinstance(value, Value):
        raise TypeError('Expected a polyspec.ordered_json Value')


def _write(value: Value, out: list[bytes] | None = None) -> bytes:
    """The serialization of the value; a compact value is its source token."""
    if value._compact:
        return value._source[value._start:value._end]
    parts: list[bytes] = []
    if value._kind == 'object':
        parts.append(b'{')
        separator = b''
        for name, member in value._members.items():
            parts.append(separator)
            separator = b','
            start, end = value._key_spans[name]
            parts.append(value._source[start:end])
            parts.append(b':')
            parts.append(_write(member))
        parts.append(b'}')
    else:
        parts.append(b'[')
        separator = b''
        for item in value._items:
            parts.append(separator)
            separator = b','
            parts.append(_write(item))
        parts.append(b']')
    return b''.join(parts)


class _Parser:
    """The byte scanner; its rejections match the shared contract."""

    def __init__(self, source: bytes, options: ParseOptions):
        self.source = source
        self.length = len(source)
        self.max_depth = options.max_depth
        self.reject_duplicates = options.reject_duplicates
        self.whitespace = 0
        self.duplicates = 0

    def parse(self) -> Value:
        offset = _invalid_utf8_offset(self.source)
        if offset is not None:
            raise ParseError('invalid_utf8', offset)
        end, value = self._value(0, 0)
        end = self._skip(end)
        if end != self.length:
            raise ParseError('trailing_input', end)
        value._root = True
        return value

    def _skip(self, pos: int) -> int:
        source = self.source
        start = pos
        while pos < self.length and source[pos] in _WHITESPACE:
            pos += 1
        self.whitespace += pos - start
        return pos

    def _fail(self, kind: str, pos: int) -> None:
        raise ParseError(kind, pos)

    def _string_end(self, pos: int) -> tuple[int, bool]:
        """Validates the string token at pos; returns its end and whether
        it contains escapes."""
        source = self.source
        if source[pos:pos + 1] != b'"':
            self._fail('expected_object_key', pos)
        pos += 1
        escaped = False
        while True:
            while pos < self.length:
                byte = source[pos]
                if byte == 0x22 or byte == 0x5c or byte < 0x20:
                    break
                pos += 1
            if pos >= self.length:
                self._fail('unterminated_string', pos)
            byte = source[pos]
            pos += 1
            if byte == 0x22:
                return pos, escaped
            if byte != 0x5c:
                self._fail('unescaped_control_character', pos - 1)
            escaped = True
            if pos >= self.length:
                self._fail('unfinished_escape', pos)
            escape = source[pos]
            pos += 1
            if escape == 0x75:
                digits = 0
                while digits < 4 and pos + digits < self.length and source[pos + digits] in _HEX_DIGITS:
                    digits += 1
                if digits != 4:
                    self._fail('invalid_unicode_escape', pos + digits)
                pos += 4
            elif escape not in _SIMPLE_ESCAPES:
                self._fail('invalid_escape', pos - 1)

    def _value(self, depth: int, pos: int) -> tuple[int, Value]:
        pos = self._skip(pos)
        source = self.source
        start = pos
        value = Value(_INTERNAL)
        first = source[pos] if pos < self.length else -1
        if first == 0x7b or first == 0x5b:
            if depth >= self.max_depth:
                self._fail('maximum_depth_exceeded', pos)
            return self._container(depth, start, first == 0x7b)
        if first == 0x22:
            end, escaped = self._string_end(pos)
            value._kind = 'string'
            value._compact = True
            pos = end
        elif first == 0x2d or 0x30 <= first <= 0x39:
            pos = self._number(pos)
            value._kind = 'number'
            value._compact = True
        elif source[start:start + 4] == b'true' or source[start:start + 5] == b'false':
            pos += 4 if source[start:start + 4] == b'true' else 5
            value._kind = 'boolean'
            value._compact = True
        elif source[start:start + 4] == b'null':
            pos += 4
            value._kind = 'null'
            value._compact = True
        else:
            self._fail('expected_value', pos)
        value._source = source
        value._start = start
        value._end = pos
        value._root = False
        return pos, value

    def _number(self, pos: int) -> int:
        source = self.source
        if source[pos] == 0x2d:
            pos += 1
        if source[pos:pos + 1] == b'0':
            pos += 1
        else:
            digits = self._digits(pos)
            if digits == 0:
                self._fail('expected_digit', pos)
            pos += digits
        if source[pos:pos + 1] == b'.':
            pos += 1
            digits = self._digits(pos)
            if digits == 0:
                self._fail('expected_digit', pos)
            pos += digits
        if source[pos:pos + 1] in (b'e', b'E'):
            pos += 1
            if source[pos:pos + 1] in (b'+', b'-'):
                pos += 1
            digits = self._digits(pos)
            if digits == 0:
                self._fail('expected_digit', pos)
            pos += digits
        return pos

    def _digits(self, pos: int) -> int:
        count = 0
        while pos + count < self.length and self.source[pos + count] in _DIGITS:
            count += 1
        return count

    def _container(self, depth: int, start: int, is_object: bool) -> tuple[int, Value]:
        source = self.source
        close = b'}' if is_object else b']'
        whitespace_before = self.whitespace
        duplicates_before = self.duplicates
        members: dict[str, Value] = {} if is_object else {}
        key_spans: dict[str, tuple[int, int]] = {}
        items: list[Value] = []
        pos = self._skip(start + 1)
        if source[pos:pos + 1] != close:
            while True:
                if is_object:
                    if source[pos:pos + 1] != b'"':
                        self._fail('expected_object_key', pos)
                    key_start = pos
                    key_end, _ = self._string_end(pos)
                    name = _combine(_token_units(source[key_start + 1:key_end - 1]))
                    if self.reject_duplicates and name in members:
                        self._fail('duplicate_object_key', key_start)
                    pos = self._skip(key_end)
                    if source[pos:pos + 1] != b':':
                        self._fail('expected_colon', pos)
                    pos, member = self._value(depth + 1, pos + 1)
                    if name in members:
                        members[name] = member
                        self.duplicates += 1
                    else:
                        members[name] = member
                        key_spans[name] = (key_start, key_end)
                else:
                    pos, item = self._value(depth + 1, pos)
                    items.append(item)
                pos = self._skip(pos)
                following = source[pos:pos + 1]
                if following == close:
                    break
                if following != b',':
                    self._fail('expected_delimiter', pos)
                pos = self._skip(pos + 1)
        pos += 1
        value = Value(_INTERNAL)
        value._source = source
        value._start = start
        value._end = pos
        value._kind = 'object' if is_object else 'array'
        value._root = depth == 0
        value._compact = (self.whitespace == whitespace_before
                          and self.duplicates == duplicates_before)
        value._members = members
        value._key_spans = key_spans
        value._items = tuple(items)
        return pos, value


def _parse_bytes(data: bytes, options: ParseOptions) -> Value:
    return _Parser(data, options).parse()


def parse(source: str, options: ParseOptions | None = None) -> Value:
    """Parses JSON text; a literal unpaired surrogate of the text is
    rejected at its byte position."""
    if not isinstance(source, str):
        raise TypeError('Expected JSON text')
    settings = _settings(options)
    try:
        data = source.encode('utf-8')
    except UnicodeEncodeError as error:
        prefix = source[:error.start].encode('utf-8')
        raise ParseError('unescaped_lone_surrogate', len(prefix)) from None
    return _parse_bytes(data, settings)


def parse_bytes(data: bytes | bytearray | memoryview,
                options: ParseOptions | None = None) -> Value:
    """Parses a UTF-8 byte document."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError('Expected UTF-8 bytes')
    return _parse_bytes(bytes(data), _settings(options))


def stringify(value: Value) -> str:
    """Serializes without insignificant whitespace, preserving scalar
    tokens and the first spelling of each key."""
    _expect_value(value)
    return _write(value).decode('utf-8')


def _settings(options: ParseOptions | None) -> ParseOptions:
    if options is None:
        return ParseOptions()
    if not isinstance(options, ParseOptions):
        raise TypeError('Expected ParseOptions')
    return options
