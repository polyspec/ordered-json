<?php
declare(strict_types=1);
require dirname(__DIR__) . '/src/OrderedJson.php';
use OrderedJson\{Value, ParseError};
use function OrderedJson\parse;

$expectNative = in_array('--native', $argv, true);
if ($expectNative !== extension_loaded('ordered_json')) {
    throw new RuntimeException('Unexpected PHP parser backend');
}

// No test cases or expectations here; the common verifier supplies documents.
function quote(string $s): string { return json_encode($s, JSON_THROW_ON_ERROR); }
function text(Value $v): string { return Value::fromUnits($v->stringUnits())->raw(); }
function objectTree(Value $v): string {
    $parts = [];
    foreach ($v->members() as $key => $value)
        $parts[] = '['.OrderedJson\quoteKey((string)$key).','.tree($value).']';
    return '["object",['.implode(',', $parts).']]';
}
function tree(Value $v): string {
    return match ($v->kind()) {
        'object' => objectTree($v),
        'array' => '["array",['.implode(',', array_map(tree(...), $v->items())).']]',
        'string' => '["string",'.text($v).']',
        'number' => '["number",'.quote($v->numberLiteral()).']',
        'boolean' => '["boolean",'.($v->booleanValue() ? 'true':'false').']',
        default => '["null"]',
    };
}
function rebuild(Value $v): Value {
    if ($v->kind() === 'object') {
        $members = [];
        foreach ($v->members() as $key => $_) $members[$key] = Value::null();
        foreach (array_reverse(array_keys($members)) as $key) $members[$key] = rebuild($v->get((string)$key));
        return Value::object($members);
    }
    return match ($v->kind()) {
        'array' => Value::array(array_map(rebuild(...), $v->items())),
        default => $v,
    };
}
while (($line = fgets(STDIN)) !== false) {
    $source = file_get_contents(rtrim($line, "\r\n"));
    if ($source === false) throw new RuntimeException('Cannot read document');
    try { $value = parse($source); }
    catch (ParseError $e) { echo '{"ok":false}', "\n"; continue; }
    echo '{"ok":true,"raw":',quote($value->raw()),',"serialized":',quote(OrderedJson\stringify($value)),',"compact":',quote($value->compact()),
        ',"tree":',tree($value),',"rebuilt":',quote(rebuild($value)->compact()),"}\n";
}
