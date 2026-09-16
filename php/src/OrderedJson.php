<?php
declare(strict_types=1);

namespace OrderedJson;

const MAX_DEPTH = 256;

final class ParseError extends \InvalidArgumentException
{
    public function __construct(string $message, public readonly int $offset)
    {
        parent::__construct("$message at byte $offset");
    }
}

/** @internal Convert UTF-16 units to UTF-8, optionally retaining lone surrogates as WTF-8. */
function unitsToUtf8(array $units, bool $allowUnpaired = true): string
{
    $out = '';
    for ($i = 0, $n = count($units); $i < $n; $i++) {
        $point = $units[$i];
        if (!is_int($point) || $point < 0 || $point > 65535)
            throw new \InvalidArgumentException('Expected UTF-16 code units');
        if ($point >= 0xd800 && $point <= 0xdbff) {
            if ($i + 1 < $n && is_int($units[$i + 1]) && $units[$i + 1] >= 0xdc00 && $units[$i + 1] <= 0xdfff) {
                $point = 0x10000 + (($point - 0xd800) << 10) + $units[++$i] - 0xdc00;
            } elseif (!$allowUnpaired) {
                throw new \UnexpectedValueException('Unpaired surrogate; use stringUnits()');
            }
        } elseif ($point >= 0xdc00 && $point <= 0xdfff && !$allowUnpaired) {
            throw new \UnexpectedValueException('Unpaired surrogate; use stringUnits()');
        }
        if ($point < 0x80) $out .= chr($point);
        elseif ($point < 0x800) $out .= chr(0xc0 | ($point >> 6)) . chr(0x80 | ($point & 63));
        elseif ($point < 0x10000) $out .= chr(0xe0 | ($point >> 12)) . chr(0x80 | (($point >> 6) & 63)) . chr(0x80 | ($point & 63));
        else $out .= chr(0xf0 | ($point >> 18)) . chr(0x80 | (($point >> 12) & 63)) . chr(0x80 | (($point >> 6) & 63)) . chr(0x80 | ($point & 63));
    }
    return $out;
}

/** @internal Object-key identity uses WTF-8 for lone UTF-16 surrogates. */
function keyText(array $units): string
{
    return unitsToUtf8($units, true);
}

/** @internal Decode UTF-8 or WTF-8 into UTF-16 units. */
function utf8Units(string $text, bool $allowWtf8 = false): array
{
    $units = [];
    for ($i = 0, $n = strlen($text); $i < $n;) {
        $first = ord($text[$i++]);
        if ($first < 0x80) $point = $first;
        elseif ($first >= 0xc2 && $first <= 0xdf) {
            if ($i >= $n) throw new \InvalidArgumentException('Invalid UTF-8');
            $next = ord($text[$i++]);
            if (($next & 0xc0) !== 0x80) throw new \InvalidArgumentException('Invalid UTF-8');
            $point = (($first & 0x1f) << 6) | ($next & 63);
        } elseif ($first >= 0xe0 && $first <= 0xef) {
            if ($i + 1 >= $n) throw new \InvalidArgumentException('Invalid UTF-8');
            $b1 = ord($text[$i++]); $b2 = ord($text[$i++]);
            if (($b1 & 0xc0) !== 0x80 || ($b2 & 0xc0) !== 0x80)
                throw new \InvalidArgumentException('Invalid UTF-8');
            $point = (($first & 15) << 12) | (($b1 & 63) << 6) | ($b2 & 63);
            if ($point < 0x800 || ($point >= 0xd800 && $point <= 0xdfff && !$allowWtf8))
                throw new \InvalidArgumentException('Invalid UTF-8');
        } elseif ($first >= 0xf0 && $first <= 0xf4) {
            if ($i + 2 >= $n) throw new \InvalidArgumentException('Invalid UTF-8');
            $b1 = ord($text[$i++]); $b2 = ord($text[$i++]); $b3 = ord($text[$i++]);
            if (($b1 & 0xc0) !== 0x80 || ($b2 & 0xc0) !== 0x80 || ($b3 & 0xc0) !== 0x80)
                throw new \InvalidArgumentException('Invalid UTF-8');
            $point = (($first & 7) << 18) | (($b1 & 63) << 12) | (($b2 & 63) << 6) | ($b3 & 63);
            if ($point < 0x10000 || $point > 0x10ffff)
                throw new \InvalidArgumentException('Invalid UTF-8');
        } else throw new \InvalidArgumentException('Invalid UTF-8');
        if ($point <= 0xffff) $units[] = $point;
        else { $point -= 0x10000; $units[] = 0xd800 | ($point >> 10); $units[] = 0xdc00 | ($point & 1023); }
    }
    return $units;
}

/** @internal First invalid UTF-8 byte offset, or null for valid text. */
function invalidUtf8Offset(string $text): ?int
{
    $length = strlen($text);
    for ($i = 0; $i < $length;) {
        $start = $i;
        $first = ord($text[$i++]);
        if ($first < 0x80) continue;
        $need = $first >= 0xc2 && $first <= 0xdf ? 1
            : ($first >= 0xe0 && $first <= 0xef ? 2
            : ($first >= 0xf0 && $first <= 0xf4 ? 3 : -1));
        if ($need < 0 || $i + $need > $length) return $start;
        $point = $first & ((1 << (6 - $need)) - 1);
        for ($j = 0; $j < $need; $j++) {
            $next = ord($text[$i++]);
            if (($next & 0xc0) !== 0x80) return $start;
            $point = ($point << 6) | ($next & 0x3f);
        }
        if (($need === 1 && $point < 0x80) || ($need === 2 && $point < 0x800)
            || ($need === 3 && $point < 0x10000) || $point > 0x10ffff
            || ($point >= 0xd800 && $point <= 0xdfff)) return $start;
    }
    return null;
}

/** @internal Decode the contents of a validated string token into UTF-16 units. */
function tokenUnits(string $content): array
{
    $units = [];
    $offset = 0;
    while (($slash = strpos($content, '\\', $offset)) !== false) {
        if ($slash > $offset)
            foreach (textUnits(substr($content, $offset, $slash - $offset)) as $unit) $units[] = $unit;
        $escape = $content[$slash + 1];
        if ($escape === 'u') {
            $units[] = (int)hexdec(substr($content, $slash + 2, 4));
            $offset = $slash + 6;
        } else {
            $units[] = match ($escape) { 'b' => 8, 'f' => 12, 'n' => 10, 'r' => 13, 't' => 9, default => ord($escape) };
            $offset = $slash + 2;
        }
    }
    if ($offset < strlen($content))
        foreach (textUnits(substr($content, $offset)) as $unit) $units[] = $unit;
    return $units;
}

/** @internal UTF-16 units of valid UTF-8 text. */
function textUnits(string $text): array
{
    static $ascii = null;
    $ascii ??= implode('', array_map('chr', range(0, 127)));
    return strspn($text, $ascii) === strlen($text) ? array_values(unpack('C*', $text)) : utf8Units($text);
}

/**
 * @internal UTF-8 text of validated string token contents. A lone surrogate becomes WTF-8
 * when $allowUnpaired is true; otherwise it is rejected like unitsToUtf8().
 */
function tokenText(string $content, bool $allowUnpaired): string
{
    $slash = strpos($content, '\\');
    if ($slash === false) return $content;
    $out = '';
    $offset = 0;
    do {
        $out .= substr($content, $offset, $slash - $offset);
        $escape = $content[$slash + 1];
        if ($escape !== 'u') {
            $out .= match ($escape) { 'b' => "\x08", 'f' => "\f", 'n' => "\n", 'r' => "\r", 't' => "\t", default => $escape };
            $offset = $slash + 2;
        } else {
            $point = hexdec(substr($content, $slash + 2, 4));
            $offset = $slash + 6;
            if ($point >= 0xd800 && $point <= 0xdbff && substr($content, $offset, 2) === '\\u') {
                $low = hexdec(substr($content, $offset + 2, 4));
                if ($low >= 0xdc00 && $low <= 0xdfff) {
                    $point = 0x10000 + (($point - 0xd800) << 10) + $low - 0xdc00;
                    $offset += 6;
                }
            }
            if ($point >= 0xd800 && $point <= 0xdfff && !$allowUnpaired)
                throw new \UnexpectedValueException('Unpaired surrogate; use stringUnits()');
            if ($point < 0x80) $out .= chr($point);
            elseif ($point < 0x800) $out .= chr(0xc0 | $point >> 6) . chr(0x80 | $point & 63);
            elseif ($point < 0x10000) $out .= chr(0xe0 | $point >> 12) . chr(0x80 | $point >> 6 & 63) . chr(0x80 | $point & 63);
            else $out .= chr(0xf0 | $point >> 18) . chr(0x80 | $point >> 12 & 63) . chr(0x80 | $point >> 6 & 63) . chr(0x80 | $point & 63);
        }
        $slash = strpos($content, '\\', $offset);
    } while ($slash !== false);
    return $out . substr($content, $offset);
}

/** @internal Encode UTF-16 units with the shared constructor spelling. */
function quoteUnits(array $units): string
{
    $out = '"';
    foreach ($units as $unit) {
        if (!is_int($unit) || $unit < 0 || $unit > 65535)
            throw new \InvalidArgumentException('Expected UTF-16 code units');
        $out .= match ($unit) {
            34 => '\"', 92 => '\\\\', 8 => '\b', 12 => '\f', 10 => '\n',
            13 => '\r', 9 => '\t',
            default => ($unit >= 0x20 && $unit <= 0x7e) ? chr($unit) : sprintf('\u%04x', $unit),
        };
    }
    return $out . '"';
}

/** @internal Encode associative array keys, including stored WTF-8 surrogate keys. */
function quoteKey(string $key): string
{
    return quoteUnits(utf8Units($key, true));
}

/**
 * @internal Descriptor tape layout shared with the C extension. Each value has three
 * integers in document order: meta, start and end. meta = kind | flags | link << LINK.
 * A container links past its subtree; an object key links to the value of its member.
 */
final class Tape
{
    public const OBJECT = 1, ARRAY = 2, STRING = 3, NUMBER = 4, BOOLEAN = 5, NULL = 6, KIND = 7;
    public const KINDS = [self::OBJECT => 'object', self::ARRAY => 'array', self::STRING => 'string',
        self::NUMBER => 'number', self::BOOLEAN => 'boolean', self::NULL => 'null'];
    /** The value serializes to exactly its source token. */
    public const COMPACT = 8;
    /** The string token contains escape sequences. */
    public const ESCAPED = 16;
    /** A repeated object key; the first key of that name links to the final value. */
    public const SKIP = 32;
    public const LINK = 8;
}

/** JSON value. Objects use insertion-ordered PHP associative arrays. Child values hydrate lazily. */
final class Value implements \JsonSerializable, \Stringable
{
    private static ?bool $native = null;
    private string $source;
    /** @var list<int> Descriptor tape; this value's record starts at $index. */
    private array $tape;
    private int $index;
    /** Members and key tokens of an object, items of an array, or UTF-16 units of a string once read. */
    private mixed $cache = null;

    private function __construct() {}

    public static function parse(string $source, int $maxDepth = MAX_DEPTH): self
    {
        if ($maxDepth < 0 || $maxDepth > MAX_DEPTH)
            throw new \InvalidArgumentException('maxDepth must be between 0 and 256');
        if (self::$native ??= \extension_loaded('ordered_json')) {
            try { $tape = \ordered_json_scan($source, $maxDepth); }
            catch (\OrderedJsonNativeParseError $e) {
                throw new ParseError($e->getMessage(), $e->offset);
            }
        } else {
            $tape = (new Parser($source, $maxDepth))->parse();
        }
        $value = new self();
        $value->source = $source;
        $value->tape = $tape;
        $value->index = 0;
        return $value;
    }

    /** @return array<string|int, Value> Members keyed by decoded name, in first insertion order. */
    private function hydrateMembers(): array
    {
        if (self::$native ??= \extension_loaded('ordered_json'))
            return \ordered_json_hydrate($this->source, $this->tape, $this->index);
        $members = [];
        $source = $this->source;
        $tape = $this->tape;
        for ($i = $this->index + 3, $end = $tape[$this->index] >> Tape::LINK; $i < $end;) {
            $meta = $tape[$i];
            $valueMeta = $tape[$i + 3];
            $next = ($valueMeta & Tape::KIND) <= Tape::ARRAY ? $valueMeta >> Tape::LINK : $i + 6;
            if (!($meta & Tape::SKIP)) {
                $start = $tape[$i + 1] + 1;
                $name = substr($source, $start, $tape[$i + 2] - 1 - $start);
                if ($meta & Tape::ESCAPED) $name = tokenText($name, true);
                $member = new self();
                $member->source = $source;
                $member->tape = $tape;
                $member->index = $meta >> Tape::LINK;
                $members[$name] = $member;
            }
            $i = $next;
        }
        return $members;
    }

    /** @return list<Value> */
    private function hydrateItems(): array
    {
        if (self::$native ??= \extension_loaded('ordered_json'))
            return \ordered_json_hydrate($this->source, $this->tape, $this->index);
        $items = [];
        $source = $this->source;
        $tape = $this->tape;
        for ($i = $this->index + 3, $end = $tape[$this->index] >> Tape::LINK; $i < $end;) {
            $item = new self();
            $item->source = $source;
            $item->tape = $tape;
            $item->index = $i;
            $items[] = $item;
            $meta = $tape[$i];
            $i = ($meta & Tape::KIND) <= Tape::ARRAY ? $meta >> Tape::LINK : $i + 3;
        }
        return $items;
    }

    public function kind(): string { return Tape::KINDS[$this->tape[$this->index] & Tape::KIND]; }
    public function raw(): string { return $this->index === 0 ? $this->source : $this->token(); }
    private function token(): string
    {
        $start = $this->tape[$this->index + 1];
        return substr($this->source, $start, $this->tape[$this->index + 2] - $start);
    }
    private function mismatch(string $kind): never
    {
        throw new \LogicException("Expected $kind, got {$this->kind()}");
    }
    /** @return array<string|int, Value> Key order is the first insertion order. */
    public function members(): array
    {
        if (($this->tape[$this->index] & Tape::KIND) !== Tape::OBJECT) $this->mismatch('object');
        return $this->cache ??= $this->hydrateMembers();
    }
    /** @return list<Value> */
    public function items(): array
    {
        if (($this->tape[$this->index] & Tape::KIND) !== Tape::ARRAY) $this->mismatch('array');
        return $this->cache ??= $this->hydrateItems();
    }
    /** @return list<int> UTF-16 units, including escaped unpaired surrogates. */
    public function stringUnits(): array
    {
        $tape = $this->tape;
        $index = $this->index;
        if (($tape[$index] & Tape::KIND) !== Tape::STRING) $this->mismatch('string');
        $start = $tape[$index + 1] + 1;
        return $this->cache ??= tokenUnits(substr($this->source, $start, $tape[$index + 2] - 1 - $start));
    }
    public function stringValue(): string
    {
        $tape = $this->tape;
        $index = $this->index;
        $meta = $tape[$index];
        if (($meta & Tape::KIND) !== Tape::STRING) $this->mismatch('string');
        $start = $tape[$index + 1] + 1;
        $content = substr($this->source, $start, $tape[$index + 2] - 1 - $start);
        return $meta & Tape::ESCAPED ? tokenText($content, false) : $content;
    }
    public function numberLiteral(): string
    {
        $tape = $this->tape;
        $index = $this->index;
        if (($tape[$index] & Tape::KIND) !== Tape::NUMBER) $this->mismatch('number');
        $start = $tape[$index + 1];
        return substr($this->source, $start, $tape[$index + 2] - $start);
    }
    public function booleanValue(): bool
    {
        $tape = $this->tape;
        $index = $this->index;
        if (($tape[$index] & Tape::KIND) !== Tape::BOOLEAN) $this->mismatch('boolean');
        return $this->source[$tape[$index + 1]] === 't';
    }
    public function get(string $key): ?self
    {
        if (($this->tape[$this->index] & Tape::KIND) !== Tape::OBJECT) $this->mismatch('object');
        return ($this->cache ??= $this->hydrateMembers())[$key] ?? null;
    }
    public function getUnits(array $units): ?self
    {
        return $this->get(keyText($units));
    }
    public static function string(string $text): self
    {
        return self::parse(quoteUnits(utf8Units($text)));
    }
    public static function fromUnits(array $units): self
    {
        $raw = '"';
        foreach ($units as $unit) {
            if (!is_int($unit) || $unit < 0 || $unit > 65535)
                throw new \InvalidArgumentException('Expected UTF-16 code units');
            $raw .= sprintf('\\u%04x', $unit);
        }
        return self::parse($raw . '"');
    }
    public static function number(string $literal): self
    {
        $v = self::parse($literal);
        if ($v->kind() !== 'number' || trim($literal) !== $literal)
            throw new \InvalidArgumentException('Expected number literal without whitespace');
        return $v;
    }
    public static function boolean(bool $value): self { return self::parse($value ? 'true' : 'false'); }
    public static function null(): self { return self::parse('null'); }
    public static function array(array $items): self
    {
        if (!array_is_list($items)) throw new \InvalidArgumentException('Expected a list of values');
        return self::parse('[' . implode(',', array_map(fn(self $v) => $v->compact(), $items)) . ']');
    }
    /** @param array<string|int, Value> $members */
    public static function object(array $members): self
    {
        $parts = [];
        foreach ($members as $key => $value) {
            if (!$value instanceof self) throw new \InvalidArgumentException('Expected ordered_json Value');
            $parts[] = quoteKey((string)$key) . ':' . $value->compact();
        }
        return self::parse('{' . implode(',', $parts) . '}');
    }
    public function compact(): string
    {
        if (self::$native ??= \extension_loaded('ordered_json'))
            return \ordered_json_compact_node($this->source, $this->tape, $this->index);
        $meta = $this->tape[$this->index];
        return $meta & Tape::COMPACT || ($meta & Tape::KIND) > Tape::ARRAY ? $this->token() : $this->render();
    }
    /** Serializes a container in PHP; kept out of compact() so the extension path has a small call frame. */
    private function render(): string
    {
        $tape = $this->tape;
        $index = $this->index;
        if (($tape[$index] & Tape::KIND) === Tape::OBJECT) {
            $source = $this->source;
            // Members and the tape records share one order, so key tokens pair with hydrated values.
            $values = array_values($this->cache ??= $this->hydrateMembers());
            $parts = [];
            $n = 0;
            for ($i = $index + 3, $end = $tape[$index] >> Tape::LINK; $i < $end;) {
                $valueMeta = $tape[$i + 3];
                if (!($tape[$i] & Tape::SKIP))
                    $parts[] = substr($source, $tape[$i + 1], $tape[$i + 2] - $tape[$i + 1]) . ':' . $values[$n++]->compact();
                $i = ($valueMeta & Tape::KIND) <= Tape::ARRAY ? $valueMeta >> Tape::LINK : $i + 6;
            }
            return '{' . implode(',', $parts) . '}';
        }
        return '[' . implode(',', array_map(fn(self $v) => $v->compact(), $this->cache ??= $this->hydrateItems())) . ']';
    }
    public function __toString(): string { return $this->compact(); }
    public function jsonSerialize(): never
    {
        throw new \LogicException('Use OrderedJson\\stringify($value)');
    }
}

function parse(string $source, int $maxDepth = MAX_DEPTH): Value
{
    return Value::parse($source, $maxDepth);
}
function stringify(Value $value): string
{
    return $value->compact();
}

/** @internal Descriptor parser producing the same tape as the C extension. */
final class Parser
{
    /** Bytes that end the ordinary run of a string: quote, backslash and control characters. */
    private const STRING_STOP = "\"\\\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f";
    private const WHITESPACE = " \t\n\r";
    private const DIGITS = '0123456789';
    private int $length;
    /** @var list<int> */
    private array $tape = [];
    private int $whitespace = 0;
    private int $duplicates = 0;
    public function __construct(private string $source, private int $maxDepth)
    {
        $this->length = strlen($source);
    }
    private function fail(string $message, int $pos): never { throw new ParseError($message, $pos); }
    public function parse(): array
    {
        // PCRE validates UTF-8 before matching, so only a UTF-8 error means invalid input;
        // other errors come from the backtrack or recursion limits in php.ini.
        if (preg_match('//u', $this->source) !== 1 && preg_last_error() === PREG_BAD_UTF8_ERROR)
            $this->fail('Invalid UTF-8', invalidUtf8Offset($this->source) ?? 0);
        $pos = $this->value(0, 0);
        $pos += strspn($this->source, self::WHITESPACE, $pos);
        if ($pos !== $this->length) $this->fail('Unexpected trailing input', $pos);
        return $this->tape;
    }
    /**
     * Validates the string token at $pos. Returns the offset after it shifted left by one,
     * with the low bit set when the token contains escapes.
     */
    private function string(int $pos): int
    {
        $s = $this->source;
        if (($s[$pos] ?? '') !== '"') $this->fail('Expected string', $pos);
        $pos++;
        $escaped = 0;
        while (true) {
            $pos += strcspn($s, self::STRING_STOP, $pos);
            if ($pos >= $this->length) $this->fail('Unterminated string', $pos);
            $ch = $s[$pos++];
            if ($ch === '"') return $pos << 1 | $escaped;
            if ($ch !== '\\') $this->fail('Unescaped control character', $pos - 1);
            $escaped = 1;
            $escape = $s[$pos] ?? '';
            if ($escape === '') $this->fail('Unfinished escape', $pos);
            $pos++;
            if ($escape === 'u') {
                if (($digits = strspn($s, '0123456789abcdefABCDEF', $pos, 4)) !== 4)
                    $this->fail('Invalid Unicode escape', $pos + $digits);
                $pos += 4;
            } elseif (!str_contains('"\\/bfnrt', $escape)) {
                $this->fail('Invalid escape', $pos - 1);
            }
        }
    }
    /** Parses the value at or after $pos and returns the offset after it. */
    private function value(int $depth, int $pos): int
    {
        $s = $this->source;
        if (($skipped = strspn($s, self::WHITESPACE, $pos)) !== 0) {
            $pos += $skipped;
            $this->whitespace += $skipped;
        }
        $start = $pos;
        $ch = $s[$pos] ?? '';
        if ($ch === '{' || $ch === '[') {
            if ($depth >= $this->maxDepth) $this->fail('Maximum nesting depth exceeded', $pos);
            return $this->container($depth, $pos, $ch === '{');
        }
        if ($ch === '"') {
            $result = $this->string($pos);
            $pos = $result >> 1;
            $kind = Tape::STRING | Tape::COMPACT | ($result & 1 ? Tape::ESCAPED : 0);
        } elseif ($ch === '-' || ($ch !== '' && $ch >= '0' && $ch <= '9')) {
            if ($ch === '-') $pos++;
            if (($s[$pos] ?? '') === '0') {
                $pos++;
            } else {
                if (($count = strspn($s, self::DIGITS, $pos)) === 0) $this->fail('Expected digit', $pos);
                $pos += $count;
            }
            if (($s[$pos] ?? '') === '.') {
                if (($count = strspn($s, self::DIGITS, ++$pos)) === 0) $this->fail('Expected digit', $pos);
                $pos += $count;
            }
            $ch = $s[$pos] ?? '';
            if ($ch === 'e' || $ch === 'E') {
                $ch = $s[++$pos] ?? '';
                if ($ch === '+' || $ch === '-') $pos++;
                if (($count = strspn($s, self::DIGITS, $pos)) === 0) $this->fail('Expected digit', $pos);
                $pos += $count;
            }
            $kind = Tape::NUMBER | Tape::COMPACT;
        } elseif ($ch === 't' && substr_compare($s, 'true', $pos, 4) === 0) {
            $pos += 4;
            $kind = Tape::BOOLEAN | Tape::COMPACT;
        } elseif ($ch === 'f' && substr_compare($s, 'false', $pos, 5) === 0) {
            $pos += 5;
            $kind = Tape::BOOLEAN | Tape::COMPACT;
        } elseif ($ch === 'n' && substr_compare($s, 'null', $pos, 4) === 0) {
            $pos += 4;
            $kind = Tape::NULL | Tape::COMPACT;
        } else {
            $this->fail('Expected JSON value', $pos);
        }
        $this->tape[] = $kind;
        $this->tape[] = $start;
        $this->tape[] = $pos;
        return $pos;
    }
    /** Parses the container that opens at $start and returns the offset after it. */
    private function container(int $depth, int $start, bool $object): int
    {
        $s = $this->source;
        $close = $object ? '}' : ']';
        $whitespace = $this->whitespace;
        $duplicates = $this->duplicates;
        $index = count($this->tape);
        $this->tape[] = 0;
        $this->tape[] = $start;
        $this->tape[] = 0;
        $names = [];
        $pos = $start + 1;
        if (($skipped = strspn($s, self::WHITESPACE, $pos)) !== 0) {
            $pos += $skipped;
            $this->whitespace += $skipped;
        }
        if (($s[$pos] ?? '') !== $close) {
            while (true) {
                if ($object) {
                    $key = count($this->tape);
                    $keyStart = $pos;
                    $result = $this->string($pos);
                    $pos = $result >> 1;
                    $this->tape[] = Tape::STRING | Tape::COMPACT | ($result & 1 ? Tape::ESCAPED : 0) | ($key + 3) << Tape::LINK;
                    $this->tape[] = $keyStart;
                    $this->tape[] = $pos;
                    $name = substr($s, $keyStart + 1, $pos - $keyStart - 2);
                    if (($skipped = strspn($s, self::WHITESPACE, $pos)) !== 0) {
                        $pos += $skipped;
                        $this->whitespace += $skipped;
                    }
                    if (($s[$pos] ?? '') !== ':') $this->fail('Expected colon', $pos);
                    $pos = $this->value($depth + 1, $pos + 1);
                    if ($result & 1) $name = tokenText($name, true);
                    if (isset($names[$name])) {
                        $first = $names[$name];
                        $this->tape[$first] = $this->tape[$first] & 0xff | ($key + 3) << Tape::LINK;
                        $this->tape[$key] |= Tape::SKIP;
                        $this->duplicates++;
                    } else {
                        $names[$name] = $key;
                    }
                } else {
                    $pos = $this->value($depth + 1, $pos);
                }
                if (($skipped = strspn($s, self::WHITESPACE, $pos)) !== 0) {
                    $pos += $skipped;
                    $this->whitespace += $skipped;
                }
                $next = $s[$pos] ?? '';
                if ($next === $close) break;
                if ($next !== ',') $this->fail('Expected comma or closing delimiter', $pos);
                $pos++;
                if (($skipped = strspn($s, self::WHITESPACE, $pos)) !== 0) {
                    $pos += $skipped;
                    $this->whitespace += $skipped;
                }
            }
        }
        $pos++;
        $compact = $this->whitespace === $whitespace && $this->duplicates === $duplicates ? Tape::COMPACT : 0;
        $this->tape[$index] = ($object ? Tape::OBJECT : Tape::ARRAY) | $compact | count($this->tape) << Tape::LINK;
        $this->tape[$index + 2] = $pos;
        return $pos;
    }
}
