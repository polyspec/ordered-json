package orderedjson

import (
	"errors"
	"reflect"
	"strings"
	"testing"
	"time"
)

type inner struct {
	A int `json:"a"`
}

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

func TestMarshalRejectsUnsupportedMapKey(t *testing.T) {
	if _, err := Marshal(map[int]string{1: "x"}); err == nil {
		t.Fatal("Marshal() accepted non-string map key")
	}
}

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

func TestMarshalRejectsRepeatedFieldNames(t *testing.T) {
	if _, err := Marshal(collides{inner: inner{A: 1}, A: 2}); err == nil {
		t.Fatal("Marshal() silently dropped a field with a repeated name")
	}
}

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

func TestMarshalRejectsValuesDeeperThanTheParser(t *testing.T) {
	var deep any = "leaf"
	for i := 0; i <= MaxDepth; i++ {
		deep = []any{deep}
	}
	if _, err := Marshal(deep); err == nil {
		t.Fatal("Marshal() accepted a value deeper than the parser allows")
	}
}
