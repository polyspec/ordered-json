<?php

declare(strict_types=1);

// The extension polyspec_ordered_json registers the constant and the functions of OrderedJson.php with the classes of
// the library, so the library declares them only without it. Composer loads this file with its autoloader.
if (!extension_loaded('polyspec_ordered_json')) {
    require __DIR__ . '/OrderedJson.php';
}
