package orderedjson

import "testing"

func TestParseManyPreservesValuesAndRejectsInvalidTrailingValue(t *testing.T) {
	values, err := ParseMany(" {}\n[1,2] \t null ")
	if err != nil {
		t.Fatal(err)
	}
	if len(values) != 3 || values[0].Kind() != ObjectKind || values[1].Kind() != ArrayKind || values[2].Kind() != NullKind {
		t.Fatalf("parsed values = %d, %s, %s, %s", len(values), values[0].Kind(), values[1].Kind(), values[2].Kind())
	}
	if _, err := ParseMany(`{} {`); err == nil {
		t.Fatal("accepted invalid sequence")
	}
}
