<?php
declare(strict_types=1);
require dirname(__DIR__) . '/php/src/OrderedJson.php';

use OrderedJson\Value;

$iterations = (int)($_SERVER['OJ_BENCH_ITERATIONS'] ?? 1000);
$mode = $argv[1] ?? 'custom';
$files = array_slice($argv, 2);
$clock = static fn(): float => hrtime(true);
$digest = static fn(string $value): string => hash('sha256', $value);
$sink = null;
$measure = static function (callable $fn) use ($iterations, $clock): array {
    $start = $clock(); $result = '';
    for ($i = 0; $i < $iterations; $i++) $result = $fn();
    return [(($clock() - $start) / $iterations), $result];
};
foreach ($files as $file) {
    $source = file_get_contents($file);
    if ($source === false) throw new RuntimeException("Cannot read $file");
    $parseFn = $mode === 'native-json'
        ? static fn() => json_decode($source, false, 512, JSON_THROW_ON_ERROR)
        : static fn() => Value::parse($source, 256, $mode === 'extension');
    $stringifyFn = $mode === 'native-json'
        ? static fn($value) => json_encode($value, JSON_THROW_ON_ERROR)
        : static fn($value) => $value->compact();
    [$parseNs] = $measure(function () use ($parseFn, &$sink) { $sink = $parseFn(); return $sink; });
    $value = $parseFn();
    [$stringifyNs, $output] = $measure(fn() => $stringifyFn($value));
    [$roundtripNs, $roundtrip] = $measure(fn() => $stringifyFn($parseFn()));
    echo implode("\t", [$file, $mode, $parseNs, $stringifyNs, $roundtripNs, $digest($output), strlen($source), strlen($output)]), "\n";
}
