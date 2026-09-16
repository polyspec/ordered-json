<?php
// Package tests for the native backend: the descriptor API and the shared value
// API checks so both PHP backends answer identically.
declare(strict_types=1);

$library = $argv[1] ?? dirname(__DIR__, 2) . '/php/src/OrderedJson.php';
require dirname($library, 2) . '/tests/api_checks.php';

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

/** @return array<string, callable> Descriptor cases, keyed by case id. */
function descriptorCases(): array
{
    $source = '{"aa":1,"b":[2,3]}';
    $tape = ordered_json_scan($source);
    $array = firstRecord($tape, 2);
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
    return [
        'hydrate_object_members' => static function () use ($source, $tape) {
            $members = ordered_json_hydrate($source, $tape, 0);
            expectSame(['aa', 'b'], array_keys($members));
            expectSame(['1', '[2,3]'], tokens($members));
        },
        'hydrate_array_items' => static function () use ($source, $tape, $array) {
            expectSame(['2', '3'], tokens(ordered_json_hydrate($source, $tape, $array)));
        },
        'escaped_member_name_decodes' => static function () {
            $escaped = '{"aé🌍":1}';
            $members = ordered_json_hydrate($escaped, ordered_json_scan($escaped), 0);
            expectSame(["a\u{e9}\u{1f30d}"], array_keys($members));
        },
        'unpaired_surrogate_member_name_keeps_wtf8_identity' => static function () {
            $lone = '{"a\ud800":1}';
            $members = ordered_json_hydrate($lone, ordered_json_scan($lone), 0);
            expectSame(["a\xed\xa0\x80"], array_keys($members));
        },
        'hydrate_rejects_malformed_descriptors' => static function () use ($malformed) {
            foreach ($malformed as $name => $arguments)
                try {
                    expectThrows(ValueError::class, '', static fn() => ordered_json_hydrate(...$arguments));
                } catch (Throwable $error) {
                    throw new RuntimeException($name . ': ' . $error->getMessage());
                }
        },
        'compact_node_rejects_mismatched_descriptors' => static function () use ($source, $tape) {
            expectThrows(ValueError::class, '', static fn() => ordered_json_compact_node($source, array_replace($tape, [2 => 9999]), 0));
            expectThrows(ValueError::class, '', static fn() => ordered_json_compact_node($source, $tape, -1));
        },
        'compact_node_copies_a_compact_token' => static function () use ($source, $tape, $array) {
            expectSame('[2,3]', ordered_json_compact_node($source, $tape, $array));
            expectSame($source, ordered_json_compact_node($source, $tape, 0));
        },
        'scan_rejects_depth_outside_the_range' => static function () {
            expectThrows(ValueError::class, '', static fn() => ordered_json_scan('[]', -1));
            expectThrows(ValueError::class, '', static fn() => ordered_json_scan('[]', 257));
        },
        'scan_reports_the_parse_error_offset' => static function () {
            try {
                ordered_json_scan('[1,]');
            } catch (OrderedJsonNativeParseError $error) {
                expectSame(3, $error->offset);
                return;
            }
            throw new RuntimeException('expected OrderedJsonNativeParseError');
        },
    ];
}

if (!extension_loaded('ordered_json')) {
    fwrite(STDERR, 'These checks cover the native backend; load the ordered_json extension' . PHP_EOL);
    exit(1);
}

$failures = [];
// The class lookup happens before descriptor validation, so this runs first.
check($failures, 'hydrate_without_the_value_class', static function () {
    expectThrows(Error::class, '', static fn() => ordered_json_hydrate('[1]', ordered_json_scan('[1]'), 0));
});

require $library;

foreach (descriptorCases() as $id => $body) check($failures, $id, $body);
// The extension is a second backend for the same value API; both must answer identically.
$failures = array_merge($failures, orderedJsonApiChecks());

if ($failures) {
    fwrite(STDERR, implode(PHP_EOL, $failures) . PHP_EOL);
    exit(1);
}

// All descriptor and shared checks ran before the listing. The keys describe
// cases implemented by this executable suite, not entries copied from the
// repository standard.
if (in_array('--cases', $argv, true)) {
    echo implode(PHP_EOL, ['hydrate_without_the_value_class',
        ...array_keys(descriptorCases()), ...array_keys(orderedJsonApiCases())]), PHP_EOL;
}
