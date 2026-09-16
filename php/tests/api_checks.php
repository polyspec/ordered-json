<?php
// Value API checks shared by both PHP backends. The pure library and the
// extension must answer identically, so one suite runs against each.
declare(strict_types=1);

use OrderedJson\ParseError;
use OrderedJson\Value;

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

/** @return list<string> Failure descriptions; empty when every check passes. */
function orderedJsonApiCases(): array
{
    $cases = [];

    $cases['depth_argument_is_bounded'] = static function () {
        expectThrows(InvalidArgumentException::class, 'maxDepth', static fn() => Value::parse('[]', -1));
        expectThrows(InvalidArgumentException::class, 'maxDepth', static fn() => Value::parse('[]', 257));
    };

    $cases['depth_limit_is_enforced'] = static function () {
        expectSame(1, count(Value::parse('[[1]]', 2)->items()));
        expectThrows(ParseError::class, 'Maximum nesting depth', static fn() => Value::parse('[[1]]', 1));
    };

    $cases['values_come_only_from_the_library'] = static function () {
        expectThrows(Error::class, '', static fn() => new Value());
        expectThrows(TypeError::class, '', static fn() => OrderedJson\stringify(new stdClass()));
    };

    $cases['returned_collections_are_immutable'] = static function () {
        $value = Value::parse('{"a":1,"b":2}');
        $members = $value->members();
        unset($members['a']);
        expectSame(2, count($value->members()));
        $array = Value::parse('[1,2]');
        $items = $array->items();
        array_pop($items);
        expectSame(2, count($array->items()));
    };

    $cases['wrong_kind_access_is_reported'] = static function () {
        expectThrows(LogicException::class, 'Expected object, got array', static fn() => Value::parse('[]')->members());
        expectThrows(LogicException::class, 'Expected array, got object', static fn() => Value::parse('{}')->items());
        expectThrows(LogicException::class, 'Expected string, got number', static fn() => Value::parse('1')->stringValue());
        expectThrows(LogicException::class, 'Expected number, got string', static fn() => Value::parse('"a"')->numberLiteral());
        expectThrows(LogicException::class, 'Expected boolean, got null', static fn() => Value::parse('null')->booleanValue());
        expectThrows(LogicException::class, 'Expected object, got array', static fn() => Value::parse('[]')->get('a'));
    };

    $cases['unpaired_surrogate_stays_in_units'] = static function () {
        $lone = Value::parse('"a\ud800"');
        expectSame([0x61, 0xd800], $lone->stringUnits());
        expectThrows(UnexpectedValueException::class, 'stringUnits', static fn() => $lone->stringValue());
    };

    $cases['surrogate_pair_decodes'] = static function () {
        expectSame([0xd83c, 0xdf0d], Value::parse('"\ud83c\udf0d"')->stringUnits());
        expectSame("\u{1f30d}", Value::parse('"\ud83c\udf0d"')->stringValue());
    };

    $cases['member_lookup_uses_decoded_names'] = static function () {
        $value = Value::parse('{"a\u00e9":1,"b":2}');
        expectSame('1', $value->get("a\u{e9}")->raw());
        expectSame(null, $value->get('missing'));
        expectSame('2', $value->getUnits([0x62])->raw());
        expectSame(null, $value->getUnits([0x63]));
    };

    $cases['repeated_key_keeps_first_position_and_last_value'] = static function () {
        $members = Value::parse('{"a":1,"b":2,"a":3}')->members();
        expectSame(['a', 'b'], array_keys($members));
        expectSame('3', $members['a']->raw());
    };

    $cases['root_keeps_surrounding_text'] = static function () {
        expectSame("  [1] \n", Value::parse("  [1] \n")->raw());
        expectSame('[1]', Value::parse("  [1] \n")->compact());
    };

    $cases['factories_validate_arguments'] = static function () {
        expectThrows(InvalidArgumentException::class, 'UTF-16 code units', static fn() => Value::fromUnits([65536]));
        expectThrows(InvalidArgumentException::class, 'UTF-16 code units', static fn() => Value::fromUnits(['a']));
        expectThrows(InvalidArgumentException::class, 'without whitespace', static fn() => Value::number(' 1'));
        expectThrows(InvalidArgumentException::class, 'list of values', static fn() => Value::array(['k' => Value::null()]));
        expectSame('"\ud800"', Value::fromUnits([0xd800])->compact());
        expectSame('{"a":1}', Value::object(['a' => Value::number('1')])->compact());
    };

    $cases['host_serialization_boundary'] = static function () {
        expectThrows(LogicException::class, 'OrderedJson\\stringify', static fn() => json_encode(Value::parse('[1]')));
        expectSame('[1]', (string)Value::parse('[1]'));
    };

    $cases['invalid_utf8_reports_the_first_bad_byte'] = static function () {
        // The bad byte sits at index 2 of ["<bad>"]; the error names that position.
        try {
            Value::parse("[\"\xff\"]");
        } catch (ParseError $error) {
            expectSame('Invalid UTF-8', substr($error->getMessage(), 0, 13));
            expectSame(2, $error->offset);
            return;
        }
        throw new RuntimeException('expected ParseError for invalid UTF-8');
    };

    $cases['parse_errors_report_offsets'] = static function () {
        try {
            Value::parse('[1,]');
        } catch (ParseError $error) {
            expectSame(3, $error->offset);
            return;
        }
        throw new RuntimeException('expected ParseError');
    };

    // A backtrack or recursion limit must not be read as invalid UTF-8; only a
    // UTF-8 error is one. Low limits are the configuration that caught this.
    $cases['utf8_validation_survives_low_pcre_limits'] = static function () {
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
                expectSame('Invalid UTF-8 at byte 2', $error->getMessage());
                expectSame(2, $error->offset);
            }
        } finally {
            ini_set('pcre.backtrack_limit', (string)$backtrack);
            ini_set('pcre.recursion_limit', (string)$recursion);
        }
    };

    return $cases;
}

/** @return list<string> Failure descriptions; empty when every case passes. */
function orderedJsonApiChecks(): array
{
    $failures = [];
    foreach (orderedJsonApiCases() as $id => $body) check($failures, $id, $body);
    return $failures;
}
