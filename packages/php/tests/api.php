<?php
// Package tests for the pure PHP backend.
declare(strict_types=1);

require dirname(__DIR__) . '/src/OrderedJson.php';
require __DIR__ . '/api_checks.php';

if (extension_loaded('ordered_json')) {
    fwrite(STDERR, 'These checks cover the pure PHP path; run them with php -n' . PHP_EOL);
    exit(1);
}

$failures = orderedJsonApiChecks();
if ($failures) {
    fwrite(STDERR, implode(PHP_EOL, $failures) . PHP_EOL);
    exit(1);
}
