<?php

declare(strict_types=1);

namespace Polyspec\OrderedJson\Tests;

use Polyspec\OrderedJson\Value;

use function Polyspec\OrderedJson\quoteKey;

/**
 * The serializations of the probe of the common verifier (probe.php): the JSON text of a string, the value tree of a
 * parsed value and the value rebuilt through the factories. The probe holds no test cases or expectations; the common
 * verifier supplies the documents.
 */
final class ProbeTree
{
    public static function quote(string $s): string
    {
        return json_encode($s, JSON_THROW_ON_ERROR);
    }

    public static function text(Value $v): string
    {
        return Value::fromUnits($v->stringUnits())->raw();
    }

    public static function tree(Value $v): string
    {
        return match ($v->kind()) {
            'object' => self::objectTree($v),
            'array' => '["array",[' . implode(',', array_map(self::tree(...), $v->items())) . ']]',
            'string' => '["string",' . self::text($v) . ']',
            'number' => '["number",' . self::quote($v->numberLiteral()) . ']',
            'boolean' => '["boolean",' . ($v->booleanValue() ? 'true' : 'false') . ']',
            default => '["null"]',
        };
    }

    public static function rebuild(Value $v): Value
    {
        if ($v->kind() === 'object') {
            $members = [];
            foreach ($v->members() as $key => $_) {
                $members[$key] = Value::null();
            }
            foreach (array_reverse(array_keys($members)) as $key) {
                $members[$key] = self::rebuild($v->get((string)$key));
            }
            return Value::object($members);
        }
        return match ($v->kind()) {
            'array' => Value::array(array_map(self::rebuild(...), $v->items())),
            default => $v,
        };
    }

    private static function objectTree(Value $v): string
    {
        $parts = [];
        foreach ($v->members() as $key => $value) {
            $parts[] = '[' . quoteKey((string)$key) . ',' . self::tree($value) . ']';
        }
        return '["object",[' . implode(',', $parts) . ']]';
    }
}
