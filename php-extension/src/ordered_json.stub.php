<?php
/** Native descriptors are tapes of three integers per value: meta, start and end. */
function ordered_json_scan(string $source, int $maxDepth = 256): array {}
function ordered_json_compact(string $source, int $maxDepth = 256): string {}
function ordered_json_compact_node(string $source, array $node, int $index = 0): string {}
