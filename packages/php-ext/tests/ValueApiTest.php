<?php

declare(strict_types=1);

namespace Polyspec\OrderedJson\Extension\Tests;

use Polyspec\OrderedJson\Tests\ValueApiTestCase;

/**
 * The value API of the native backend: the tests of ValueApiTestCase of packages/php with the polyspec_ordered_json
 * extension.
 */
final class ValueApiTest extends ValueApiTestCase
{
    protected function setUp(): void
    {
        self::assertTrue(
            extension_loaded('polyspec_ordered_json'),
            'these tests cover the native backend; load the polyspec_ordered_json extension',
        );
    }
}
