<?php

declare(strict_types=1);

namespace Polyspec\OrderedJson\Extension\Tests;

use Polyspec\OrderedJson\Tests\OfficialTestCase;

/**
 * The official examples on the native backend: the cases of OfficialTestCase of packages/php with the
 * polyspec_ordered_json extension.
 * Requirements: RQ-022
 */
final class OfficialTest extends OfficialTestCase
{
    protected function setUp(): void
    {
        self::assertTrue(
            extension_loaded('polyspec_ordered_json'),
            'these tests cover the native backend; load the polyspec_ordered_json extension',
        );
    }
}
