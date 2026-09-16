<?php
// Reports the public API of the package, one symbol per line. A function or
// method marked @internal is part of the implementation, not the surface.
declare(strict_types=1);

require dirname(__DIR__) . '/src/OrderedJson.php';

$native = in_array('--native', $argv, true);
if ($native !== extension_loaded('ordered_json')) {
    fwrite(STDERR, 'The reported surface depends on the backend; load the extension for --native' . PHP_EOL);
    exit(1);
}

/** Whether a docblock marks the element as implementation detail. */
function internal(string|false $doc): bool
{
    return $doc !== false && str_contains($doc, '@internal');
}

$symbols = [];
if ($native) {
    foreach (get_extension_funcs('ordered_json') as $name) $symbols[] = $name;
    $symbols[] = 'ORDERED_JSON_VERSION';
    $symbols[] = 'OrderedJsonNativeParseError';
} else {
    foreach (['OrderedJson\\Value', 'OrderedJson\\ParseError'] as $class) {
        $reflection = new ReflectionClass($class);
        $symbols[] = $reflection->getShortName();
        foreach ($reflection->getMethods(ReflectionMethod::IS_PUBLIC) as $method) {
            if ($method->getDeclaringClass()->getName() !== $class || internal($method->getDocComment())) continue;
            if ($method->getName() === '__construct' && !$method->isPublic()) continue;
            $symbols[] = $reflection->getShortName() . '.' . $method->getName();
        }
    }
    foreach (get_defined_functions()['user'] as $name) {
        if (!str_starts_with($name, 'orderedjson\\')) continue;
        if (internal((new ReflectionFunction($name))->getDocComment())) continue;
        $symbols[] = substr($name, strlen('orderedjson\\'));
    }
    $symbols[] = 'MAX_DEPTH';
}
sort($symbols);
echo implode(PHP_EOL, array_values(array_unique($symbols))), PHP_EOL;
