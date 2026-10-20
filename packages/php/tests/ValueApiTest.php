<?php

declare(strict_types=1);

namespace Polyspec\OrderedJson\Tests;

/** The value API of the pure PHP backend: the tests of ValueApiTestCase without the polyspec_ordered_json extension. */
final class ValueApiTest extends ValueApiTestCase
{
    protected function setUp(): void
    {
        self::assertFalse(
            extension_loaded('polyspec_ordered_json'),
            'these tests cover the pure PHP backend; run them without the polyspec_ordered_json extension',
        );
    }
}
