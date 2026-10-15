<?php

declare(strict_types=1);

namespace Polyspec\OrderedJson\Tests;

/** The official examples on the pure PHP backend: the cases of OfficialTestCase without the ordered_json extension. */
final class OfficialTest extends OfficialTestCase
{
    protected function setUp(): void
    {
        self::assertFalse(
            extension_loaded('ordered_json'),
            'these tests cover the pure PHP backend; run them without the ordered_json extension',
        );
    }
}
