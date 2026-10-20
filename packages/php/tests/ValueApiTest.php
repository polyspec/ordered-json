<?php

declare(strict_types=1);

namespace Polyspec\OrderedJson\Tests;

/** The value API of the pure PHP backend: the tests of ValueApiTestCase without the polyspec_ordered_json extension. */
/**
 * Requirements: RQ-001, RQ-002, RQ-004, RQ-005, RQ-006, RQ-007, RQ-009, RQ-012, RQ-013, RQ-014, RQ-015, RQ-017,
 * RQ-018, RQ-019, RQ-020, RQ-023, RQ-024.
 */
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
