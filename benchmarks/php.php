<?php
declare(strict_types=1);
require dirname(__DIR__) . '/php/src/OrderedJson.php';

use OrderedJson\Value;

$iterations = (int)($_SERVER['OJ_BENCH_ITERATIONS'] ?? 1000);
$warmup = (int)($_SERVER['OJ_BENCH_WARMUP'] ?? 1000);
$samples = (int)($_SERVER['OJ_BENCH_SAMPLES'] ?? 9);
$mode = $argv[1] ?? 'custom';
$files = array_slice($argv, 2);
$clock = static fn(): float => hrtime(true);
$digest = static fn(string $value): string => hash('sha256', $value);
$sink = null;
$percentile = static function (array $values, float $p): float {
    sort($values, SORT_NUMERIC);
    return $values[min(count($values) - 1, (int)ceil(count($values) * $p) - 1)];
};
$measure = static function (callable $fn) use ($iterations, $warmup, $samples, $clock, $percentile): array {
    for ($i = 0; $i < $warmup; $i++) $fn();
    $values = []; $result = '';
    for ($sample = 0; $sample < $samples; $sample++) {
        $start = $clock();
        for ($i = 0; $i < $iterations; $i++) $result = $fn();
        $values[] = ($clock() - $start) / $iterations;
    }
    sort($values, SORT_NUMERIC);
    return [['median' => $values[(int)floor(count($values) / 2)], 'p95' => $percentile($values, 0.95), 'samples' => $values], $result];
};
foreach ($files as $file) {
    $source = file_get_contents($file);
    if ($source === false) throw new RuntimeException("Cannot read $file");
    $parseFn = $mode === 'native-json'
        ? static fn() => json_decode($source, false, 512, JSON_THROW_ON_ERROR)
        : static fn() => Value::parse($source, 256);
    $stringifyFn = $mode === 'native-json'
        ? static fn($value) => json_encode($value, JSON_THROW_ON_ERROR)
        : static fn($value) => $value->compact();
    [$parseStats] = $measure(function () use ($parseFn, &$sink) { $sink = $parseFn(); return $sink; });
    $value = $parseFn();
    [$stringifyStats, $output] = $measure(fn() => $stringifyFn($value));
    [$roundtripStats] = $measure(fn() => $stringifyFn($parseFn()));
    echo implode("\t", [$file, $mode, $parseStats['median'], $stringifyStats['median'], $roundtripStats['median'],
        $parseStats['p95'], $stringifyStats['p95'], $roundtripStats['p95'],
        json_encode(['parse'=>$parseStats['samples'], 'stringify'=>$stringifyStats['samples'], 'roundtrip'=>$roundtripStats['samples']], JSON_PRESERVE_ZERO_FRACTION),
        $digest($output), strlen($source), strlen($output)]), "\n";
}
