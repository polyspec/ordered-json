<?php

declare(strict_types=1);

namespace Polyspec\OrderedJson;

const MAX_DEPTH = 256;

function parse(string $source, int $maxDepth = MAX_DEPTH): Value
{
    return Value::parse($source, $maxDepth);
}
function stringify(Value $value): string
{
    return $value->compact();
}
