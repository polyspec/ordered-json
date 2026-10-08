package orderedjson

import (
	"encoding/json"
	"errors"
	"testing"
)

// Package tests for the Go value API. The shared cases exercise the JSON
// contract through the adapter; argument validation, map building, UTF-16
// units, wrong-kind access and the zero value are reachable only from here.

func TestDepthArgumentIsBounded(t *testing.T) {
	if _, err := ParseWithMaxDepth("[]", MaxDepth+1); err == nil || err.Error() != "maxDepth must be between 0 and 256" {
		t.Fatalf("ParseWithMaxDepth(257) error = %v", err)
	}
}

func TestDepthLimitIsEnforced(t *testing.T) {
	if _, err := ParseWithMaxDepth("[[1]]", 2); err != nil {
		t.Fatalf("ParseWithMaxDepth(2) error = %v", err)
	}
	var shallow *ParseError
	_, err := ParseWithMaxDepth("[[1]]", 1)
	if !errors.As(err, &shallow) || shallow.Message != "maximum nesting depth exceeded" {
		t.Fatalf("ParseWithMaxDepth(1) error = %v", err)
	}
}

func TestRejectionNamesItsKind(t *testing.T) {
	// The wording is Go's own; the kind is the shared contract.
	cases := map[string]string{
		"[1,]":       "expected_value",
		"{1:2}":      "expected_object_key",
		"[1.]":       "expected_digit",
		"\"a\x01b\"": "unescaped_control_character",
		"[1] x":      "trailing_input",
	}
	for document, kind := range cases {
		var failure *ParseError
		_, err := Parse(document)
		if !errors.As(err, &failure) {
			t.Fatalf("%q was accepted: %v", document, err)
		}
		if failure.Kind() != kind {
			t.Errorf("%q: kind = %q, want %q (%s)", document, failure.Kind(), kind, failure.Message)
		}
	}
}

func TestInvalidUTF8ReportsTheFirstBadByte(t *testing.T) {
	// The bad byte sits at index 2 of ["<bad>"]; the error names that position.
	var failure *ParseError
	_, err := ParseBytes([]byte{'[', '"', 0xff, '"', ']'})
	if !errors.As(err, &failure) || failure.Message != "invalid UTF-8" {
		t.Fatalf("ParseBytes error = %v", err)
	}
	if failure.Offset != 2 {
		t.Fatalf("offset = %d, want 2", failure.Offset)
	}
}

func TestParseErrorsReportOffsets(t *testing.T) {
	var failure *ParseError
	_, err := Parse("[1,]")
	if !errors.As(err, &failure) {
		t.Fatalf("Parse error = %v", err)
	}
	if failure.Offset != 3 || failure.Error() != "expected JSON value at byte 3" {
		t.Fatalf("offset = %d, message = %q", failure.Offset, failure.Error())
	}
	// Byte offsets, not rune counts: the emoji occupies four bytes.
	_, err = Parse(`["🌍",]`)
	if !errors.As(err, &failure) || failure.Offset != 8 {
		t.Fatalf("astral offset = %v", err)
	}
}

func TestBorrowedInputIsCopiedOnAccess(t *testing.T) {
	// Borrowed parsing reads the caller's bytes, so text handed back is copied.
	source := []byte(`{"a":"text"}`)
	value, err := ParseBytesBorrowed(source)
	if err != nil {
		t.Fatal(err)
	}
	compact, err := value.Compact()
	if err != nil {
		t.Fatal(err)
	}
	text, err := value.Get("a").StringValue()
	if err != nil {
		t.Fatal(err)
	}
	for i := range source {
		source[i] = 'x'
	}
	if compact != `{"a":"text"}` {
		t.Fatalf("Compact() changed with the caller's bytes: %s", compact)
	}
	if text != "text" {
		t.Fatalf("StringValue() changed with the caller's bytes: %q", text)
	}
}

func TestBytesInputIsValidated(t *testing.T) {
	var invalid *ParseError
	_, err := ParseBytes([]byte{'[', '"', 0xff, '"', ']'})
	if !errors.As(err, &invalid) || invalid.Message != "invalid UTF-8" {
		t.Fatalf("ParseBytes error = %v", err)
	}
	value, parseErr := ParseBytes([]byte(`["한"]`))
	if parseErr != nil {
		t.Fatal(parseErr)
	}
	if compact, _ := value.Compact(); compact != `["한"]` {
		t.Fatalf("Compact() = %s", compact)
	}
}

func TestWrongKindAccessIsReported(t *testing.T) {
	array, object := mustParse(t, "[1]"), mustParse(t, `{"a":1}`)
	cases := []struct {
		name string
		err  error
	}{
		{"members of an array", second(array.Members())},
		{"items of an object", second(object.Items())},
		{"string value of an object", secondString(object.StringValue())},
		{"number literal of an object", secondString(object.NumberLiteral())},
		{"boolean value of an object", secondBool(object.BooleanValue())},
		{"string units of an array", second(array.StringUnits())},
	}
	want := map[string]string{
		"members of an array": "expected object", "items of an object": "expected array",
		"string value of an object": "expected string", "number literal of an object": "expected number",
		"boolean value of an object": "expected boolean", "string units of an array": "expected string",
	}
	for _, test := range cases {
		if test.err == nil || test.err.Error() != want[test.name] {
			t.Errorf("%s: error = %v, want %q", test.name, test.err, want[test.name])
		}
	}
}

func TestOrderedMapRejectsNonStringKey(t *testing.T) {
	members := &OrderedMap{}
	number, err := Number("1")
	if err != nil {
		t.Fatal(err)
	}
	if err := members.Set(number, Null()); err == nil || err.Error() != "object key must be string" {
		t.Fatalf("Set with a number key error = %v", err)
	}
	if members.Len() != 0 {
		t.Fatalf("rejected key was stored: len = %d", members.Len())
	}
	if err := members.Set(nil, Null()); err == nil {
		t.Fatal("Set accepted an invalid key value")
	}
}

func TestRepeatedKeyKeepsFirstPositionAndLastValue(t *testing.T) {
	members := &OrderedMap{}
	for _, pair := range [][2]string{{"a", "1"}, {"b", "2"}, {"a", "3"}} {
		key, err := String(pair[0])
		if err != nil {
			t.Fatal(err)
		}
		value, err := Number(pair[1])
		if err != nil {
			t.Fatal(err)
		}
		if err := members.Set(key, value); err != nil {
			t.Fatal(err)
		}
	}
	object, err := Object(members)
	if err != nil {
		t.Fatal(err)
	}
	if compact, _ := object.Compact(); compact != `{"a":3,"b":2}` {
		t.Fatalf("Compact() = %s", compact)
	}
	if members.Len() != 2 {
		t.Fatalf("Len() = %d", members.Len())
	}
}

func TestMemberLookupUsesDecodedNames(t *testing.T) {
	value := mustParse(t, `{"a\u00e9":1,"b":2}`)
	if child := value.Get("aé"); child == nil {
		t.Fatal(`Get("aé") returned nothing`)
	} else if literal, _ := child.NumberLiteral(); literal != "1" {
		t.Fatalf("NumberLiteral() = %q", literal)
	}
	if value.Get("missing") != nil {
		t.Fatal(`Get("missing") returned a value`)
	}
	if child := value.GetUnits([]uint16{'b'}); child == nil {
		t.Fatal("GetUnits returned nothing")
	}
	if value.GetUnits([]uint16{'c'}) != nil {
		t.Fatal("GetUnits returned a value for a missing key")
	}
}

func TestUnpairedSurrogateStaysInUnits(t *testing.T) {
	lone := mustParse(t, `"a\ud800"`)
	units, err := lone.StringUnits()
	if err != nil {
		t.Fatal(err)
	}
	if len(units) != 2 || units[0] != 'a' || units[1] != 0xd800 {
		t.Fatalf("StringUnits() = %v", units)
	}
	if _, err := lone.StringValue(); err == nil || err.Error() != "unpaired surrogate; use StringUnits" {
		t.Fatalf("StringValue() error = %v", err)
	}
	if compact, _ := StringFromUnits([]uint16{0xd800}).Compact(); compact != `"\ud800"` {
		t.Fatalf("StringFromUnits Compact() = %s", compact)
	}
}

func TestSurrogatePairDecodes(t *testing.T) {
	pair := mustParse(t, `"\ud83c\udf0d"`)
	units, err := pair.StringUnits()
	if err != nil {
		t.Fatal(err)
	}
	if len(units) != 2 || units[0] != 0xd83c || units[1] != 0xdf0d {
		t.Fatalf("StringUnits() = %v", units)
	}
	if text, _ := pair.StringValue(); text != "🌍" {
		t.Fatalf("StringValue() = %q", text)
	}
}

func TestFactoriesValidateArguments(t *testing.T) {
	if _, err := Number(" 1"); err == nil || err.Error() != "expected number literal without whitespace" {
		t.Fatalf("Number(\" 1\") error = %v", err)
	}
	if _, err := Number("x"); err == nil {
		t.Fatal("Number accepted a non-number literal")
	}
	if _, err := Array([]*Value{nil}); err == nil || err.Error() != "expected orderedjson Value" {
		t.Fatalf("Array with an invalid item error = %v", err)
	}
	if _, err := Object(nil); err == nil || err.Error() != "expected ordered map" {
		t.Fatalf("Object(nil) error = %v", err)
	}
	text, err := String(`"q"`)
	if err != nil {
		t.Fatal(err)
	}
	if compact, _ := text.Compact(); compact != `"\"q\""` {
		t.Fatalf("String Compact() = %s", compact)
	}
}

func TestValuesComeOnlyFromTheLibrary(t *testing.T) {
	var zero Value
	if _, err := Stringify(&zero); err == nil || err.Error() != "expected orderedjson Value" {
		t.Fatalf("Stringify(zero) error = %v", err)
	}
	if _, err := (&zero).Compact(); err == nil {
		t.Fatal("Compact accepted the zero value")
	}
	if _, err := Stringify(nil); err == nil {
		t.Fatal("Stringify accepted nil")
	}
}

func TestReturnedCollectionsAreImmutable(t *testing.T) {
	array := mustParse(t, "[1,2]")
	items, err := array.Items()
	if err != nil {
		t.Fatal(err)
	}
	items[0] = nil
	again, _ := array.Items()
	if again[0] == nil {
		t.Fatal("Items() handed out the parsed slice")
	}
	object := mustParse(t, `{"a":1,"b":2}`)
	members, err := object.Members()
	if err != nil {
		t.Fatal(err)
	}
	key, _ := String("c")
	if err := members.Set(key, Null()); err != nil {
		t.Fatal(err)
	}
	fresh, _ := object.Members()
	if fresh.Len() != 2 {
		t.Fatalf("Members() shares state: Len() = %d", fresh.Len())
	}
}

func TestRootKeepsSurroundingText(t *testing.T) {
	value := mustParse(t, "  [1] \n")
	if value.Raw() != "  [1] \n" {
		t.Fatalf("Raw() = %q", value.Raw())
	}
	if compact, _ := value.Compact(); compact != "[1]" {
		t.Fatalf("Compact() = %s", compact)
	}
	items, err := value.Items()
	if err != nil {
		t.Fatal(err)
	}
	if items[0].Raw() != "1" {
		t.Fatalf("item Raw() = %q", items[0].Raw())
	}
}

func TestHostSerializationBoundary(t *testing.T) {
	// MarshalJSON is the documented integration point; it writes the ordered text.
	encoded, err := json.Marshal(mustParse(t, `{"b":1,"a":2}`))
	if err != nil {
		t.Fatal(err)
	}
	if string(encoded) != `{"b":1,"a":2}` {
		t.Fatalf("json.Marshal() = %s", encoded)
	}
}

func mustParse(t *testing.T, source string) *Value {
	t.Helper()
	value, err := Parse(source)
	if err != nil {
		t.Fatalf("Parse(%q) error = %v", source, err)
	}
	return value
}

func second[T any](_ T, err error) error { return err }

func secondString(_ string, err error) error { return err }

func secondBool(_ bool, err error) error { return err }
