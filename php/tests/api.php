<?php
// Package tests for the PHP value API. The shared cases exercise the JSON
// contract through the adapter; accessor errors, UTF-16 units, factory
// arguments and the PCRE limits below are reachable only from here.
declare(strict_types=1);

require dirname(__DIR__) . '/src/OrderedJson.php';

use OrderedJson\ParseError;
use OrderedJson\Value;

$failures = [];

function check(array &$failures, string $name, callable $body): void
{
    try {
        $body();
    } catch (Throwable $error) {
        $failures[] = $name . ': ' . get_class($error) . ': ' . $error->getMessage();
    }
}

function expectThrows(string $class, string $message, callable $body): void
{
    try {
        $body();
    } catch (Throwable $error) {
        if (!($error instanceof $class))
            throw new RuntimeException('expected ' . $class . ', got ' . get_class($error) . ': ' . $error->getMessage());
        if ($message !== '' && !str_contains($error->getMessage(), $message))
            throw new RuntimeException('expected message containing ' . json_encode($message) . ', got ' . json_encode($error->getMessage()));
        return;
    }
    throw new RuntimeException('expected ' . $class . ', no error was raised');
}

function expectSame(mixed $expected, mixed $actual): void
{
    if ($expected !== $actual)
        throw new RuntimeException('expected ' . json_encode($expected) . ', got ' . json_encode($actual));
}

check($failures, 'the pure implementation runs without the extension', static function () {
    if (extension_loaded('ordered_json'))
        throw new RuntimeException('these tests cover the pure PHP path; run them with php -n');
});

check($failures, 'parse rejects a depth outside the supported range', static function () {
    expectThrows(InvalidArgumentException::class, 'maxDepth', static fn() => Value::parse('[]', -1));
    expectThrows(InvalidArgumentException::class, 'maxDepth', static fn() => Value::parse('[]', 257));
});

check($failures, 'wrong-kind access names both kinds', static function () {
    expectThrows(LogicException::class, 'Expected object, got array', static fn() => Value::parse('[]')->members());
    expectThrows(LogicException::class, 'Expected array, got object', static fn() => Value::parse('{}')->items());
    expectThrows(LogicException::class, 'Expected string, got number', static fn() => Value::parse('1')->stringValue());
    expectThrows(LogicException::class, 'Expected number, got string', static fn() => Value::parse('"a"')->numberLiteral());
    expectThrows(LogicException::class, 'Expected boolean, got null', static fn() => Value::parse('null')->booleanValue());
    expectThrows(LogicException::class, 'Expected object, got array', static fn() => Value::parse('[]')->get('a'));
});

check($failures, 'string units keep escaped unpaired surrogates', static function () {
    $lone = Value::parse('"a\ud800"');
    expectSame([0x61, 0xd800], $lone->stringUnits());
    expectThrows(UnexpectedValueException::class, 'stringUnits', static fn() => $lone->stringValue());
    expectSame([0xd83c, 0xdf0d], Value::parse('"\ud83c\udf0d"')->stringUnits());
    expectSame("\u{1f30d}", Value::parse('"\ud83c\udf0d"')->stringValue());
});

check($failures, 'member lookup uses decoded names', static function () {
    $value = Value::parse('{"a\u00e9":1,"b":2}');
    expectSame('1', $value->get("a\u{e9}")->raw());
    expectSame(null, $value->get('missing'));
    expectSame('2', $value->getUnits([0x62])->raw());
    expectSame(null, $value->getUnits([0x63]));
});

check($failures, 'a repeated key keeps its first position and last value', static function () {
    $members = Value::parse('{"a":1,"b":2,"a":3}')->members();
    expectSame(['a', 'b'], array_keys($members));
    expectSame('3', $members['a']->raw());
});

check($failures, 'the root raw text includes surrounding whitespace', static function () {
    expectSame("  [1] \n", Value::parse("  [1] \n")->raw());
    expectSame('[1]', Value::parse("  [1] \n")->compact());
});

check($failures, 'factories validate their arguments', static function () {
    expectThrows(InvalidArgumentException::class, 'UTF-16 code units', static fn() => Value::fromUnits([65536]));
    expectThrows(InvalidArgumentException::class, 'UTF-16 code units', static fn() => Value::fromUnits(['a']));
    expectThrows(InvalidArgumentException::class, 'without whitespace', static fn() => Value::number(' 1'));
    expectThrows(InvalidArgumentException::class, 'list of values', static fn() => Value::array(['k' => Value::null()]));
    expectSame('"\ud800"', Value::fromUnits([0xd800])->compact());
    expectSame('{"a":1}', Value::object(['a' => Value::number('1')])->compact());
});

check($failures, 'serialization boundaries stay explicit', static function () {
    expectThrows(LogicException::class, 'OrderedJson\\stringify', static fn() => json_encode(Value::parse('[1]')));
    expectSame('[1]', (string)Value::parse('[1]'));
});

check($failures, 'parse errors report a byte offset', static function () {
    try {
        Value::parse('[1,]');
    } catch (ParseError $error) {
        expectSame(3, $error->offset);
        return;
    }
    throw new RuntimeException('expected ParseError');
});

// A backtrack or recursion limit must not be read as invalid UTF-8; only a
// UTF-8 error is one. Low limits are the configuration that caught this.
check($failures, 'UTF-8 validation survives low PCRE limits', static function () {
    $backtrack = ini_get('pcre.backtrack_limit');
    $recursion = ini_get('pcre.recursion_limit');
    ini_set('pcre.backtrack_limit', '1');
    ini_set('pcre.recursion_limit', '1');
    try {
        $document = '{"key":"' . str_repeat("\u{d55c}\u{1f30d}", 64) . '"}';
        expectSame(str_repeat("\u{d55c}\u{1f30d}", 64), Value::parse($document)->get('key')->stringValue());
        try {
            Value::parse("[\"\xff\"]");
            throw new RuntimeException('expected ParseError for invalid UTF-8');
        } catch (ParseError $error) {
            expectSame('Invalid UTF-8 at byte 0', $error->getMessage());
            expectSame(0, $error->offset);
        }
    } finally {
        ini_set('pcre.backtrack_limit', (string)$backtrack);
        ini_set('pcre.recursion_limit', (string)$recursion);
    }
});

if ($failures) {
    fwrite(STDERR, implode(PHP_EOL, $failures) . PHP_EOL);
    exit(1);
}
