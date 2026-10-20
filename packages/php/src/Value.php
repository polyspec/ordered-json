<?php

declare(strict_types=1);

namespace Polyspec\OrderedJson;

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

    private function __construct()
    {
    }

    public static function parse(string $source, int $maxDepth = MAX_DEPTH): self
    {
        if ($maxDepth < 0 || $maxDepth > MAX_DEPTH) {
            throw new \InvalidArgumentException('maxDepth must be between 0 and 256');
        }
        if (self::$native ??= \extension_loaded('polyspec_ordered_json')) {
            try {
                $tape = \ordered_json_scan($source, $maxDepth);
            } catch (NativeParseError $e) {
                throw new ParseError($e->getMessage(), $e->offset);
            }
        } else {
            $tape = (new Parser($source, $maxDepth))->parse();
        }
        return self::root($source, $tape);
    }

    /**
     * Parses like parse() with the default depth limit and rejects a repeated decoded object key
     * at the first byte of the second key token. The native scanner keeps the last value of a
     * repeated key, so this method always parses with the PHP parser.
     */
    public static function parseRejectDuplicates(string $source): self
    {
        return self::root($source, (new Parser($source, MAX_DEPTH, true))->parse());
    }

    /** @param list<int> $tape */
    private static function root(string $source, array $tape): self
    {
        $value = new self();
        $value->source = $source;
        $value->tape = $tape;
        $value->index = 0;
        return $value;
    }

    /** @return array<string|int, Value> Members keyed by decoded name, in first insertion order. */
    private function hydrateMembers(): array
    {
        if (self::$native ??= \extension_loaded('polyspec_ordered_json')) {
            return \ordered_json_hydrate($this->source, $this->tape, $this->index);
        }
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
                if ($meta & Tape::ESCAPED) {
                    $name = tokenText($name, true);
                }
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
        if (self::$native ??= \extension_loaded('polyspec_ordered_json')) {
            return \ordered_json_hydrate($this->source, $this->tape, $this->index);
        }
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

    public function kind(): string
    {
        return Tape::KINDS[$this->tape[$this->index] & Tape::KIND];
    }
    public function raw(): string
    {
        return $this->index === 0 ? $this->source : $this->token();
    }
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
        if (($this->tape[$this->index] & Tape::KIND) !== Tape::OBJECT) {
            $this->mismatch('object');
        }
        return $this->cache ??= $this->hydrateMembers();
    }
    /** @return list<Value> */
    public function items(): array
    {
        if (($this->tape[$this->index] & Tape::KIND) !== Tape::ARRAY) {
            $this->mismatch('array');
        }
        return $this->cache ??= $this->hydrateItems();
    }
    /** @return list<int> UTF-16 units, including escaped unpaired surrogates. */
    public function stringUnits(): array
    {
        $tape = $this->tape;
        $index = $this->index;
        if (($tape[$index] & Tape::KIND) !== Tape::STRING) {
            $this->mismatch('string');
        }
        $start = $tape[$index + 1] + 1;
        return $this->cache ??= tokenUnits(substr($this->source, $start, $tape[$index + 2] - 1 - $start));
    }
    public function stringValue(): string
    {
        $tape = $this->tape;
        $index = $this->index;
        $meta = $tape[$index];
        if (($meta & Tape::KIND) !== Tape::STRING) {
            $this->mismatch('string');
        }
        $start = $tape[$index + 1] + 1;
        $content = substr($this->source, $start, $tape[$index + 2] - 1 - $start);
        return $meta & Tape::ESCAPED ? tokenText($content, false) : $content;
    }
    public function numberLiteral(): string
    {
        $tape = $this->tape;
        $index = $this->index;
        if (($tape[$index] & Tape::KIND) !== Tape::NUMBER) {
            $this->mismatch('number');
        }
        $start = $tape[$index + 1];
        return substr($this->source, $start, $tape[$index + 2] - $start);
    }
    public function booleanValue(): bool
    {
        $tape = $this->tape;
        $index = $this->index;
        if (($tape[$index] & Tape::KIND) !== Tape::BOOLEAN) {
            $this->mismatch('boolean');
        }
        return $this->source[$tape[$index + 1]] === 't';
    }
    public function get(string $key): ?self
    {
        if (($this->tape[$this->index] & Tape::KIND) !== Tape::OBJECT) {
            $this->mismatch('object');
        }
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
            if (!is_int($unit) || $unit < 0 || $unit > 65535) {
                throw new \InvalidArgumentException('Expected UTF-16 code units');
            }
            $raw .= sprintf('\\u%04x', $unit);
        }
        return self::parse($raw . '"');
    }
    public static function number(string $literal): self
    {
        $v = self::parse($literal);
        if ($v->kind() !== 'number' || trim($literal) !== $literal) {
            throw new \InvalidArgumentException('Expected number literal without whitespace');
        }
        return $v;
    }
    public static function boolean(bool $value): self
    {
        return self::parse($value ? 'true' : 'false');
    }
    public static function null(): self
    {
        return self::parse('null');
    }
    public static function array(array $items): self
    {
        if (!array_is_list($items)) {
            throw new \InvalidArgumentException('Expected a list of values');
        }
        return self::parse('[' . implode(',', array_map(fn(self $v) => $v->compact(), $items)) . ']');
    }
    /** @param array<string|int, Value> $members */
    public static function object(array $members): self
    {
        $parts = [];
        foreach ($members as $key => $value) {
            if (!$value instanceof self) {
                throw new \InvalidArgumentException('Expected ordered_json Value');
            }
            $parts[] = quoteKey((string)$key) . ':' . $value->compact();
        }
        return self::parse('{' . implode(',', $parts) . '}');
    }
    public function compact(): string
    {
        if (self::$native ??= \extension_loaded('polyspec_ordered_json')) {
            return \ordered_json_compact_node($this->source, $this->tape, $this->index);
        }
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
                if (!($tape[$i] & Tape::SKIP)) {
                    $parts[] = substr($source, $tape[$i + 1], $tape[$i + 2] - $tape[$i + 1])
                        . ':' . $values[$n++]->compact();
                }
                $i = ($valueMeta & Tape::KIND) <= Tape::ARRAY ? $valueMeta >> Tape::LINK : $i + 6;
            }
            return '{' . implode(',', $parts) . '}';
        }
        $items = $this->cache ??= $this->hydrateItems();
        return '[' . implode(',', array_map(fn(self $v) => $v->compact(), $items)) . ']';
    }
    public function __toString(): string
    {
        return $this->compact();
    }
    public function jsonSerialize(): never
    {
        throw new \LogicException('Use Polyspec\\OrderedJson\\stringify($value)');
    }
}
