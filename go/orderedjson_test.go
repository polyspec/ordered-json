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

func TestParseManyValuesMatchSeparateParses(t *testing.T) {
	documents := []string{`[1,2]`, `[3,[4,5]]`, `{"a":[6]}`, ` [ 7 , 8 ] `, `[]`, `"x"`, `{"a":1,"a":2}`}
	source := ""
	for _, document := range documents {
		source += document + "\n"
	}
	values, err := ParseMany(source)
	if err != nil {
		t.Fatal(err)
	}
	if len(values) != len(documents) {
		t.Fatalf("parsed %d values, want %d", len(values), len(documents))
	}
	for i, document := range documents {
		want, err := Parse(document)
		if err != nil {
			t.Fatal(err)
		}
		wantItems, _ := want.Items()
		gotItems, _ := values[i].Items()
		if values[i].String() != want.String() || len(gotItems) != len(wantItems) {
			t.Fatalf("value %d = %s with %d items, want %s with %d items", i, values[i], len(gotItems), want, len(wantItems))
		}
		for j := range wantItems {
			if gotItems[j].String() != wantItems[j].String() {
				t.Errorf("value %d item %d = %s, want %s", i, j, gotItems[j], wantItems[j])
			}
		}
	}
}
