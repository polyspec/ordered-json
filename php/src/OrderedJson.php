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

/** Immutable JSON value. Objects use insertion-ordered PHP associative arrays. */
final readonly class Value implements \JsonSerializable, \Stringable
{
    private function __construct(
        private string $source,
        private int $start,
        private int $end,
        private string $kind,
        private array $members = [],
        private array $items = [],
        private array $units = [],
        private array $keys = [],
    ) {}

    public static function parse(string $source, int $maxDepth = MAX_DEPTH, bool $useNative = true): self
    {
        if ($maxDepth < 0 || $maxDepth > MAX_DEPTH)
            throw new \InvalidArgumentException('maxDepth must be between 0 and 256');
        if ($useNative && \extension_loaded('ordered_json')) {
            try { $node = \ordered_json_scan($source, $maxDepth); }
            catch (\OrderedJsonNativeParseError $e) {
                throw new ParseError($e->getMessage(), $e->offset);
            }
        } else {
            $node = (new Parser($source, $maxDepth))->parse();
        }
        return self::hydrate($source, $node);
    }

    private static function hydrate(string $source, array $node): self
    {
        $members = [];
        foreach ($node['members'] ?? [] as $key => $value)
            $members[$key] = self::hydrate($source, $value);
        $keys = [];
        foreach ($node['keys'] ?? [] as $key => $value) $keys[$key] = self::hydrate($source, $value);
        $items = [];
        foreach ($node['items'] ?? [] as $item) $items[] = self::hydrate($source, $item);
        return new self($source, $node['start'], $node['end'], $node['kind'],
            $members, $items, $node['units'] ?? [], $keys);
    }

    public function kind(): string { return $this->kind; }
    public function raw(): string { return substr($this->source, $this->start, $this->end - $this->start); }
    private function expect(string $kind): void
    {
        if ($this->kind !== $kind) throw new \LogicException("Expected $kind, got {$this->kind}");
    }
    /** @return array<string|int, Value> Key order is the first insertion order. */
    public function members(): array { $this->expect('object'); return $this->members; }
    /** @return list<Value> */
    public function items(): array { $this->expect('array'); return $this->items; }
    /** @return list<int> UTF-16 units, including escaped unpaired surrogates. */
    public function stringUnits(): array { $this->expect('string'); return $this->units; }
    public function stringValue(): string
    {
        $this->expect('string');
        return unitsToUtf8($this->units, false);
    }
    public function numberLiteral(): string { $this->expect('number'); return trim($this->raw()); }
    public function booleanValue(): bool { $this->expect('boolean'); return trim($this->raw()) === 'true'; }
    public function get(string $key): ?self { $this->expect('object'); return $this->members[$key] ?? null; }
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
        if ($v->kind !== 'number' || trim($literal) !== $literal)
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
        if (\extension_loaded('ordered_json')) return \ordered_json_compact($this->raw());
        if ($this->kind === 'object') {
            $parts = [];
            foreach ($this->members as $key => $value)
                $parts[] = trim($this->keys[$key]->raw()) . ':' . $value->compact();
            return '{' . implode(',', $parts) . '}';
        }
        if ($this->kind === 'array') return '[' . implode(',', array_map(fn(self $v) => $v->compact(), $this->items)) . ']';
        return trim($this->raw());
    }
    public function __toString(): string { return $this->compact(); }
    public function jsonSerialize(): never
    {
        throw new \LogicException('Use OrderedJson\\stringify($value)');
    }
}

function parse(string $source, int $maxDepth = MAX_DEPTH, bool $useNative = true): Value
{
    return Value::parse($source, $maxDepth, $useNative);
}
function parseNative(string $source, int $maxDepth = MAX_DEPTH): Value
{
    if (!\extension_loaded('ordered_json')) throw new \RuntimeException('The ordered_json extension is not loaded');
    return Value::parse($source, $maxDepth, true);
}
function stringify(Value $value, bool $compact = false): string
{
    return $value->compact();
}

/** @internal Descriptor parser shared in shape with the C extension. */
final class Parser
{
    private int $pos = 0;
    private int $length;
    public function __construct(private string $source, private int $maxDepth)
    {
        $this->length = strlen($source);
    }
    private function fail(string $message): never { throw new ParseError($message, $this->pos); }
    private function peek(): string { return $this->source[$this->pos] ?? ''; }
    private function ws(): void
    {
        while ($this->pos < $this->length && str_contains(" \t\n\r", $this->peek())) $this->pos++;
    }
    private function expect(string $ch, string $message): void
    {
        if ($this->peek() !== $ch) $this->fail($message);
        $this->pos++;
    }
    public function parse(): array
    {
        if (preg_match('//u', $this->source) !== 1) $this->fail('Invalid UTF-8');
        $v = $this->value(0); $this->ws();
        if ($this->pos !== $this->length) $this->fail('Unexpected trailing input');
        $v['start'] = 0; $v['end'] = $this->length;
        return $v;
    }
    private function stringNode(): array
    {
        $start = $this->pos;
        $this->expect('"', 'Expected string');
        $units = [];
        while ($this->pos < $this->length) {
            $ch = ord($this->source[$this->pos++]);
            if ($ch === 34) return ['kind'=>'string', 'start'=>$start, 'end'=>$this->pos, 'units'=>$units];
            if ($ch < 32) $this->fail('Unescaped control character');
            if ($ch === 92) {
                $escape = $this->peek();
                if ($escape === '') $this->fail('Unfinished escape');
                $this->pos++;
                if ($escape === 'u') {
                    $hex = substr($this->source, $this->pos, 4);
                    if (strlen($hex) !== 4 || preg_match('/\A[0-9a-fA-F]{4}\z/', $hex) !== 1)
                        $this->fail('Invalid Unicode escape');
                    $units[] = (int)hexdec($hex); $this->pos += 4;
                } else {
                    $units[] = match ($escape) {
                        '"'=>34, '\\'=>92, '/'=>47, 'b'=>8, 'f'=>12, 'n'=>10, 'r'=>13, 't'=>9,
                        default => $this->fail('Invalid escape'),
                    };
                }
            } elseif ($ch < 128) { $units[] = $ch; }
            else {
                // The entire source was validated as UTF-8 before parsing.
                $count = $ch < 224 ? 1 : ($ch < 240 ? 2 : 3);
                $point = $ch & (0x7f >> $count);
                for ($i = 0; $i < $count; $i++) $point = ($point << 6) | (ord($this->source[$this->pos++]) & 63);
                if ($point <= 65535) $units[] = $point;
                else { $point -= 65536; $units[] = 0xd800 | ($point >> 10); $units[] = 0xdc00 | ($point & 1023); }
            }
        }
        $this->fail('Unterminated string');
    }
    private function digit(): bool { $ch = $this->peek(); return $ch !== '' && $ch >= '0' && $ch <= '9'; }
    private function digits(): void
    {
        if (!$this->digit()) $this->fail('Expected digit');
        while ($this->digit()) $this->pos++;
    }
    private function value(int $depth): array
    {
        $this->ws(); $start = $this->pos; $ch = $this->peek();
        $node = ['start'=>$start];
        if ($ch === '{' || $ch === '[') {
            if ($depth >= $this->maxDepth) $this->fail('Maximum nesting depth exceeded');
            $object = $ch === '{'; $close = $object ? '}' : ']';
            $node['kind'] = $object ? 'object' : 'array';
            $children = []; $keys = []; $this->pos++; $this->ws();
            if ($this->peek() !== $close) {
                while (true) {
                    if ($object) {
                        $key = $this->stringNode(); $this->ws(); $this->expect(':', 'Expected colon');
                        $name = keyText($key['units']);
                        $child = $this->value($depth + 1);
                        $keys[$name] ??= $key;
                        $children[$name] = $child;
                    } else $children[] = $this->value($depth + 1);
                    $this->ws();
                    if ($this->peek() === $close) break;
                    $this->expect(',', 'Expected comma or closing delimiter'); $this->ws();
                }
            }
            $node[$object ? 'members' : 'items'] = $children; $this->pos++;
            if ($object) $node['keys'] = $keys;
        } elseif ($ch === '"') return $this->stringNode();
        elseif ($ch === '-' || $this->digit()) {
            $node['kind'] = 'number';
            if ($ch === '-') $this->pos++;
            if ($this->peek() === '0') $this->pos++; else $this->digits();
            if ($this->peek() === '.') { $this->pos++; $this->digits(); }
            if ($this->peek() === 'e' || $this->peek() === 'E') {
                $this->pos++;
                if ($this->peek() === '+' || $this->peek() === '-') $this->pos++;
                $this->digits();
            }
        } else {
            $found = false;
            foreach (['true', 'false', 'null'] as $literal) {
                if (substr_compare($this->source, $literal, $this->pos, strlen($literal)) === 0) {
                    $node['kind'] = $literal === 'null' ? 'null' : 'boolean';
                    $this->pos += strlen($literal); $found = true; break;
                }
            }
            if (!$found) $this->fail('Expected JSON value');
        }
        $node['end'] = $this->pos;
        return $node;
    }
}
