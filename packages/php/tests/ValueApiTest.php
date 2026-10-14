<?php
declare(strict_types=1);

namespace Polyspec\OrderedJson\Tests;

/** The value API of the pure PHP backend: the tests of ValueApiTestCase without the ordered_json extension. */
final class ValueApiTest extends ValueApiTestCase
{
    protected function setUp(): void
    {
        self::assertFalse(extension_loaded('ordered_json'), 'these tests cover the pure PHP backend; run them without the ordered_json extension');
    }
}
