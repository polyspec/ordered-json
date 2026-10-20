package orderedjson

import (
	"encoding/json"
	"errors"
	"math"
	"reflect"
	"strconv"
	"strings"
	"testing"
	"time"
)

// Package tests for the Go value API. The shared cases exercise the JSON
// contract through the adapter; argument validation, map building, UTF-16
// units, wrong-kind access and the zero value are reachable only from here.

// Requirements: RQ-006
func TestDepthArgumentIsBounded(t *testing.T) {
	if _, err := ParseWithMaxDepth("[]", MaxDepth+1); err == nil || err.Error() != "maxDepth must be between 0 and 256" {
		t.Fatalf("ParseWithMaxDepth(257) error = %v", err)
	}
}

// Requirements: RQ-006
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

// Requirements: RQ-005
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

// Requirements: RQ-004, RQ-007
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

// Requirements: RQ-004
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

// Requirements: RQ-007
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

// Requirements: RQ-014
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

// Requirements: RQ-016
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

// Requirements: RQ-001
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

// Requirements: RQ-002, RQ-019
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

// Requirements: RQ-009
func TestUnpairedSurrogateStaysInUnits(t *testing.T) {
	lone := mustParse(t, `"a\ud800"`)
	units, err := lone.StringUnits()
	if err != nil {
		t.Fatal(err)
	}
	if len(units) != 2 || units[0] != 'a' || units[1] != 0xd800 {
		t.Fatalf("StringUnits() = %v", units)
	}
	if compact, _ := StringFromUnits([]uint16{0xd800}).Compact(); compact != `"\ud800"` {
		t.Fatalf("StringFromUnits Compact() = %s", compact)
	}
}

// Requirements: RQ-009
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

// Requirements: RQ-007
func TestUtf8ValidationHoldsForLongMultibyteText(t *testing.T) {
	text := strings.Repeat("\ud55c\U0001f30d", 64)
	value, err := ParseBytes([]byte(`{"key":"` + text + `"}`))
	if err != nil {
		t.Fatal(err)
	}
	if got, err := value.Get("key").StringValue(); err != nil || got != text {
		t.Fatalf("StringValue() = %q, %v", got, err)
	}
	var parseError *ParseError
	if _, err := ParseBytes([]byte("[\"\xff\"]")); !errors.As(err, &parseError) || parseError.Kind() != "invalid_utf8" || parseError.Offset != 2 {
		t.Fatalf("ParseBytes of an invalid byte error = %v", err)
	}
}

// Requirements: RQ-015
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
	if compact, _ := Boolean(true).Compact(); compact != "true" {
		t.Fatalf("Boolean(true) Compact() = %s", compact)
	}
}

// Requirements: RQ-012
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

// Requirements: RQ-013
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

// Requirements: RQ-018
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

// Requirements: RQ-020
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

// Requirements: RQ-020
func TestHostSerializationEmbedsValues(t *testing.T) {
	// A native structure that holds values is encoded by the host encoder with their contract bytes.
	encoded, err := json.Marshal(struct {
		Call  string `json:"call"`
		Props *Value `json:"props"`
	}{Call: "view", Props: mustParse(t, `{"z":1.50,"a":[{"b":2,"a":3}]}`)})
	if err != nil {
		t.Fatal(err)
	}
	if want := `{"call":"view","props":{"z":1.50,"a":[{"b":2,"a":3}]}}`; string(encoded) != want {
		t.Fatalf("json.Marshal() = %s, want %s", encoded, want)
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

func TestPublicApiExportsTheEntryPoints(t *testing.T) {
	// RQ-023: the parse, serialization, factory and accessor functions are exported.
	text, err := String("x")
	if err != nil {
		t.Fatal(err)
	}
	number, err := Number("1")
	if err != nil {
		t.Fatal(err)
	}
	list, err := Array([]*Value{text, number, Boolean(true), Null()})
	if err != nil {
		t.Fatal(err)
	}
	var members OrderedMap
	if err := members.Set(mustParse(t, `"a"`), list); err != nil {
		t.Fatal(err)
	}
	built, err := Object(&members)
	if err != nil {
		t.Fatal(err)
	}
	compact, err := Stringify(built)
	if err != nil || compact != `{"a":["x",1,true,null]}` {
		t.Fatalf("Stringify = %q, %v", compact, err)
	}
	parsed := mustParse(t, compact)
	object, err := parsed.Members()
	if err != nil {
		t.Fatal(err)
	}
	items, err := object.Get("a").Items()
	if err != nil {
		t.Fatal(err)
	}
	kinds := []Kind{StringKind, NumberKind, BooleanKind, NullKind}
	for index, item := range items {
		if item.Kind() != kinds[index] {
			t.Fatalf("item %d kind = %s", index, item.Kind())
		}
	}
	if value, _ := items[0].StringValue(); value != "x" {
		t.Fatalf("StringValue = %q", value)
	}
	if literal, _ := items[1].NumberLiteral(); literal != "1" {
		t.Fatalf("NumberLiteral = %q", literal)
	}
	if flag, _ := items[2].BooleanValue(); !flag {
		t.Fatal("BooleanValue = false")
	}
	if _, err := ParseBytes([]byte("[]")); err != nil {
		t.Fatal(err)
	}
}

func TestParseErrorExposesKindOffsetAndMessage(t *testing.T) {
	// RQ-024: a parse error exposes its kind, its offset and its message.
	var failure *ParseError
	_, err := Parse("[1,]")
	if !errors.As(err, &failure) {
		t.Fatalf("Parse error = %v", err)
	}
	if failure.Kind() != "expected_value" || failure.Offset != 3 || failure.Message != "expected JSON value" {
		t.Fatalf("kind = %q, offset = %d, message = %q", failure.Kind(), failure.Offset, failure.Message)
	}
}

// Requirements: RQ-017
func TestStrictParseRejectsDuplicateKeys(t *testing.T) {
	for _, source := range []string{
		`{"a":1,"a":2}`,
		`{"a":1,"a":2}`,
		`{"nested":{"a":1,"a":2}}`,
		`[{"a":1,"a":2}]`,
		`{"\ud800":1,"\ud800":2}`,
	} {
		if _, err := Parse(source); err != nil {
			t.Fatalf("Parse(%s) error = %v", source, err)
		}
		var failure *ParseError
		_, err := ParseRejectDuplicates(source)
		if !errors.As(err, &failure) {
			t.Fatalf("ParseRejectDuplicates(%s) error = %v", source, err)
		}
		if failure.Message != "duplicate object key" || failure.Kind() != "duplicate_object_key" || failure.Offset != strings.LastIndex(source, `,"`)+1 {
			t.Fatalf("ParseRejectDuplicates(%s) = %q %q at %d", source, failure.Message, failure.Kind(), failure.Offset)
		}
	}
}

// Requirements: RQ-017
func TestStrictParseAcceptsUniqueKeys(t *testing.T) {
	source := `{"a":1,"nested":[{"b":2}],"state":null}`
	parsed, err := ParseRejectDuplicates(source)
	if err != nil {
		t.Fatal(err)
	}
	if compact, _ := parsed.Compact(); compact != source {
		t.Fatalf("Compact() = %s", compact)
	}
	var failure *ParseError
	if _, err := ParseRejectDuplicates("\xff"); !errors.As(err, &failure) || failure.Message != "invalid UTF-8" || failure.Offset != 0 {
		t.Fatalf("invalid UTF-8 error = %v", err)
	}
}

// Requirements: RQ-009
func TestStringValueKeepsAnUnpairedSurrogate(t *testing.T) {
	// The string value is the library form: UTF-8 with an unpaired surrogate as WTF-8, never replaced by U+FFFD.
	if value, err := mustParse(t, `"a\ud800"`).StringValue(); err != nil || value != "a\xed\xa0\x80" {
		t.Fatalf("StringValue() = %q, %v", value, err)
	}
	if value, err := mustParse(t, `"\ud83c\udf0d"`).StringValue(); err != nil || value != "\U0001f30d" {
		t.Fatalf("StringValue() of a pair = %q, %v", value, err)
	}
}

// Requirements: RQ-008
func TestTextInputRejectsLoneSurrogates(t *testing.T) {
	// A literal unpaired surrogate has only its WTF-8 encoding in a Go string, which is no UTF-8: it is rejected before the
	// grammar is read, at the byte of the surrogate.
	for source, offset := range map[string]int{"[\"\xed\xa0\x80\"]": 2, "[\"\xed\xb0\x80\"]": 2, "{\"\xed\xa0\x80\":1}": 2, "[\"\xed\xa0\x80": 2} {
		var failure *ParseError
		if _, err := Parse(source); !errors.As(err, &failure) || failure.Message != "invalid UTF-8" || failure.Offset != offset {
			t.Fatalf("Parse(%q) error = %v", source, err)
		}
	}
}

// The typed encoder Marshal, tested beside the value API.
type inner struct {
	A int `json:"a"`
}

// Requirements: RQ-011, RQ-020
func TestMarshalPreservesTypedJSONContract(t *testing.T) {
	type document struct {
		First  string         `json:"first"`
		Empty  []string       `json:"empty,omitempty"`
		Object map[string]any `json:"object"`
		Bytes  []byte         `json:"bytes"`
	}
	got, err := Marshal(document{
		First:  "한글",
		Object: map[string]any{"z": 1, "a": []int{}},
		Bytes:  []byte{0, 1, 2},
	})
	if err != nil {
		t.Fatal(err)
	}
	want := `{"first":"한글","object":{"a":[],"z":1},"bytes":"AAEC"}`
	if string(got) != want {
		t.Fatalf("Marshal() = %s, want %s", got, want)
	}
	value, err := ParseBytes(got)
	if err != nil || value.Kind() != ObjectKind {
		t.Fatalf("Marshal output is not an ordered object: %v", err)
	}
}

// Requirements: RQ-003
func TestMarshalKeepsEmptyObjectAndArrayDistinct(t *testing.T) {
	got, err := Marshal(struct {
		Object map[string]string `json:"object"`
		Array  []string          `json:"array"`
	}{Object: map[string]string{}, Array: []string{}})
	if err != nil {
		t.Fatal(err)
	}
	want := `{"object":{},"array":[]}`
	if string(got) != want {
		t.Fatalf("Marshal() = %s, want %s", got, want)
	}
}

type marshalFixture struct{}

func (marshalFixture) MarshalJSON() ([]byte, error) { return []byte(`{"b":2,"a":1}`), nil }

// Requirements: RQ-015, RQ-020
func TestMarshalValidatesCustomMarshalerThroughOrderedParser(t *testing.T) {
	got, err := Marshal(marshalFixture{})
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != `{"b":2,"a":1}` {
		t.Fatalf("Marshal() = %s", got)
	}
	_, err = Marshal(errors.New("unsupported custom error"))
	if err != nil {
		t.Fatalf("error values should encode through their exported fields: %v", err)
	}
}

// Requirements: RQ-020
func TestMarshalWritesNullForNilValuePointer(t *testing.T) {
	var nothing *Value
	got, err := Marshal(struct {
		Missing *Value `json:"missing"`
		Present *Value `json:"present"`
		Items   []*Value
		Members map[string]*Value
	}{Present: Null(), Items: []*Value{nil}, Members: map[string]*Value{"a": nil}})
	if err != nil {
		t.Fatal(err)
	}
	want := `{"missing":null,"present":null,"Items":[null],"Members":{"a":null}}`
	if string(got) != want {
		t.Fatalf("Marshal() = %s, want %s", got, want)
	}
	got, err = Marshal(nothing)
	if err != nil || string(got) != "null" {
		t.Fatalf("Marshal(nil *Value) = %s, %v", got, err)
	}
	var marshaler json.Marshaler = nothing
	got, err = Marshal(struct {
		Custom json.Marshaler `json:"custom"`
	}{Custom: marshaler})
	if err != nil || string(got) != `{"custom":null}` {
		t.Fatalf("Marshal(nil *Value in interface) = %s, %v", got, err)
	}
	got, err = Marshal(struct {
		Missing *Value `json:"missing,omitempty"`
		Zero    *Value `json:"zero,omitzero"`
	}{})
	if err != nil || string(got) != `{}` {
		t.Fatalf("Marshal(omitted nil *Value) = %s, %v", got, err)
	}
}

// Requirements: RQ-016
func TestMarshalRejectsUnsupportedMapKey(t *testing.T) {
	if _, err := Marshal(map[int]string{1: "x"}); err == nil {
		t.Fatal("Marshal() accepted non-string map key")
	}
}

// Requirements: RQ-020
func TestMarshalTimeAndBytesMatchTypedValues(t *testing.T) {
	got, err := Marshal(struct {
		When time.Time `json:"when"`
		Data []byte    `json:"data"`
	}{When: time.Date(2026, 9, 16, 1, 2, 3, 4, time.UTC), Data: []byte("x")})
	if err != nil {
		t.Fatal(err)
	}
	value, err := ParseBytes(got)
	if err != nil {
		t.Fatal(err)
	}
	when, _ := value.Get("when").StringValue()
	data, _ := value.Get("data").StringValue()
	if !reflect.DeepEqual([]string{when, data}, []string{"2026-09-16T01:02:03.000000004Z", "eA=="}) {
		t.Fatalf("unexpected typed output: %s", got)
	}
}

type promoted struct {
	inner
	B int `json:"b"`
}

// Requirements: RQ-020
func TestMarshalPromotesEmbeddedFields(t *testing.T) {
	got, err := Marshal(promoted{inner: inner{A: 1}, B: 2})
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != `{"a":1,"b":2}` {
		t.Fatalf("Marshal() = %s, want {\"a\":1,\"b\":2}", got)
	}
}

type collides struct {
	inner
	A int `json:"a"`
}

// Requirements: RQ-017
func TestMarshalRejectsRepeatedFieldNames(t *testing.T) {
	if _, err := Marshal(collides{inner: inner{A: 1}, A: 2}); err == nil {
		t.Fatal("Marshal() silently dropped a field with a repeated name")
	}
}

// Requirements: RQ-006, RQ-020
func TestMarshalRejectsCyclicValues(t *testing.T) {
	type node struct {
		Next *node `json:"next"`
	}
	cycle := &node{}
	cycle.Next = cycle
	_, err := Marshal(cycle)
	if err == nil || !strings.Contains(err.Error(), "maximum nesting depth exceeded") {
		t.Fatalf("Marshal() on a cyclic value returned %v", err)
	}
}

// Requirements: RQ-006
func TestMarshalRejectsValuesDeeperThanTheParser(t *testing.T) {
	var deep any = "leaf"
	for i := 0; i <= MaxDepth; i++ {
		deep = []any{deep}
	}
	if _, err := Marshal(deep); err == nil {
		t.Fatal("Marshal() accepted a value deeper than the parser allows")
	}
}

// Random values compare Marshal with encoding/json. Typed encoding has no second
// implementation in this repository, so the host encoder is the reference for the
// decoded structure only; ordered-json still owns the JSON text it produces.

type marshalRNG struct{ state uint64 }

func (r *marshalRNG) next() uint64 {
	r.state ^= r.state << 13
	r.state ^= r.state >> 7
	r.state ^= r.state << 17
	return r.state
}

func (r *marshalRNG) intn(n int) int { return int(r.next() % uint64(n)) }

type fuzzTagged struct {
	Name   string         `json:"name"`
	Count  int            `json:"count,omitempty"`
	Ratio  float64        `json:"ratio"`
	Flag   bool           `json:"flag,omitempty"`
	Items  []any          `json:"items"`
	Lookup map[string]any `json:"lookup,omitempty"`
	Zeroed int            `json:"zeroed,omitzero"`
	When   time.Time      `json:"when,omitzero"`
	Hidden string         `json:"-"`
	Plain  string
	Labels map[string]string `json:"labels,omitempty"`
}

type fuzzBase struct {
	ID string `json:"id"`
}

type fuzzEmbeds struct {
	fuzzBase
	Extra int `json:"extra"`
}

var fuzzStrings = []string{"", "a", "키", `"q"`, "tab\there", "line\nbreak", `\slash`, "emoji🙂", "<html>&", "\x00\x1f"}

func (r *marshalRNG) value(depth int) any {
	switch r.intn(12) {
	case 0:
		return nil
	case 1:
		return r.intn(2) == 0
	case 2:
		return r.intn(1000) - 500
	case 3:
		return float64(r.intn(10000)) / float64(1+r.intn(100))
	case 4:
		return fuzzStrings[r.intn(len(fuzzStrings))]
	case 5, 6:
		if depth > 3 {
			return r.intn(10)
		}
		list := make([]any, r.intn(4))
		for i := range list {
			list[i] = r.value(depth + 1)
		}
		return list
	case 7, 8:
		if depth > 3 {
			return fuzzStrings[r.intn(len(fuzzStrings))]
		}
		object := map[string]any{}
		for i := 0; i < r.intn(4); i++ {
			object[fuzzStrings[r.intn(len(fuzzStrings))]+strconv.Itoa(i)] = r.value(depth + 1)
		}
		return object
	case 9:
		return fuzzTagged{
			Name:   fuzzStrings[r.intn(len(fuzzStrings))],
			Count:  r.intn(5),
			Ratio:  float64(r.intn(100)) / 4,
			Flag:   r.intn(2) == 0,
			Items:  []any{r.value(depth + 1)},
			Lookup: map[string]any{"k": r.value(depth + 1)},
			Zeroed: r.intn(3),
			When:   time.Unix(int64(r.intn(2))*1_700_000_000, 0).UTC(),
			Hidden: "dropped",
			Plain:  fuzzStrings[r.intn(len(fuzzStrings))],
		}
	case 10:
		return fuzzEmbeds{fuzzBase: fuzzBase{ID: fuzzStrings[r.intn(len(fuzzStrings))]}, Extra: r.intn(9)}
	default:
		return []byte(fuzzStrings[r.intn(len(fuzzStrings))])
	}
}

// Requirements: RQ-020
func TestMarshalMatchesHostEncoderStructures(t *testing.T) {
	cases := 20000
	if testing.Short() {
		cases = 2000
	}
	random := &marshalRNG{state: 2654435761}
	compared := 0
	for i := 0; i < cases; i++ {
		value := random.value(0)
		got, err := Marshal(value)
		native, nativeErr := json.Marshal(value)
		if err != nil {
			if nativeErr == nil {
				t.Fatalf("case %d: Marshal failed where the host encoder succeeded: %v (%#v)", i, err, value)
			}
			continue
		}
		parsed, parseErr := ParseBytes(got)
		if parseErr != nil {
			t.Fatalf("case %d: Marshal produced JSON the parser rejects: %v (%s)", i, parseErr, got)
		}
		again, compactErr := parsed.Compact()
		if compactErr != nil || again != string(got) {
			t.Fatalf("case %d: round trip changed the output: %s -> %s (%v)", i, got, again, compactErr)
		}
		if nativeErr != nil {
			continue
		}
		var mine, theirs any
		if err := json.Unmarshal(got, &mine); err != nil {
			t.Fatalf("case %d: output rejected by the host decoder: %v (%s)", i, err, got)
		}
		if err := json.Unmarshal(native, &theirs); err != nil {
			continue
		}
		compared++
		if !reflect.DeepEqual(mine, theirs) {
			t.Fatalf("case %d: structures differ\n  ordered-json=%s\n  host=%s", i, got, native)
		}
	}
	if compared < cases/2 {
		t.Fatalf("only %d of %d cases reached the structural comparison", compared, cases)
	}
}

// Requirements: RQ-020
func TestMarshalOmitRulesFollowTheHostEncoder(t *testing.T) {
	type omissions struct {
		EmptyString string         `json:"emptystring,omitempty"`
		ZeroInt     int            `json:"zeroint,omitempty"`
		EmptyMap    map[string]int `json:"emptymap,omitempty"`
		ZeroTime    time.Time      `json:"zerotime,omitempty"`
		ZeroedTime  time.Time      `json:"zeroedtime,omitzero"`
		ZeroedInt   int            `json:"zeroedint,omitzero"`
		Kept        string         `json:"kept"`
	}
	got, err := Marshal(omissions{})
	if err != nil {
		t.Fatal(err)
	}
	native, err := json.Marshal(omissions{})
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != string(native) {
		t.Fatalf("Marshal() = %s, host encoder = %s", got, native)
	}
}

// Requirements: RQ-010
func TestMarshalReportsNonFiniteNumbers(t *testing.T) {
	for _, value := range []float64{math.NaN(), math.Inf(1), math.Inf(-1)} {
		if _, err := Marshal(map[string]float64{"x": value}); err == nil {
			t.Fatalf("Marshal() accepted %v", value)
		}
	}
}

// Requirements: RQ-003
func TestArraysAndObjectsStayDistinct(t *testing.T) {
	items, err := mustParse(t, "[3,1,2]").Items()
	if err != nil {
		t.Fatal(err)
	}
	for index, want := range []string{"3", "1", "2"} {
		if literal, _ := items[index].NumberLiteral(); literal != want {
			t.Fatalf("item %d = %s, want %s", index, literal, want)
		}
	}
	if mustParse(t, "[]").Kind() != ArrayKind || mustParse(t, "{}").Kind() != ObjectKind {
		t.Fatal("[] and {} are not an array and an object")
	}
	text := `{"a":[],"b":{},"c":[{}]}`
	if compact, _ := Stringify(mustParse(t, text)); compact != text {
		t.Fatalf("Stringify() = %s", compact)
	}
}

// Requirements: RQ-010
func TestNumberTokensAreKeptExactly(t *testing.T) {
	tokens := []string{"1.0e+2", "-0", "0.10", "123456789012345678901234567890", "1E400"}
	items, err := mustParse(t, "["+strings.Join(tokens, ",")+"]").Items()
	if err != nil {
		t.Fatal(err)
	}
	for index, want := range tokens {
		if literal, _ := items[index].NumberLiteral(); literal != want {
			t.Fatalf("item %d = %s, want %s", index, literal, want)
		}
	}
	for source, kind := range map[string]string{"NaN": "expected_value", "Infinity": "expected_value", "-Infinity": "expected_digit", "[NaN]": "expected_value"} {
		var failure *ParseError
		if _, err := Parse(source); !errors.As(err, &failure) || failure.Kind() != kind {
			t.Fatalf("Parse(%s) error = %v", source, err)
		}
	}
}

// Requirements: RQ-011
func TestSerializationIsIdempotent(t *testing.T) {
	once, _ := Stringify(mustParse(t, ` { "b" : 1 , "a" : 2 , "b" : 3 } `))
	if once != `{"b":3,"a":2}` {
		t.Fatalf("Stringify() = %s", once)
	}
	if again, _ := Stringify(mustParse(t, once)); again != once {
		t.Fatalf("Stringify(Parse(%s)) = %s", once, again)
	}
}
