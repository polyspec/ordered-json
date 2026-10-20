<?php

declare(strict_types=1);

namespace Polyspec\OrderedJson\Extension\Tests;

use Error;
use PHPUnit\Framework\TestCase;

/**
 * Hydration before the library is loaded, run by PHPUnit with the extension loaded (config/parity.json, php-extension).
 * The extension looks the value class up without autoloading it, so hydration fails while no test of the run has loaded
 * the class: kit parity runs this file alone, and phpunit.xml runs it before DescriptorTest, which loads the class.
 */
final class ValueClassTest extends TestCase
{
    // Requirements: RQ-021
    public function testHydrateWithoutTheValueClass(): void
    {
        self::assertTrue(
            extension_loaded('polyspec_ordered_json'),
            'this test covers the native backend; load the polyspec_ordered_json extension',
        );
        self::assertFalse(
            class_exists('Polyspec\OrderedJson\Value', false),
            'no test of this run may load the value class first',
        );
        $this->expectException(Error::class);
        $this->expectExceptionMessage(
            'Class Polyspec\OrderedJson\Value with source, tape and index properties is not loaded',
        );
        ordered_json_hydrate('[1]', ordered_json_scan('[1]'), 0);
    }
}
