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

final readonly class Member
{
    public function __construct(public Value $key, public Value $value)
    {
        if ($key->kind() !== 'string') throw new \InvalidArgumentException('Object key must be string');
    }
}

/** Immutable JSON value. Object members are lists, never associative maps. */
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
        foreach ($node['members'] ?? [] as $m)
            $members[] = new Member(self::hydrate($source, $m['key']), self::hydrate($source, $m['value']));
        $items = [];
        foreach ($node['items'] ?? [] as $item) $items[] = self::hydrate($source, $item);
        return new self($source, $node['start'], $node['end'], $node['kind'],
            $members, $items, $node['units'] ?? []);
    }

    public function kind(): string { return $this->kind; }
    public function raw(): string { return substr($this->source, $this->start, $this->end - $this->start); }
    private function expect(string $kind): void
    {
        if ($this->kind !== $kind) throw new \LogicException("Expected $kind, got {$this->kind}");
    }
    /** @return list<Member> */
    public function members(): array { $this->expect('object'); return $this->members; }
    /** @return list<Value> */
    public function items(): array { $this->expect('array'); return $this->items; }
    /** @return list<int> UTF-16 units, including escaped unpaired surrogates. */
    public function stringUnits(): array { $this->expect('string'); return $this->units; }
    public function stringValue(): string
    {
        $this->expect('string');
        try { return json_decode($this->raw(), false, 512, JSON_THROW_ON_ERROR); }
        catch (\JsonException $e) { throw new \UnexpectedValueException('Unpaired surrogate; use stringUnits()', 0, $e); }
    }
    public function numberLiteral(): string { $this->expect('number'); return trim($this->raw()); }
    public function booleanValue(): bool { $this->expect('boolean'); return trim($this->raw()) === 'true'; }
    public function get(string $key): ?self { return $this->getAll($key)[0] ?? null; }
    public function getUnits(array $units): ?self
    {
        foreach ($this->members() as $m) if ($m->key->units === $units) return $m->value;
        return null;
    }
    /** @return list<Value> */
    public function getAll(string $key): array
    {
        $units = self::string($key)->units;
        $out = [];
        foreach ($this->members() as $m) if ($m->key->units === $units) $out[] = $m->value;
        return $out;
    }
    public static function string(string $text): self
    {
        return self::parse(json_encode($text, JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
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
        return self::parse('[' . implode(',', array_map(fn(self $v) => $v->raw(), $items)) . ']');
    }
    /** @param list<Member> $members */
    public static function object(array $members): self
    {
        if (!array_is_list($members)) throw new \InvalidArgumentException('Expected a list of members');
        return self::parse('{' . implode(',', array_map(
            fn(Member $m) => $m->key->raw() . ':' . $m->value->raw(), $members)) . '}');
    }
    public function compact(): string
    {
        if (\extension_loaded('ordered_json')) return \ordered_json_compact($this->raw());
        $out = ''; $quoted = false; $escaped = false; $raw = $this->raw();
        for ($i = 0, $n = strlen($raw); $i < $n; $i++) {
            $ch = $raw[$i];
            if ($quoted) {
                $out .= $ch;
                if ($escaped) $escaped = false;
                elseif ($ch === '\\') $escaped = true;
                elseif ($ch === '"') $quoted = false;
            } elseif (!str_contains(" \t\n\r", $ch)) {
                $out .= $ch;
                if ($ch === '"') $quoted = true;
            }
        }
        return $out;
    }
    public function __toString(): string { return $this->raw(); }
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
    return $compact ? $value->compact() : $value->raw();
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
            $children = []; $this->pos++; $this->ws();
            if ($this->peek() !== $close) {
                while (true) {
                    if ($object) {
                        $key = $this->stringNode(); $this->ws(); $this->expect(':', 'Expected colon');
                        $children[] = ['key'=>$key, 'value'=>$this->value($depth + 1)];
                    } else $children[] = $this->value($depth + 1);
                    $this->ws();
                    if ($this->peek() === $close) break;
                    $this->expect(',', 'Expected comma or closing delimiter'); $this->ws();
                }
            }
            $node[$object ? 'members' : 'items'] = $children; $this->pos++;
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
