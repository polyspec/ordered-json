<?php
declare(strict_types=1);

namespace Polyspec\OrderedJson\Extension\Tests;

use Polyspec\OrderedJson\Tests\ValueApiTestCase;

/** The value API of the native backend: the tests of ValueApiTestCase of packages/php with the ordered_json extension. */
final class ValueApiTest extends ValueApiTestCase
{
    protected function setUp(): void
    {
        self::assertTrue(extension_loaded('ordered_json'), 'these tests cover the native backend; load the ordered_json extension');
    }
}
