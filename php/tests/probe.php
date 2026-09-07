<?php
declare(strict_types=1);
require dirname(__DIR__) . '/src/OrderedJson.php';
use OrderedJson\{Value, Member, ParseError};
use function OrderedJson\parse;

$expectNative = in_array('--native', $argv, true);
if ($expectNative !== extension_loaded('ordered_json')) {
    throw new RuntimeException('Unexpected PHP parser backend');
}

// No test cases or expectations here; the common verifier supplies documents.
function quote(string $s): string { return json_encode($s, JSON_THROW_ON_ERROR); }
function text(Value $v): string { return Value::fromUnits($v->stringUnits())->raw(); }
function tree(Value $v): string {
    return match ($v->kind()) {
        'object' => '["object",['.implode(',', array_map(
            fn(Member $m) => '['.text($m->key).','.tree($m->value).']', $v->members())).']]',
        'array' => '["array",['.implode(',', array_map(tree(...), $v->items())).']]',
        'string' => '["string",'.text($v).']',
        'number' => '["number",'.quote($v->numberLiteral()).']',
        'boolean' => '["boolean",'.($v->booleanValue() ? 'true':'false').']',
        default => '["null"]',
    };
}
function rebuild(Value $v): Value {
    return match ($v->kind()) {
        'object' => Value::object(array_map(fn(Member $m) => new Member($m->key, rebuild($m->value)), $v->members())),
        'array' => Value::array(array_map(rebuild(...), $v->items())),
        default => $v,
    };
}
while (($line = fgets(STDIN)) !== false) {
    $source = file_get_contents(rtrim($line, "\r\n"));
    if ($source === false) throw new RuntimeException('Cannot read document');
    try { $value = parse($source); }
    catch (ParseError $e) { echo '{"ok":false}', "\n"; continue; }
    echo '{"ok":true,"raw":',quote($value->raw()),',"compact":',quote($value->compact()),
        ',"tree":',tree($value),',"rebuilt":',quote(rebuild($value)->compact()),"}\n";
}
