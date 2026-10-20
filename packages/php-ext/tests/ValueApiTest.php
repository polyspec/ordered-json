<?php

declare(strict_types=1);

namespace Polyspec\OrderedJson\Extension\Tests;

use Polyspec\OrderedJson\Tests\ValueApiTestCase;

/**
 * The value API of the native backend: the tests of ValueApiTestCase of packages/php with the polyspec_ordered_json
 * extension.
 * Requirements: RQ-001, RQ-002, RQ-004, RQ-005, RQ-006, RQ-007, RQ-008, RQ-009, RQ-012, RQ-013, RQ-014, RQ-015, RQ-017,
 * RQ-018, RQ-019, RQ-020, RQ-023, RQ-024.
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
