package orderedjson

import (
	"encoding/json"
	"math"
	"reflect"
	"strconv"
	"testing"
	"time"
)

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

func TestMarshalReportsNonFiniteNumbers(t *testing.T) {
	for _, value := range []float64{math.NaN(), math.Inf(1), math.Inf(-1)} {
		if _, err := Marshal(map[string]float64{"x": value}); err == nil {
			t.Fatalf("Marshal() accepted %v", value)
		}
	}
}
