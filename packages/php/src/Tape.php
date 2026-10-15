<?php

declare(strict_types=1);

namespace Polyspec\OrderedJson;

/**
 * @internal Descriptor tape layout shared with the C extension. Each value has three
 * integers in document order: meta, start and end. meta = kind | flags | link << LINK.
 * A container links past its subtree; an object key links to the value of its member.
 */
final class Tape
{
    public const OBJECT = 1;
    public const ARRAY = 2;
    public const STRING = 3;
    public const NUMBER = 4;
    public const BOOLEAN = 5;
    public const NULL = 6;
    public const KIND = 7;
    public const KINDS = [self::OBJECT => 'object', self::ARRAY => 'array', self::STRING => 'string',
        self::NUMBER => 'number', self::BOOLEAN => 'boolean', self::NULL => 'null'];
    /** The value serializes to exactly its source token. */
    public const COMPACT = 8;
    /** The string token contains escape sequences. */
    public const ESCAPED = 16;
    /** A repeated object key; the first key of that name links to the final value. */
    public const SKIP = 32;
    public const LINK = 8;
}
