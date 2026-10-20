<?php

declare(strict_types=1);

require dirname(__DIR__) . '/vendor/autoload.php';

use Polyspec\OrderedJson\ParseError;
use Polyspec\OrderedJson\Tests\ProbeTree;
use Polyspec\OrderedJson\Value;

use function Polyspec\OrderedJson\parse;
use function Polyspec\OrderedJson\stringify;

$expectNative = in_array('--native', $argv, true);
if ($expectNative !== extension_loaded('polyspec_ordered_json')) {
    throw new RuntimeException('Unexpected PHP parser backend');
}

// No test cases or expectations here; the common verifier supplies documents.
while (($line = fgets(STDIN)) !== false) {
    $source = file_get_contents(rtrim($line, "\r\n"));
    if ($source === false) {
        throw new RuntimeException('Cannot read document');
    }
    try {
        $value = parse($source);
    } catch (ParseError $e) {
        echo '{"ok":false,"offset":', $e->offset, ',"unit":"byte","kind":', ProbeTree::quote($e->kind), '}', "\n";
        continue;
    }
    $serialized = stringify($value);
    $roundtrip = parse($serialized);
    $factory = Value::string("quote \" slash \\ line\n 한 🌍")->compact();
    echo '{"ok":true',
        ',"raw":', ProbeTree::quote($value->raw()),
        ',"serialized":', ProbeTree::quote($serialized),
        ',"compact":', ProbeTree::quote($value->compact()),
        ',"tree":', ProbeTree::tree($value),
        ',"roundtrip":', ProbeTree::quote(stringify($roundtrip)),
        ',"roundtrip_tree":', ProbeTree::tree($roundtrip),
        ',"rebuilt":', ProbeTree::quote(ProbeTree::rebuild($value)->compact()),
        ',"factory":', ProbeTree::quote($factory),
        "}\n";
}
