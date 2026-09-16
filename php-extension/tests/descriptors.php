<?php
// Package tests for the native descriptor API. Shared cases reach the extension
// only through the PHP Value API, so descriptor handling is covered here.
declare(strict_types=1);

$failures = [];

function check(array &$failures, string $name, callable $body): void
{
    try {
        $body();
    } catch (Throwable $error) {
        $failures[] = $name . ': ' . get_class($error) . ': ' . $error->getMessage();
    }
}

function expectThrows(string $class, callable $body): void
{
    try {
        $body();
    } catch (Throwable $error) {
        if (!($error instanceof $class))
            throw new RuntimeException('expected ' . $class . ', got ' . get_class($error) . ': ' . $error->getMessage());
        return;
    }
    throw new RuntimeException('expected ' . $class . ', no error was raised');
}

function expectSame(mixed $expected, mixed $actual): void
{
    if ($expected !== $actual)
        throw new RuntimeException('expected ' . json_encode($expected) . ', got ' . json_encode($actual));
}

/** @return list<string> Raw tokens of hydrated children. */
function tokens(array $children): array
{
    return array_values(array_map(static fn($child) => $child->raw(), $children));
}

/** Index of the first record of the given kind, so tests do not hard-code tape offsets. */
function firstRecord(array $tape, int $kind): int
{
    for ($index = 0; $index < count($tape); $index += 3)
        if (($tape[$index] & 7) === $kind) return $index;
    throw new RuntimeException('No record of kind ' . $kind);
}

// The class lookup happens before descriptor validation, so this runs first.
check($failures, 'hydrate without the value class', static function () {
    expectThrows(Error::class, static fn() => ordered_json_hydrate('[1]', ordered_json_scan('[1]'), 0));
});

require $argv[1] ?? dirname(__DIR__, 2) . '/php/src/OrderedJson.php';

$source = '{"aa":1,"b":[2,3]}';
$tape = ordered_json_scan($source);
$array = firstRecord($tape, 2);

check($failures, 'hydrate object members', static function () use ($source, $tape) {
    $members = ordered_json_hydrate($source, $tape, 0);
    expectSame(['aa', 'b'], array_keys($members));
    expectSame(['1', '[2,3]'], tokens($members));
});

check($failures, 'hydrate array items', static function () use ($source, $tape, $array) {
    expectSame(['2', '3'], tokens(ordered_json_hydrate($source, $tape, $array)));
});

check($failures, 'repeated key keeps the first position and the last value', static function () {
    $repeated = '{"a":1,"b":2,"a":3}';
    $members = ordered_json_hydrate($repeated, ordered_json_scan($repeated), 0);
    expectSame(['a', 'b'], array_keys($members));
    expectSame(['3', '2'], tokens($members));
});

check($failures, 'escaped member name decodes', static function () {
    $escaped = '{"aé🌍":1}';
    $members = ordered_json_hydrate($escaped, ordered_json_scan($escaped), 0);
    expectSame(["a\u{e9}\u{1f30d}"], array_keys($members));
});

check($failures, 'unpaired surrogate member name keeps WTF-8 identity', static function () {
    $lone = '{"a\ud800":1}';
    $members = ordered_json_hydrate($lone, ordered_json_scan($lone), 0);
    expectSame(["a\xed\xa0\x80"], array_keys($members));
});

$malformed = [
    'negative index' => [$source, $tape, -1],
    'index past the tape' => [$source, $tape, 999],
    'scalar record' => [$source, $tape, 6],
    'link past the tape' => [$source, array_replace($tape, [0 => ($tape[0] & 0xff) | (9999 << 8)]), 0],
    'key span past the source' => [$source, array_replace($tape, [4 => 9999]), 0],
    'member value before its key' => [$source, array_replace($tape, [3 => $tape[3] & 0xff]), 0],
    'truncated escape' => ['{"a\u00":1}', [1 | (9 << 8), 0, 10, 3 | 16 | (6 << 8), 1, 9, 4 | 8, 10, 11], 0],
    'empty tape' => [$source, [], 0],
];
foreach ($malformed as $name => $arguments)
    check($failures, 'hydrate rejects a ' . $name, static function () use ($arguments) {
        expectThrows(ValueError::class, static fn() => ordered_json_hydrate(...$arguments));
    });

check($failures, 'compact_node rejects a descriptor that does not match the source', static function () use ($source, $tape) {
    expectThrows(ValueError::class, static fn() => ordered_json_compact_node($source, array_replace($tape, [2 => 9999]), 0));
    expectThrows(ValueError::class, static fn() => ordered_json_compact_node($source, $tape, -1));
});

check($failures, 'compact_node copies a compact token', static function () use ($source, $tape, $array) {
    expectSame('[2,3]', ordered_json_compact_node($source, $tape, $array));
    expectSame($source, ordered_json_compact_node($source, $tape, 0));
});

check($failures, 'scan rejects a depth outside the supported range', static function () {
    expectThrows(ValueError::class, static fn() => ordered_json_scan('[]', -1));
    expectThrows(ValueError::class, static fn() => ordered_json_scan('[]', 257));
});

check($failures, 'scan reports the parse error offset', static function () {
    try {
        ordered_json_scan('[1,]');
    } catch (OrderedJsonNativeParseError $error) {
        expectSame(3, $error->offset);
        return;
    }
    throw new RuntimeException('expected OrderedJsonNativeParseError');
});

if ($failures) {
    fwrite(STDERR, implode(PHP_EOL, $failures) . PHP_EOL);
    exit(1);
}
