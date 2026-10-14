<?php
declare(strict_types=1);

namespace Polyspec\OrderedJson\Tests;

use InvalidArgumentException;
use LogicException;
use PHPUnit\Framework\TestCase;
use Polyspec\OrderedJson\ParseError;
use Polyspec\OrderedJson\Value;
use Throwable;
use TypeError;
use UnexpectedValueException;

/**
 * The value API of both PHP backends, run by PHPUnit; each test method is a feature unit of config/parity.json. The pure
 * library and the extension must answer identically, so ValueApiTest of this package runs these tests without the
 * extension and ValueApiTest of packages/php-ext with it.
 */
abstract class ValueApiTestCase extends TestCase
{

    /** Runs $body and requires an error of $class whose message contains $message. */
    private static function expectThrown(string $class, string $message, callable $body): void
    {
        try {
            $body();
        } catch (Throwable $error) {
            self::assertInstanceOf($class, $error, get_class($error) . ': ' . $error->getMessage());
            if ($message !== '') {
                self::assertStringContainsString($message, $error->getMessage());
            }
            return;
        }
        self::fail('expected ' . $class . ', no error was raised');
    }

    public function testDepthArgumentIsBounded(): void
    {
        self::expectThrown(InvalidArgumentException::class, 'maxDepth', static fn() => Value::parse('[]', -1));
        self::expectThrown(InvalidArgumentException::class, 'maxDepth', static fn() => Value::parse('[]', 257));
    }

    public function testDepthLimitIsEnforced(): void
    {
        self::assertSame(1, count(Value::parse('[[1]]', 2)->items()));
        self::expectThrown(ParseError::class, 'Maximum nesting depth', static fn() => Value::parse('[[1]]', 1));
    }

    public function testValuesComeOnlyFromTheLibrary(): void
    {
        self::expectThrown(\Error::class, '', static fn() => new Value());
        self::expectThrown(TypeError::class, '', static fn() => \Polyspec\OrderedJson\stringify(new \stdClass()));
    }

    public function testReturnedCollectionsAreImmutable(): void
    {
        $value = Value::parse('{"a":1,"b":2}');
        $members = $value->members();
        unset($members['a']);
        self::assertSame(2, count($value->members()));
        $array = Value::parse('[1,2]');
        $items = $array->items();
        array_pop($items);
        self::assertSame(2, count($array->items()));
    }

    public function testWrongKindAccessIsReported(): void
    {
        self::expectThrown(LogicException::class, 'Expected object, got array', static fn() => Value::parse('[]')->members());
        self::expectThrown(LogicException::class, 'Expected array, got object', static fn() => Value::parse('{}')->items());
        self::expectThrown(LogicException::class, 'Expected string, got number', static fn() => Value::parse('1')->stringValue());
        self::expectThrown(LogicException::class, 'Expected number, got string', static fn() => Value::parse('"a"')->numberLiteral());
        self::expectThrown(LogicException::class, 'Expected boolean, got null', static fn() => Value::parse('null')->booleanValue());
        self::expectThrown(LogicException::class, 'Expected object, got array', static fn() => Value::parse('[]')->get('a'));
    }

    public function testUnpairedSurrogateStaysInUnits(): void
    {
        $lone = Value::parse('"a\ud800"');
        self::assertSame([0x61, 0xd800], $lone->stringUnits());
        self::expectThrown(UnexpectedValueException::class, 'stringUnits', static fn() => $lone->stringValue());
    }

    public function testSurrogatePairDecodes(): void
    {
        self::assertSame([0xd83c, 0xdf0d], Value::parse('"\ud83c\udf0d"')->stringUnits());
        self::assertSame("\u{1f30d}", Value::parse('"\ud83c\udf0d"')->stringValue());
    }

    public function testMemberLookupUsesDecodedNames(): void
    {
        $value = Value::parse('{"a\u00e9":1,"b":2}');
        self::assertSame('1', $value->get("a\u{e9}")->raw());
        self::assertSame(null, $value->get('missing'));
        self::assertSame('2', $value->getUnits([0x62])->raw());
        self::assertSame(null, $value->getUnits([0x63]));
    }

    public function testRepeatedKeyKeepsFirstPositionAndLastValue(): void
    {
        $members = Value::parse('{"a":1,"b":2,"a":3}')->members();
        self::assertSame(['a', 'b'], array_keys($members));
        self::assertSame('3', $members['a']->raw());
    }

    public function testRootKeepsSurroundingText(): void
    {
        self::assertSame("  [1] \n", Value::parse("  [1] \n")->raw());
        self::assertSame('[1]', Value::parse("  [1] \n")->compact());
    }

    public function testFactoriesValidateArguments(): void
    {
        self::expectThrown(InvalidArgumentException::class, 'UTF-16 code units', static fn() => Value::fromUnits([65536]));
        self::expectThrown(InvalidArgumentException::class, 'UTF-16 code units', static fn() => Value::fromUnits(['a']));
        self::expectThrown(InvalidArgumentException::class, 'without whitespace', static fn() => Value::number(' 1'));
        self::expectThrown(InvalidArgumentException::class, 'list of values', static fn() => Value::array(['k' => Value::null()]));
        self::assertSame('"\ud800"', Value::fromUnits([0xd800])->compact());
        self::assertSame('{"a":1}', Value::object(['a' => Value::number('1')])->compact());
    }

    public function testHostSerializationBoundary(): void
    {
        self::expectThrown(LogicException::class, 'Polyspec\\OrderedJson\\stringify', static fn() => json_encode(Value::parse('[1]')));
        self::assertSame('[1]', (string)Value::parse('[1]'));
    }

    public function testRejectionNamesItsKind(): void
    {
        // The wording is PHP's own; the kind is the shared contract.
        $kinds = [
            '[1,]' => 'expected_value',
            '{1:2}' => 'expected_object_key',
            '[1.]' => 'expected_digit',
            "\"a\x01b\"" => 'unescaped_control_character',
            '[1] x' => 'trailing_input',
        ];
        foreach ($kinds as $document => $kind) {
            try {
                Value::parse($document);
            } catch (ParseError $error) {
                self::assertSame($kind, $error->kind);
                continue;
            }
            self::fail('accepted ' . $document);
        }
    }

    public function testInvalidUtf8ReportsTheFirstBadByte(): void
    {
        // The bad byte sits at index 2 of ["<bad>"]; the error names that position.
        try {
            Value::parse("[\"\xff\"]");
        } catch (ParseError $error) {
            self::assertSame('Invalid UTF-8', substr($error->getMessage(), 0, 13));
            self::assertSame(2, $error->offset);
            return;
        }
        self::fail('expected ParseError for invalid UTF-8');
    }

    public function testParseErrorsReportOffsets(): void
    {
        try {
            Value::parse('[1,]');
        } catch (ParseError $error) {
            self::assertSame(3, $error->offset);
            return;
        }
        self::fail('expected ParseError');
    }

    public function testStrictParseRejectsDuplicateKeys(): void
    {
        $sources = [
            '{"a":1,"a":2}',
            '{"a":1,"\u0061":2}',
            '{"nested":{"a":1,"a":2}}',
            '[{"a":1,"a":2}]',
            '{"\ud800":1,"\ud800":2}',
        ];
        foreach ($sources as $source) {
            Value::parse($source);
            $offset = strrpos($source, ',"') + 1;
            try {
                Value::parseRejectDuplicates($source);
            } catch (ParseError $error) {
                self::assertSame('Duplicate object key at byte ' . $offset, $error->getMessage());
                self::assertSame('duplicate_object_key', $error->kind);
                self::assertSame($offset, $error->offset);
                continue;
            }
            self::fail('accepted ' . $source);
        }
    }

    public function testStrictParseAcceptsUniqueKeys(): void
    {
        $source = '{"a":1,"nested":[{"b":2}],"state":null}';
        self::assertSame($source, Value::parseRejectDuplicates($source)->compact());
        self::assertSame('2', Value::parseRejectDuplicates($source)->get('nested')->items()[0]->get('b')->raw());
        try {
            Value::parseRejectDuplicates("\xff");
        } catch (ParseError $error) {
            self::assertSame('Invalid UTF-8 at byte 0', $error->getMessage());
            self::assertSame(0, $error->offset);
            return;
        }
        self::fail('expected ParseError for invalid UTF-8');
    }

    // Long multibyte text is valid UTF-8 and only a UTF-8 error is invalid. PHP validates with PCRE, whose backtrack or
    // recursion limit must not be read as invalid UTF-8; low limits are the configuration that caught this.
    public function testUtf8ValidationHoldsForLongMultibyteText(): void
    {
        $backtrack = ini_get('pcre.backtrack_limit');
        $recursion = ini_get('pcre.recursion_limit');
        ini_set('pcre.backtrack_limit', '1');
        ini_set('pcre.recursion_limit', '1');
        try {
            $document = '{"key":"' . str_repeat("\u{d55c}\u{1f30d}", 64) . '"}';
            self::assertSame(str_repeat("\u{d55c}\u{1f30d}", 64), Value::parse($document)->get('key')->stringValue());
            try {
                Value::parse("[\"\xff\"]");
                self::fail('expected ParseError for invalid UTF-8');
            } catch (ParseError $error) {
                self::assertSame('Invalid UTF-8 at byte 2', $error->getMessage());
                self::assertSame(2, $error->offset);
            }
        } finally {
            ini_set('pcre.backtrack_limit', (string)$backtrack);
            ini_set('pcre.recursion_limit', (string)$recursion);
        }
    }
}
