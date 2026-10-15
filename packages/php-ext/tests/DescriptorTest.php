<?php

declare(strict_types=1);

namespace Polyspec\OrderedJson\Extension\Tests;

use PHPUnit\Framework\TestCase;
use Polyspec\OrderedJson\NativeParseError;
use Polyspec\OrderedJson\Value;
use Throwable;
use ValueError;

/**
 * The descriptor API of the extension, run by PHPUnit with the extension loaded (config/parity.json, php-extension);
 * each test method is a feature unit. The value API of both PHP backends is tested by ValueApiTest of packages/php, and
 * the hydration without the value class by ValueClassTest.
 */
final class DescriptorTest extends TestCase
{
    private const SOURCE = '{"aa":1,"b":[2,3]}';

    protected function setUp(): void
    {
        self::assertTrue(
            extension_loaded('ordered_json'),
            'these tests cover the native backend; load the ordered_json extension',
        );
        // The extension looks the value class up without autoloading it.
        self::assertTrue(class_exists(Value::class));
    }

    public function testHydrateObjectMembers(): void
    {
        $members = ordered_json_hydrate(self::SOURCE, self::tape(), 0);
        self::assertSame(['aa', 'b'], array_keys($members));
        self::assertSame(['1', '[2,3]'], self::tokens($members));
    }

    public function testHydrateArrayItems(): void
    {
        self::assertSame(
            ['2', '3'],
            self::tokens(ordered_json_hydrate(self::SOURCE, self::tape(), self::firstRecord(self::tape(), 2))),
        );
    }

    public function testEscapedMemberNameDecodes(): void
    {
        $escaped = '{"aé🌍":1}';
        $members = ordered_json_hydrate($escaped, ordered_json_scan($escaped), 0);
        self::assertSame(["a\u{e9}\u{1f30d}"], array_keys($members));
    }

    public function testUnpairedSurrogateMemberNameKeepsWtf8Identity(): void
    {
        $lone = '{"a\ud800":1}';
        $members = ordered_json_hydrate($lone, ordered_json_scan($lone), 0);
        self::assertSame(["a\xed\xa0\x80"], array_keys($members));
    }

    public function testHydrateRejectsMalformedDescriptors(): void
    {
        $tape = self::tape();
        $malformed = [
            'negative index' => [self::SOURCE, $tape, -1],
            'index past the tape' => [self::SOURCE, $tape, 999],
            'scalar record' => [self::SOURCE, $tape, 6],
            'link past the tape' => [self::SOURCE, array_replace($tape, [0 => ($tape[0] & 0xff) | (9999 << 8)]), 0],
            'key span past the source' => [self::SOURCE, array_replace($tape, [4 => 9999]), 0],
            'member value before its key' => [self::SOURCE, array_replace($tape, [3 => $tape[3] & 0xff]), 0],
            'truncated escape' => ['{"a\u00":1}', [1 | (9 << 8), 0, 10, 3 | 16 | (6 << 8), 1, 9, 4 | 8, 10, 11], 0],
            'empty tape' => [self::SOURCE, [], 0],
        ];
        foreach ($malformed as $name => $arguments) {
            self::expectThrown(ValueError::class, static fn() => ordered_json_hydrate(...$arguments), $name);
        }
    }

    public function testCompactNodeRejectsMismatchedDescriptors(): void
    {
        self::expectThrown(
            ValueError::class,
            static fn() => ordered_json_compact_node(self::SOURCE, array_replace(self::tape(), [2 => 9999]), 0),
        );
        self::expectThrown(ValueError::class, static fn() => ordered_json_compact_node(self::SOURCE, self::tape(), -1));
    }

    public function testCompactNodeCopiesACompactToken(): void
    {
        self::assertSame(
            '[2,3]',
            ordered_json_compact_node(self::SOURCE, self::tape(), self::firstRecord(self::tape(), 2)),
        );
        self::assertSame(self::SOURCE, ordered_json_compact_node(self::SOURCE, self::tape(), 0));
    }

    public function testScanRejectsDepthOutsideTheRange(): void
    {
        self::expectThrown(ValueError::class, static fn() => ordered_json_scan('[]', -1));
        self::expectThrown(ValueError::class, static fn() => ordered_json_scan('[]', 257));
    }

    public function testScanReportsTheParseErrorOffset(): void
    {
        try {
            ordered_json_scan('[1,]');
        } catch (NativeParseError $error) {
            self::assertSame(3, $error->offset);
            return;
        }
        self::fail('expected Polyspec\OrderedJson\NativeParseError');
    }

    /** @return list<int> The descriptor tape of SOURCE. */
    private static function tape(): array
    {
        return ordered_json_scan(self::SOURCE);
    }

    /** Index of the first record of the given kind, so tests do not hard-code tape offsets. */
    private static function firstRecord(array $tape, int $kind): int
    {
        for ($index = 0; $index < count($tape); $index += 3) {
            if (($tape[$index] & 7) === $kind) {
                return $index;
            }
        }
        self::fail('no record of kind ' . $kind);
    }

    /** @return list<string> Raw tokens of hydrated children. */
    private static function tokens(array $children): array
    {
        return array_values(array_map(static fn($child) => $child->raw(), $children));
    }

    /** Runs $body and requires an error of $class. */
    private static function expectThrown(string $class, callable $body, string $name = ''): void
    {
        try {
            $body();
        } catch (Throwable $error) {
            self::assertInstanceOf($class, $error, $name . ': ' . get_class($error) . ': ' . $error->getMessage());
            return;
        }
        self::fail(($name === '' ? '' : $name . ': ') . 'expected ' . $class . ', no error was raised');
    }
}
