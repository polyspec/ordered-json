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
                throw new UnexpectedValueException('Unpaired surrogate; use stringUnits()');
            }
        } elseif ($point >= 0xdc00 && $point <= 0xdfff && !$allowUnpaired) {
            throw new UnexpectedValueException('Unpaired surrogate; use stringUnits()');
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
    return preg_match('/[\x80-\xff]/', $text) === 1 ? utf8Units($text) : array_values(unpack('C*', $text));
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

    /** Index of the record that follows the value at $index and its descendants. */
    public static function next(array $tape, int $index): int
    {
        return ($tape[$index] & self::KIND) <= self::ARRAY ? $tape[$index] >> self::LINK : $index + 3;
    }
}

/** JSON value. Objects use insertion-ordered PHP associative arrays. Child values hydrate lazily. */
final class Value implements \JsonSerializable, \Stringable
{
    private static ?bool $native = null;
    /** @var array<string|int, Value>|null */
    private ?array $members = null;
    /** @var array<string|int, Value>|null The first key token of each member. */
    private ?array $keys = null;
    /** @var list<Value>|null */
    private ?array $items = null;
    /** @var list<int>|null */
    private ?array $units = null;

    /** @param list<int> $tape Descriptor tape; this value's record starts at $index. */
    private function __construct(
        private string $source,
        private array $tape,
        private int $index,
    ) {}

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
        return new self($source, $tape, 0);
    }

    private function hydrateMembers(): void
    {
        if ($this->members !== null) return;
        $members = $keys = [];
        $tape = $this->tape;
        for ($i = $this->index + 3, $end = $tape[$this->index] >> Tape::LINK; $i < $end; $i = Tape::next($tape, $i + 3)) {
            $meta = $tape[$i];
            if ($meta & Tape::SKIP) continue;
            $start = $tape[$i + 1] + 1;
            $name = substr($this->source, $start, $tape[$i + 2] - 1 - $start);
            if ($meta & Tape::ESCAPED) $name = keyText(tokenUnits($name));
            $keys[$name] = new self($this->source, $tape, $i);
            $members[$name] = new self($this->source, $tape, $meta >> Tape::LINK);
        }
        $this->keys = $keys;
        $this->members = $members;
    }

    private function hydrateItems(): void
    {
        if ($this->items !== null) return;
        $items = [];
        $tape = $this->tape;
        for ($i = $this->index + 3, $end = $tape[$this->index] >> Tape::LINK; $i < $end; $i = Tape::next($tape, $i))
            $items[] = new self($this->source, $tape, $i);
        $this->items = $items;
    }

    public function kind(): string { return Tape::KINDS[$this->tape[$this->index] & Tape::KIND]; }
    public function raw(): string { return $this->index === 0 ? $this->source : $this->token(); }
    private function token(): string
    {
        $start = $this->tape[$this->index + 1];
        return substr($this->source, $start, $this->tape[$this->index + 2] - $start);
    }
    private function content(): string
    {
        $start = $this->tape[$this->index + 1] + 1;
        return substr($this->source, $start, $this->tape[$this->index + 2] - 1 - $start);
    }
    private function expect(string $kind): void
    {
        if ($this->kind() !== $kind) throw new \LogicException("Expected $kind, got {$this->kind()}");
    }
    /** @return array<string|int, Value> Key order is the first insertion order. */
    public function members(): array { $this->expect('object'); $this->hydrateMembers(); return $this->members; }
    /** @return list<Value> */
    public function items(): array { $this->expect('array'); $this->hydrateItems(); return $this->items; }
    /** @return list<int> UTF-16 units, including escaped unpaired surrogates. */
    public function stringUnits(): array { $this->expect('string'); return $this->units ??= tokenUnits($this->content()); }
    public function stringValue(): string
    {
        $this->expect('string');
        if (!($this->tape[$this->index] & Tape::ESCAPED)) return $this->content();
        return unitsToUtf8($this->stringUnits(), false);
    }
    public function numberLiteral(): string { $this->expect('number'); return trim($this->raw()); }
    public function booleanValue(): bool { $this->expect('boolean'); return trim($this->raw()) === 'true'; }
    public function get(string $key): ?self { $this->expect('object'); $this->hydrateMembers(); return $this->members[$key] ?? null; }
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
        $kind = $meta & Tape::KIND;
        if ($meta & Tape::COMPACT || $kind > Tape::ARRAY) return $this->token();
        if ($kind === Tape::OBJECT) {
            $this->hydrateMembers();
            $parts = [];
            foreach ($this->members as $key => $value)
                $parts[] = $this->keys[$key]->token() . ':' . $value->compact();
            return '{' . implode(',', $parts) . '}';
        }
        $this->hydrateItems();
        return '[' . implode(',', array_map(fn(self $v) => $v->compact(), $this->items)) . ']';
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
    private int $pos = 0;
    private int $length;
    /** @var list<int> */
    private array $tape = [];
    private int $whitespace = 0;
    private int $duplicates = 0;
    public function __construct(private string $source, private int $maxDepth)
    {
        $this->length = strlen($source);
    }
    private function fail(string $message): never { throw new ParseError($message, $this->pos); }
    private function ws(): void
    {
        if (($skipped = strspn($this->source, " \t\n\r", $this->pos)) !== 0) {
            $this->pos += $skipped;
            $this->whitespace += $skipped;
        }
    }
    private function digits(): void
    {
        $count = strspn($this->source, '0123456789', $this->pos);
        if ($count === 0) $this->fail('Expected digit');
        $this->pos += $count;
    }
    public function parse(): array
    {
        if (preg_match('//u', $this->source) !== 1) $this->fail('Invalid UTF-8');
        $this->value(0); $this->ws();
        if ($this->pos !== $this->length) $this->fail('Unexpected trailing input');
        return $this->tape;
    }
    /** Validates the string token at the cursor and returns its flags. */
    private function string(): int
    {
        if (($this->source[$this->pos] ?? '') !== '"') $this->fail('Expected string');
        $this->pos++;
        $flags = Tape::COMPACT;
        while (true) {
            $this->pos += strcspn($this->source, self::STRING_STOP, $this->pos);
            if ($this->pos >= $this->length) $this->fail('Unterminated string');
            $ch = $this->source[$this->pos++];
            if ($ch === '"') return $flags;
            if ($ch !== '\\') $this->fail('Unescaped control character');
            $flags |= Tape::ESCAPED;
            $escape = $this->source[$this->pos] ?? '';
            if ($escape === '') $this->fail('Unfinished escape');
            $this->pos++;
            if ($escape === 'u') {
                if (strspn($this->source, '0123456789abcdefABCDEF', $this->pos, 4) !== 4) $this->fail('Invalid Unicode escape');
                $this->pos += 4;
            } elseif (!str_contains('"\\/bfnrt', $escape)) {
                $this->fail('Invalid escape');
            }
        }
    }
    private function value(int $depth): void
    {
        $this->ws();
        $start = $this->pos;
        $ch = $this->source[$start] ?? '';
        if ($ch === '{' || $ch === '[') {
            if ($depth >= $this->maxDepth) $this->fail('Maximum nesting depth exceeded');
            $this->container($depth, $start, $ch === '{');
            return;
        }
        if ($ch === '"') {
            $kind = Tape::STRING | $this->string();
        } elseif ($ch === '-' || ($ch !== '' && $ch >= '0' && $ch <= '9')) {
            if ($ch === '-') $this->pos++;
            if (($this->source[$this->pos] ?? '') === '0') $this->pos++; else $this->digits();
            if (($this->source[$this->pos] ?? '') === '.') { $this->pos++; $this->digits(); }
            $ch = $this->source[$this->pos] ?? '';
            if ($ch === 'e' || $ch === 'E') {
                $this->pos++;
                $ch = $this->source[$this->pos] ?? '';
                if ($ch === '+' || $ch === '-') $this->pos++;
                $this->digits();
            }
            $kind = Tape::NUMBER | Tape::COMPACT;
        } else {
            if ($ch === 't') { $literal = 'true'; $kind = Tape::BOOLEAN | Tape::COMPACT; }
            elseif ($ch === 'f') { $literal = 'false'; $kind = Tape::BOOLEAN | Tape::COMPACT; }
            elseif ($ch === 'n') { $literal = 'null'; $kind = Tape::NULL | Tape::COMPACT; }
            else $this->fail('Expected JSON value');
            if (substr_compare($this->source, $literal, $this->pos, strlen($literal)) !== 0) $this->fail('Expected JSON value');
            $this->pos += strlen($literal);
        }
        $this->tape[] = $kind;
        $this->tape[] = $start;
        $this->tape[] = $this->pos;
    }
    private function container(int $depth, int $start, bool $object): void
    {
        $close = $object ? '}' : ']';
        $whitespace = $this->whitespace;
        $duplicates = $this->duplicates;
        $index = count($this->tape);
        $this->tape[] = 0;
        $this->tape[] = $start;
        $this->tape[] = 0;
        $names = [];
        $this->pos++; $this->ws();
        if (($this->source[$this->pos] ?? '') !== $close) {
            while (true) {
                if ($object) {
                    $key = count($this->tape);
                    $keyStart = $this->pos;
                    $flags = $this->string();
                    $this->tape[] = Tape::STRING | $flags | ($key + 3) << Tape::LINK;
                    $this->tape[] = $keyStart;
                    $this->tape[] = $this->pos;
                    $this->ws();
                    if (($this->source[$this->pos] ?? '') !== ':') $this->fail('Expected colon');
                    $this->pos++;
                    $this->value($depth + 1);
                    $name = substr($this->source, $keyStart + 1, $this->tape[$key + 2] - $keyStart - 2);
                    if ($flags & Tape::ESCAPED) $name = keyText(tokenUnits($name));
                    if (isset($names[$name])) {
                        $first = $names[$name];
                        $this->tape[$first] = $this->tape[$first] & 0xff | ($key + 3) << Tape::LINK;
                        $this->tape[$key] |= Tape::SKIP;
                        $this->duplicates++;
                    } else {
                        $names[$name] = $key;
                    }
                } else {
                    $this->value($depth + 1);
                }
                $this->ws();
                $next = $this->source[$this->pos] ?? '';
                if ($next === $close) break;
                if ($next !== ',') $this->fail('Expected comma or closing delimiter');
                $this->pos++; $this->ws();
            }
        }
        $this->pos++;
        $compact = $this->whitespace === $whitespace && $this->duplicates === $duplicates ? Tape::COMPACT : 0;
        $this->tape[$index] = ($object ? Tape::OBJECT : Tape::ARRAY) | $compact | count($this->tape) << Tape::LINK;
        $this->tape[$index + 2] = $this->pos;
    }
}
