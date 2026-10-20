<?php

declare(strict_types=1);

namespace Polyspec\OrderedJson;

/** @internal Descriptor parser producing the same tape as the C extension. */
final class Parser
{
    /** Bytes that end the ordinary run of a string: quote, backslash and control characters. */
    private const STRING_STOP = "\"\\"
        . "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f"
        . "\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f";
    private const WHITESPACE = " \t\n\r";
    private const DIGITS = '0123456789';
    private int $length;
    /** @var list<int> */
    private array $tape = [];
    private int $whitespace = 0;
    private int $duplicates = 0;
    public function __construct(private string $source, private int $maxDepth, private bool $rejectDuplicates = false)
    {
        $this->length = strlen($source);
    }
    private function fail(string $message, int $pos): never
    {
        throw new ParseError($message, $pos);
    }
    public function parse(): array
    {
        // PCRE validates UTF-8 before matching, so only a UTF-8 error means invalid input;
        // other errors come from the backtrack or recursion limits in php.ini.
        if (preg_match('//u', $this->source) !== 1 && preg_last_error() === PREG_BAD_UTF8_ERROR) {
            $this->fail('Invalid UTF-8', invalidUtf8Offset($this->source) ?? 0);
        }
        $pos = $this->value(0, 0);
        $pos += strspn($this->source, self::WHITESPACE, $pos);
        if ($pos !== $this->length) {
            $this->fail('Unexpected trailing input', $pos);
        }
        return $this->tape;
    }
    /**
     * Validates the string token at $pos. Returns the offset after it shifted left by one,
     * with the low bit set when the token contains escapes.
     */
    private function string(int $pos): int
    {
        $s = $this->source;
        if (($s[$pos] ?? '') !== '"') {
            $this->fail('Expected string', $pos);
        }
        $pos++;
        $escaped = 0;
        while (true) {
            $pos += strcspn($s, self::STRING_STOP, $pos);
            if ($pos >= $this->length) {
                $this->fail('Unterminated string', $pos);
            }
            $ch = $s[$pos++];
            if ($ch === '"') {
                return $pos << 1 | $escaped;
            }
            if ($ch !== '\\') {
                $this->fail('Unescaped control character', $pos - 1);
            }
            $escaped = 1;
            $escape = $s[$pos] ?? '';
            if ($escape === '') {
                $this->fail('Unfinished escape', $pos);
            }
            $pos++;
            if ($escape === 'u') {
                if (($digits = strspn($s, '0123456789abcdefABCDEF', $pos, 4)) !== 4) {
                    $this->fail('Invalid Unicode escape', $pos + $digits);
                }
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
            if ($depth >= $this->maxDepth) {
                $this->fail('Maximum nesting depth exceeded', $pos);
            }
            return $this->container($depth, $pos, $ch === '{');
        }
        if ($ch === '"') {
            $result = $this->string($pos);
            $pos = $result >> 1;
            $kind = Tape::STRING | Tape::COMPACT | ($result & 1 ? Tape::ESCAPED : 0);
        } elseif ($ch === '-' || ($ch !== '' && $ch >= '0' && $ch <= '9')) {
            if ($ch === '-') {
                $pos++;
            }
            if (($s[$pos] ?? '') === '0') {
                $pos++;
            } else {
                if (($count = strspn($s, self::DIGITS, $pos)) === 0) {
                    $this->fail('Expected digit', $pos);
                }
                $pos += $count;
            }
            if (($s[$pos] ?? '') === '.') {
                if (($count = strspn($s, self::DIGITS, ++$pos)) === 0) {
                    $this->fail('Expected digit', $pos);
                }
                $pos += $count;
            }
            $ch = $s[$pos] ?? '';
            if ($ch === 'e' || $ch === 'E') {
                $ch = $s[++$pos] ?? '';
                if ($ch === '+' || $ch === '-') {
                    $pos++;
                }
                if (($count = strspn($s, self::DIGITS, $pos)) === 0) {
                    $this->fail('Expected digit', $pos);
                }
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
                    $this->tape[] = Tape::STRING | Tape::COMPACT | ($result & 1 ? Tape::ESCAPED : 0)
                        | ($key + 3) << Tape::LINK;
                    $this->tape[] = $keyStart;
                    $this->tape[] = $pos;
                    $name = substr($s, $keyStart + 1, $pos - $keyStart - 2);
                    if ($result & 1) {
                        $name = tokenText($name);
                    }
                    if ($this->rejectDuplicates && isset($names[$name])) {
                        $this->fail('Duplicate object key', $keyStart);
                    }
                    if (($skipped = strspn($s, self::WHITESPACE, $pos)) !== 0) {
                        $pos += $skipped;
                        $this->whitespace += $skipped;
                    }
                    if (($s[$pos] ?? '') !== ':') {
                        $this->fail('Expected colon', $pos);
                    }
                    $pos = $this->value($depth + 1, $pos + 1);
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
                if ($next === $close) {
                    break;
                }
                if ($next !== ',') {
                    $this->fail('Expected comma or closing delimiter', $pos);
                }
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
