#!/usr/bin/env python3
"""The package tests of the ordered-json Python package.

Every case of the shared standard of package-tests.json runs here, and
the package cases cover the API of this binding alone. `--cases` lists
the case ids one per line.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from polyspec.ordered_json import (MAX_DEPTH, ParseError, ParseOptions, Value, parse, parse_bytes,
                                    stringify)


class StandardCases(unittest.TestCase):
    def test_depth_argument_is_bounded(self):
        for limit in (-1, MAX_DEPTH + 1, 257):
            with self.subTest(limit=limit):
                with self.assertRaises(ValueError):
                    parse('1', ParseOptions(max_depth=limit))
        parse('1', ParseOptions(max_depth=0))
        parse('[]', ParseOptions(max_depth=1))
        with self.assertRaises(ParseError):
            parse('[]', ParseOptions(max_depth=0))

    def test_depth_limit_is_enforced(self):
        document = '[' * (MAX_DEPTH + 1) + ']' * (MAX_DEPTH + 1)
        with self.assertRaises(ParseError) as caught:
            parse(document)
        self.assertEqual(caught.exception.kind, 'maximum_depth_exceeded')
        self.assertEqual(caught.exception.offset, MAX_DEPTH)

    def test_parse_errors_report_offsets(self):
        # 한 is three UTF-8 bytes, so the offset of the control character is a byte position.
        with self.assertRaises(ParseError) as caught:
            parse_bytes(b'["\xed\x95\x9c\x01"]')
        self.assertEqual((caught.exception.offset, caught.exception.unit), (5, 'byte'))

    def test_rejection_names_its_kind(self):
        for document, kind in (('{', 'expected_object_key'), ('[1 2]', 'expected_delimiter'),
                               ('{"a" 1}', 'expected_colon'), ('"\\q"', 'invalid_escape'),
                               ('"\\u12"', 'invalid_unicode_escape'), ('"\\', 'unfinished_escape'),
                               ('"abc', 'unterminated_string'), ('["a"] x', 'trailing_input'),
                               ('nul', 'expected_value'), ('[-]', 'expected_digit'),
                               ('[1', 'expected_delimiter'), ('["\x01"]', 'unescaped_control_character')):
            with self.subTest(document=document):
                with self.assertRaises(ParseError) as caught:
                    parse(document)
                self.assertEqual(caught.exception.kind, kind)

    def test_wrong_kind_access_is_reported(self):
        value = parse('{"a":"b"}').get('a')
        with self.assertRaisesRegex(TypeError, 'Expected number, got string'):
            value.number_literal()
        with self.assertRaisesRegex(TypeError, 'Expected array, got string'):
            value.items()

    def test_member_lookup_uses_decoded_names(self):
        value = parse('{"\\u0062":1,"b":2,"\\ud83d\\ude00":3}')
        self.assertEqual(value.get('b').number_literal(), '2')
        self.assertEqual(value.get_units((0xd83d, 0xde00)).number_literal(), '3')
        self.assertIsNone(value.get('missing'))

    def test_repeated_key_keeps_first_position_and_last_value(self):
        value = parse('{"b":1,"a":2,"b":3}')
        self.assertEqual(stringify(value), '{"b":3,"a":2}')
        self.assertEqual(list(value.members()), ['b', 'a'])
        # The replaced value is validated like every other occurrence.
        with self.assertRaises(ParseError):
            parse('{"a":1,"a":tru}')

    def test_root_keeps_surrounding_text(self):
        value = parse(' 1 ')
        self.assertEqual(value.raw, ' 1 ')
        self.assertEqual(value.number_literal(), '1')
        self.assertEqual(parse(' [1] ').raw, ' [1] ')

    def test_unpaired_surrogate_stays_in_units(self):
        value = parse('{"k":"\\ud800"}').get('k')
        self.assertEqual(value.string_units(), [0xd800])
        self.assertEqual(value.string_value(), '\ud800')
        self.assertEqual(stringify(value), '"\\ud800"')

    def test_surrogate_pair_decodes(self):
        value = parse('{"k":"\\ud83d\\ude00"}').get('k')
        self.assertEqual(value.string_units(), [0xd83d, 0xde00])
        self.assertEqual(value.string_value(), '😀')

    def test_factories_validate_arguments(self):
        with self.assertRaises(TypeError):
            Value.string(1)
        with self.assertRaises(ValueError):
            Value.from_units([0x10000])
        with self.assertRaises(ValueError):
            Value.number(' 1')
        with self.assertRaises(ParseError):
            Value.number('1x')
        with self.assertRaises(ParseError):
            Value.number('NaN')
        with self.assertRaises(TypeError):
            Value.boolean(1)
        with self.assertRaises(TypeError):
            Value.array([1])
        with self.assertRaises(TypeError):
            Value.object({1: Value.null()})

    def test_values_come_only_from_the_library(self):
        with self.assertRaises(TypeError):
            Value()
        with self.assertRaises(TypeError):
            stringify({'a': 1})

    def test_returned_collections_are_immutable(self):
        value = parse('{"a":1,"b":[1,2]}')
        members = value.members()
        with self.assertRaises(TypeError):
            members['c'] = Value.null()
        self.assertEqual(list(value.members()), ['a', 'b'])
        self.assertEqual([stringify(item) for item in value.get('b').items()], ['1', '2'])

    def test_host_serialization_boundary(self):
        # The host encoder has no ordered knowledge and refuses the value.
        with self.assertRaises(TypeError):
            json.dumps(parse('{"a":1}'))

    def test_bytes_input_is_validated(self):
        with self.assertRaises(ParseError) as caught:
            parse_bytes(b'["\xc3"]')
        self.assertEqual((caught.exception.kind, caught.exception.offset), ('invalid_utf8', 2))

    def test_invalid_utf8_reports_the_first_bad_byte(self):
        for document, offset in ((b'\xff', 0), (b'["\x80"]', 2), (b'["\xed\xa0\x80"]', 2),
                                 (b'["\xf0\x9f\x98"]', 2), (b'["\xc0\x80"]', 2)):
            with self.subTest(document=document):
                with self.assertRaises(ParseError) as caught:
                    parse_bytes(document)
                self.assertEqual(caught.exception.kind, 'invalid_utf8')
                self.assertEqual(caught.exception.offset, offset)

    def test_ordered_map_rejects_non_string_key(self):
        with self.assertRaises(TypeError):
            Value.object({1: Value.null()})
        with self.assertRaises(TypeError):
            Value.object([(None, Value.null())])


class PackageCases(unittest.TestCase):
    def test_strict_parse_rejects_duplicate_keys(self):
        for document, offset in (('{"b":1,"b":2}', 7), ('{"x":{"b":1,"b":2}}', 12),
                                 ('{"\\u0062":1,"b":2}', 12), ('{"\\ud83d\\ude00":1,"😀":2}', 18)):
            with self.subTest(document=document):
                with self.assertRaises(ParseError) as caught:
                    parse(document, ParseOptions(reject_duplicates=True))
                self.assertEqual(caught.exception.kind, 'duplicate_object_key')
                self.assertEqual(caught.exception.offset, offset)

    def test_strict_parse_accepts_unique_keys(self):
        value = parse('{"b":1,"a":2}', ParseOptions(reject_duplicates=True))
        self.assertEqual(stringify(value), '{"b":1,"a":2}')
        with self.assertRaises(ParseError) as caught:
            parse_bytes(b'{"b":1,"b":\xff}', ParseOptions(reject_duplicates=True))
        self.assertEqual(caught.exception.kind, 'invalid_utf8')
        with self.assertRaises(TypeError):
            parse('1', ParseOptions(reject_duplicates=1))

    def test_text_input_rejects_lone_surrogates(self):
        with self.assertRaises(ParseError) as caught:
            parse('["한"]\ud800')
        self.assertEqual(caught.exception.kind, 'unescaped_lone_surrogate')
        self.assertEqual(caught.exception.offset, len('["한"]'.encode('utf-8')))


def case_ids() -> list[str]:
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite(loader.loadTestsFromModule(sys.modules[__name__]))
    ids = []
    for group in suite:
        for case in group:
            ids.append(case.id().rsplit('.', 1)[1].removeprefix('test_'))
    return sorted(ids)


if __name__ == '__main__':
    if '--cases' in sys.argv:
        print('\n'.join(case_ids()))
    else:
        unittest.main(argv=[argument for argument in sys.argv if argument != '--cases'], verbosity=2)
