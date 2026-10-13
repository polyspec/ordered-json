<?php
// One parse of the document of argv[1] with the pure PHP package of this checkout; prints the CPU seconds of the parse
// (user and system time of getrusage). benchmarks/python-parse/run.py starts it with php -n.
declare(strict_types=1);

require dirname(__DIR__, 2) . '/packages/ordered-json-php/src/OrderedJson.php';

function cpuSeconds(): float
{
    $usage = getrusage();
    return $usage['ru_utime.tv_sec'] + $usage['ru_utime.tv_usec'] / 1e6 + $usage['ru_stime.tv_sec'] + $usage['ru_stime.tv_usec'] / 1e6;
}

$data = file_get_contents($argv[1]);
$started = cpuSeconds();
$value = Polyspec\OrderedJson\parse($data);
$elapsed = cpuSeconds() - $started;
if (count($value->items()) !== (int) $argv[2]) {
    fwrite(STDERR, 'parsed ' . count($value->items()) . ' items, not ' . $argv[2] . PHP_EOL);
    exit(1);
}
printf("%.6f\n", $elapsed);
