<?php
declare(strict_types=1);

namespace Polyspec\OrderedJson;

const MAX_DEPTH = 256;

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

function parse(string $source, int $maxDepth = MAX_DEPTH): Value
{
    return Value::parse($source, $maxDepth);
}
function stringify(Value $value): string
{
    return $value->compact();
}
