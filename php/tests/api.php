<?php
// Package tests for the pure PHP backend. Case ids come from package-tests.json.
declare(strict_types=1);

require dirname(__DIR__) . '/src/OrderedJson.php';
require __DIR__ . '/api_checks.php';

if (in_array('--cases', $argv, true)) {
    $standard = json_decode(file_get_contents(dirname(__DIR__, 2) . '/package-tests.json'), true,  flags: JSON_THROW_ON_ERROR);
    $cases = array_merge(
        array_filter($standard['cases'], static fn(array $case): bool => !isset($case['exemptions']['php'])),
        $standard['package_cases']['php']
    );
    echo implode(PHP_EOL, array_column($cases, 'id')) . PHP_EOL;
    exit(0);
}

if (in_array('--cases', $argv, true)) {
    echo implode(PHP_EOL, array_keys(orderedJsonApiCases())), PHP_EOL;
    exit(0);
}

if (extension_loaded('ordered_json')) {
    fwrite(STDERR, 'These checks cover the pure PHP path; run them with php -n' . PHP_EOL);
    exit(1);
}

$failures = orderedJsonApiChecks();
if ($failures) {
    fwrite(STDERR, implode(PHP_EOL, $failures) . PHP_EOL);
    exit(1);
}
