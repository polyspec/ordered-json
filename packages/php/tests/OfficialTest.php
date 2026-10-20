<?php

declare(strict_types=1);

namespace Polyspec\OrderedJson\Tests;

/** The official examples on the pure PHP backend: the cases of OfficialTestCase without the polyspec_ordered_json extension. */
final class OfficialTest extends OfficialTestCase
{
    protected function setUp(): void
    {
        self::assertFalse(
            extension_loaded('polyspec_ordered_json'),
            'these tests cover the pure PHP backend; run them without the polyspec_ordered_json extension',
        );
    }
}
