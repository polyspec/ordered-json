// Package orderedjson preserves JSON document order at every object depth.
package orderedjson

import (
	"fmt"
	"strings"
	"unicode/utf16"
	"unicode/utf8"
	"unsafe"
)

const MaxDepth = 256

type Kind string

const (
	ObjectKind  Kind = "object"
	ArrayKind   Kind = "array"
	StringKind  Kind = "string"
	NumberKind  Kind = "number"
	BooleanKind Kind = "boolean"
	NullKind    Kind = "null"
)

// Internal kind codes index kindNames; zero marks an invalid Value.
const (
	invalidKind uint8 = iota
	objectKind
	arrayKind
	stringKind
	numberKind
	booleanKind
	nullKind
)

var kindNames = [...]Kind{invalidKind: "", objectKind: ObjectKind, arrayKind: ArrayKind,
	stringKind: StringKind, numberKind: NumberKind, booleanKind: BooleanKind, nullKind: NullKind}

const (
	// flagCompact marks a value whose compact form is exactly its source token:
	// it contains no insignificant whitespace and no duplicate object keys.
	flagCompact uint8 = 1 << iota
	// flagRoot marks a parse result; its Raw text includes surrounding whitespace.
	flagRoot
	// flagBorrowed marks a source that aliases caller memory, so derived text is copied.
	flagBorrowed
	// flagEscaped marks a string token that contains escape sequences.
	flagEscaped
)

// Objects with more members than this keep a hash index; smaller ones scan linearly.
const linearMembers = 8

// Parsed values are allocated in chunks of at most this many values.
const maxChunk = 1024

type ParseError struct {
	Offset  int
	Message string
}

func (e *ParseError) Error() string { return fmt.Sprintf("%s at byte %d", e.Message, e.Offset) }

// OrderedMap associates each key with one value and retains its insertion position.
// Its zero value is an empty map. Keys returns JSON string values in that order.
type OrderedMap struct {
	state *orderedMapState
}

type orderedMapState struct {
	keys    []*Value
	values  []*Value
	indices map[string]int // nil while len(keys) <= linearMembers
}

// unitsName is a lossless identity for decoded JSON keys: UTF-8, with lone
// surrogates encoded as WTF-8. Unescaped key tokens already have this form.
func unitsName(units []uint16) string {
	out := make([]byte, 0, len(units)*3)
	for i := 0; i < len(units); i++ {
		r := rune(units[i])
		if r >= 0xd800 && r <= 0xdbff && i+1 < len(units) && units[i+1] >= 0xdc00 && units[i+1] <= 0xdfff {
			r = utf16.DecodeRune(r, rune(units[i+1]))
			i++
		}
		switch {
		case r < 0x80:
			out = append(out, byte(r))
		case r < 0x800:
			out = append(out, 0xc0|byte(r>>6), 0x80|byte(r)&0x3f)
		case r < 0x10000:
			out = append(out, 0xe0|byte(r>>12), 0x80|byte(r>>6)&0x3f, 0x80|byte(r)&0x3f)
		default:
			out = append(out, 0xf0|byte(r>>18), 0x80|byte(r>>12)&0x3f, 0x80|byte(r>>6)&0x3f, 0x80|byte(r)&0x3f)
		}
	}
	return string(out)
}

// decodeUnits decodes the contents of a validated string token.
func decodeUnits(content string) []uint16 {
	units := make([]uint16, 0, len(content))
	for i := 0; i < len(content); {
		ch := content[i]
		switch {
		case ch == '\\':
			escape := content[i+1]
			i += 2
			switch escape {
			case 'u':
				var u uint16
				for end := i + 4; i < end; i++ {
					d, _ := hex(content[i])
					u = u<<4 | d
				}
				units = append(units, u)
			case 'b':
				units = append(units, 8)
			case 'f':
				units = append(units, 12)
			case 'n':
				units = append(units, 10)
			case 'r':
				units = append(units, 13)
			case 't':
				units = append(units, 9)
			default:
				units = append(units, uint16(escape))
			}
		case ch < utf8.RuneSelf:
			units = append(units, uint16(ch))
			i++
		default:
			r, width := utf8.DecodeRuneInString(content[i:])
			if r >= 0x10000 {
				hi, lo := utf16.EncodeRune(r)
				units = append(units, uint16(hi), uint16(lo))
			} else {
				units = append(units, uint16(r))
			}
			i += width
		}
	}
	return units
}

func (s *orderedMapState) find(name string) int {
	if s.indices != nil {
		if index, ok := s.indices[name]; ok {
			return index
		}
		return -1
	}
	for index, key := range s.keys {
		if key.name() == name {
			return index
		}
	}
	return -1
}

func (m *OrderedMap) Set(key, value *Value) error {
	if key.Kind() != StringKind {
		return fmt.Errorf("object key must be string")
	}
	if !value.valid() {
		return fmt.Errorf("expected orderedjson Value")
	}
	if m.state == nil {
		m.state = &orderedMapState{}
	}
	name := key.name()
	if index := m.state.find(name); index >= 0 {
		m.state.values[index] = value
		return nil
	}
	m.state.keys = append(m.state.keys, key)
	m.state.values = append(m.state.values, value)
	if m.state.indices != nil {
		m.state.indices[name] = len(m.state.keys) - 1
	} else if len(m.state.keys) > linearMembers {
		m.state.indices = make(map[string]int, len(m.state.keys))
		for index, key := range m.state.keys {
			m.state.indices[key.name()] = index
		}
	}
	return nil
}
func (m *OrderedMap) get(name string) *Value {
	if m.state == nil {
		return nil
	}
	index := m.state.find(name)
	if index < 0 {
		return nil
	}
	return m.state.values[index]
}
func (m *OrderedMap) GetUnits(key []uint16) *Value {
	if m.state == nil {
		return nil
	}
	return m.get(unitsName(key))
}
func (m *OrderedMap) Get(key string) *Value {
	if !utf8.ValidString(key) {
		return nil
	}
	return m.get(key)
}
func (m *OrderedMap) orderedKeys() []*Value {
	if m.state == nil {
		return nil
	}
	return m.state.keys
}
func (m *OrderedMap) Keys() []*Value { return append([]*Value{}, m.orderedKeys()...) }
func (m *OrderedMap) Len() int       { return len(m.orderedKeys()) }
func (m *OrderedMap) clone() *OrderedMap {
	out := &OrderedMap{}
	if m.state == nil {
		return out
	}
	out.state = &orderedMapState{keys: m.Keys(), values: append([]*Value{}, m.state.values...)}
	if m.state.indices != nil {
		out.state.indices = make(map[string]int, len(m.state.indices))
		for key, index := range m.state.indices {
			out.state.indices[key] = index
		}
	}
	return out
}

// Value is immutable. Construct values with Parse or the factory functions.
// The zero value is invalid. Members and Items return independent map/slice copies.
type Value struct {
	source     string
	start, end int // value token; a root's Raw text also includes surrounding whitespace
	kind       uint8
	flags      uint8
	members    OrderedMap
	items      []*Value
}

func (v *Value) valid() bool { return v != nil && v.kind != invalidKind }
func (v *Value) Kind() Kind {
	if !v.valid() {
		return ""
	}
	return kindNames[v.kind]
}
func (v *Value) Raw() string {
	if !v.valid() {
		return ""
	}
	if v.flags&flagRoot != 0 {
		return v.source
	}
	return v.source[v.start:v.end]
}

// name returns the key identity of a string value; see unitsName.
func (v *Value) name() string {
	content := v.source[v.start+1 : v.end-1]
	if v.flags&flagEscaped == 0 {
		return content
	}
	return unitsName(decodeUnits(content))
}
func (v *Value) String() string { out, _ := v.Compact(); return out }
func (v *Value) Members() (*OrderedMap, error) {
	if v.Kind() != ObjectKind {
		return nil, fmt.Errorf("expected object")
	}
	return v.members.clone(), nil
}
func (v *Value) Items() ([]*Value, error) {
	if v.Kind() != ArrayKind {
		return nil, fmt.Errorf("expected array")
	}
	return append([]*Value{}, v.items...), nil
}
func (v *Value) StringUnits() ([]uint16, error) {
	if v.Kind() != StringKind {
		return nil, fmt.Errorf("expected string")
	}
	return decodeUnits(v.source[v.start+1 : v.end-1]), nil
}
func (v *Value) StringValue() (string, error) {
	if v.Kind() != StringKind {
		return "", fmt.Errorf("expected string")
	}
	content := v.source[v.start+1 : v.end-1]
	if v.flags&flagEscaped == 0 {
		if v.flags&flagBorrowed != 0 {
			return strings.Clone(content), nil
		}
		return content, nil
	}
	units := decodeUnits(content)
	for i := 0; i < len(units); i++ {
		u := units[i]
		if u >= 0xd800 && u <= 0xdbff {
			if i+1 >= len(units) || units[i+1] < 0xdc00 || units[i+1] > 0xdfff {
				return "", fmt.Errorf("unpaired surrogate; use StringUnits")
			}
			i++
		} else if u >= 0xdc00 && u <= 0xdfff {
			return "", fmt.Errorf("unpaired surrogate; use StringUnits")
		}
	}
	return string(utf16.Decode(units)), nil
}
func (v *Value) NumberLiteral() (string, error) {
	if v.Kind() != NumberKind {
		return "", fmt.Errorf("expected number")
	}
	return strings.TrimSpace(v.Raw()), nil
}
func (v *Value) BooleanValue() (bool, error) {
	if v.Kind() != BooleanKind {
		return false, fmt.Errorf("expected boolean")
	}
	return strings.TrimSpace(v.Raw()) == "true", nil
}
func (v *Value) GetUnits(key []uint16) *Value {
	if v.Kind() != ObjectKind {
		return nil
	}
	return v.members.GetUnits(key)
}
func (v *Value) Get(key string) *Value {
	if !utf8.ValidString(key) || v.Kind() != ObjectKind {
		return nil
	}
	return v.members.get(key)
}
func String(text string) (*Value, error) {
	if !utf8.ValidString(text) {
		return nil, fmt.Errorf("invalid UTF-8")
	}
	return StringFromUnits(utf16.Encode([]rune(text))), nil
}
func StringFromUnits(units []uint16) *Value {
	var out strings.Builder
	out.WriteByte('"')
	for _, u := range units {
		switch u {
		case '"':
			out.WriteString(`\"`)
		case '\\':
			out.WriteString(`\\`)
		case '\b':
			out.WriteString(`\b`)
		case '\f':
			out.WriteString(`\f`)
		case '\n':
			out.WriteString(`\n`)
		case '\r':
			out.WriteString(`\r`)
		case '\t':
			out.WriteString(`\t`)
		default:
			if u >= 0x20 && u <= 0x7e {
				out.WriteByte(byte(u))
			} else {
				fmt.Fprintf(&out, "\\u%04x", u)
			}
		}
	}
	out.WriteByte('"')
	v, _ := Parse(out.String())
	return v
}
func Number(literal string) (*Value, error) {
	v, err := Parse(literal)
	if err != nil {
		return nil, err
	}
	if v.kind != numberKind || strings.TrimSpace(literal) != literal {
		return nil, fmt.Errorf("expected number literal without whitespace")
	}
	return v, nil
}
func Boolean(value bool) *Value {
	if value {
		v, _ := Parse("true")
		return v
	}
	v, _ := Parse("false")
	return v
}
func Null() *Value { v, _ := Parse("null"); return v }
func Array(items []*Value) (*Value, error) {
	parts := make([]string, len(items))
	for i, v := range items {
		if !v.valid() {
			return nil, fmt.Errorf("expected orderedjson Value")
		}
		parts[i], _ = v.Compact()
	}
	return Parse("[" + strings.Join(parts, ",") + "]")
}
func Object(members *OrderedMap) (*Value, error) {
	if members == nil {
		return nil, fmt.Errorf("expected ordered map")
	}
	parts := make([]string, members.Len())
	for i, key := range members.orderedKeys() {
		child, _ := members.state.values[i].Compact()
		parts[i] = strings.TrimSpace(key.Raw()) + ":" + child
	}
	return Parse("{" + strings.Join(parts, ",") + "}")
}
func Stringify(value *Value) (string, error) {
	if !value.valid() {
		return "", fmt.Errorf("expected orderedjson Value")
	}
	return value.Compact()
}

// MarshalJSON integrates with encoding/json while preserving ordered-json values.
func (v *Value) MarshalJSON() ([]byte, error) {
	raw, err := Stringify(v)
	return []byte(raw), err
}
func (v *Value) Compact() (string, error) {
	if !v.valid() {
		return "", fmt.Errorf("expected orderedjson Value")
	}
	if v.flags&flagCompact != 0 {
		out := v.source[v.start:v.end]
		if v.flags&flagBorrowed != 0 {
			out = strings.Clone(out)
		}
		return out, nil
	}
	var out strings.Builder
	out.Grow(v.end - v.start)
	v.writeJSON(&out)
	return out.String(), nil
}
func (v *Value) writeJSON(out *strings.Builder) {
	if v.flags&flagCompact != 0 {
		out.WriteString(v.source[v.start:v.end])
		return
	}
	switch v.kind {
	case objectKind:
		out.WriteByte('{')
		for i, key := range v.members.orderedKeys() {
			if i > 0 {
				out.WriteByte(',')
			}
			out.WriteString(key.source[key.start:key.end])
			out.WriteByte(':')
			v.members.state.values[i].writeJSON(out)
		}
		out.WriteByte('}')
	case arrayKind:
		out.WriteByte('[')
		for i, item := range v.items {
			if i > 0 {
				out.WriteByte(',')
			}
			item.writeJSON(out)
		}
		out.WriteByte(']')
	default:
		out.WriteString(v.source[v.start:v.end])
	}
}

func Parse(source string) (*Value, error)      { return ParseWithMaxDepth(source, MaxDepth) }
func ParseBytes(source []byte) (*Value, error) { return Parse(string(source)) }

// ParseBytesBorrowed parses source without copying its bytes.
//
// The caller must not modify source for the lifetime of the returned Value.
// Use ParseBytes when the input buffer may be reused or mutated.
func ParseBytesBorrowed(source []byte) (*Value, error) {
	return parse(unsafe.String(unsafe.SliceData(source), len(source)), MaxDepth, flagBorrowed)
}
func ParseWithMaxDepth(source string, maxDepth int) (*Value, error) {
	return parse(source, maxDepth, 0)
}

// utf8.ValidString reports only that an invalid sequence exists, so the error
// position comes from the first one.
func firstInvalidByte(source string) int {
	for i := 0; i < len(source); {
		r, size := utf8.DecodeRuneInString(source[i:])
		if r == utf8.RuneError && size <= 1 {
			return i
		}
		i += size
	}
	return len(source)
}

func parse(source string, maxDepth int, flags uint8) (*Value, error) {
	if maxDepth < 0 || maxDepth > MaxDepth {
		return nil, fmt.Errorf("maxDepth must be between 0 and 256")
	}
	if !utf8.ValidString(source) {
		return nil, &ParseError{firstInvalidByte(source), "invalid UTF-8"}
	}
	p := parser{source: source, maxDepth: maxDepth, flags: flags, estimate: -1}
	v, err := p.value(0)
	if err != nil {
		return nil, err
	}
	p.ws()
	if p.pos != len(source) {
		return nil, p.fail("unexpected trailing input")
	}
	v.flags |= flagRoot
	return v, nil
}

type member struct {
	name       string
	key, value *Value
}

type parser struct {
	source                 string
	pos, maxDepth          int
	flags                  uint8
	whitespace, duplicates int
	estimate, chunks       int      // estimated value count (-1 until counted); chunks allocated
	slab                   []Value  // values are allocated in chunks
	items                  []*Value // pending array items of open arrays
	members                []member // pending members of open objects
}

func (p *parser) newValue(kind uint8, start int, flags uint8) *Value {
	if len(p.slab) == cap(p.slab) {
		// A scalar document allocates only its value; others size chunks by their separators.
		size := 1
		if p.chunks == 1 {
			size = p.nodes()
		} else if p.chunks > 1 {
			size = max(p.nodes()/2, 16)
		}
		p.slab = make([]Value, 0, min(max(size, 1), maxChunk))
		p.chunks++
	}
	p.slab = p.slab[:len(p.slab)+1]
	v := &p.slab[len(p.slab)-1]
	v.source, v.start, v.end, v.kind, v.flags = p.source, start, p.pos, kind, flags|p.flags
	return v
}

// nodes estimates the number of values in the document from its separators.
func (p *parser) nodes() int {
	if p.estimate < 0 {
		s := p.source
		p.estimate = strings.Count(s, ",") + strings.Count(s, ":") + strings.Count(s, "[") + strings.Count(s, "{")
	}
	return p.estimate
}
func (p *parser) peek() byte {
	if p.pos >= len(p.source) {
		return 0
	}
	return p.source[p.pos]
}
func (p *parser) fail(message string) error { return &ParseError{p.pos, message} }
func (p *parser) ws() {
	pos := p.pos
	for pos < len(p.source) {
		if ch := p.source[pos]; ch != ' ' && ch != '\t' && ch != '\n' && ch != '\r' {
			break
		}
		pos++
	}
	p.whitespace += pos - p.pos
	p.pos = pos
}
func (p *parser) expect(ch byte, message string) error {
	if p.peek() != ch {
		return p.fail(message)
	}
	p.pos++
	return nil
}
func hex(ch byte) (uint16, bool) {
	switch {
	case ch >= '0' && ch <= '9':
		return uint16(ch - '0'), true
	case ch >= 'a' && ch <= 'f':
		return uint16(ch - 'a' + 10), true
	case ch >= 'A' && ch <= 'F':
		return uint16(ch - 'A' + 10), true
	}
	return 0, false
}

// string validates a string token and reports whether it contains escapes.
func (p *parser) string() (bool, error) {
	if err := p.expect('"', "expected string"); err != nil {
		return false, err
	}
	escaped := false
	for p.pos < len(p.source) {
		ch := p.source[p.pos]
		p.pos++
		switch {
		case ch == '"':
			return escaped, nil
		case ch < 32:
			return false, p.fail("unescaped control character")
		case ch == '\\':
			if p.pos >= len(p.source) {
				return false, p.fail("unfinished escape")
			}
			escape := p.source[p.pos]
			p.pos++
			escaped = true
			switch escape {
			case 'u':
				for i := 0; i < 4; i++ {
					if _, ok := hex(p.peek()); !ok {
						return false, p.fail("invalid Unicode escape")
					}
					p.pos++
				}
			case '"', '\\', '/', 'b', 'f', 'n', 'r', 't':
			default:
				return false, p.fail("invalid escape")
			}
		}
	}
	return false, p.fail("unterminated string")
}
func isDigit(ch byte) bool { return ch >= '0' && ch <= '9' }
func (p *parser) digits() error {
	if !isDigit(p.peek()) {
		return p.fail("expected digit")
	}
	for isDigit(p.peek()) {
		p.pos++
	}
	return nil
}
func (p *parser) value(depth int) (*Value, error) {
	p.ws()
	start := p.pos
	switch ch := p.peek(); {
	case ch == '{' || ch == '[':
		return p.container(depth, start, ch == '{')
	case ch == '"':
		escaped, err := p.string()
		if err != nil {
			return nil, err
		}
		flags := flagCompact
		if escaped {
			flags |= flagEscaped
		}
		return p.newValue(stringKind, start, flags), nil
	case ch == '-' || isDigit(ch):
		if ch == '-' {
			p.pos++
		}
		if p.peek() == '0' {
			p.pos++
		} else if err := p.digits(); err != nil {
			return nil, err
		}
		if p.peek() == '.' {
			p.pos++
			if err := p.digits(); err != nil {
				return nil, err
			}
		}
		if p.peek() == 'e' || p.peek() == 'E' {
			p.pos++
			if p.peek() == '+' || p.peek() == '-' {
				p.pos++
			}
			if err := p.digits(); err != nil {
				return nil, err
			}
		}
		return p.newValue(numberKind, start, flagCompact), nil
	case ch == 't' && strings.HasPrefix(p.source[p.pos:], "true"):
		p.pos += 4
		return p.newValue(booleanKind, start, flagCompact), nil
	case ch == 'f' && strings.HasPrefix(p.source[p.pos:], "false"):
		p.pos += 5
		return p.newValue(booleanKind, start, flagCompact), nil
	case ch == 'n' && strings.HasPrefix(p.source[p.pos:], "null"):
		p.pos += 4
		return p.newValue(nullKind, start, flagCompact), nil
	}
	return nil, p.fail("expected JSON value")
}
func (p *parser) container(depth, start int, object bool) (*Value, error) {
	if depth >= p.maxDepth {
		return nil, p.fail("maximum nesting depth exceeded")
	}
	close, kind, base := byte(']'), arrayKind, len(p.items)
	if object {
		close, kind, base = '}', objectKind, len(p.members)
	}
	whitespace, duplicates := p.whitespace, p.duplicates
	var index map[string]int
	p.pos++
	p.ws()
	if p.peek() != close {
		for {
			if object {
				keyStart := p.pos
				escaped, err := p.string()
				if err != nil {
					return nil, err
				}
				flags := flagCompact
				if escaped {
					flags |= flagEscaped
				}
				key := p.newValue(stringKind, keyStart, flags)
				p.ws()
				if err := p.expect(':', "expected colon"); err != nil {
					return nil, err
				}
				child, err := p.value(depth + 1)
				if err != nil {
					return nil, err
				}
				index = p.addMember(base, index, key, child)
			} else {
				child, err := p.value(depth + 1)
				if err != nil {
					return nil, err
				}
				if cap(p.items) == 0 {
					p.items = make([]*Value, 0, min(max(p.nodes(), 4), maxChunk))
				}
				p.items = append(p.items, child)
			}
			p.ws()
			if p.peek() == close {
				break
			}
			if err := p.expect(',', "expected comma or closing delimiter"); err != nil {
				return nil, err
			}
			p.ws()
		}
	}
	p.pos++
	flags := uint8(0)
	if p.whitespace == whitespace && p.duplicates == duplicates {
		flags = flagCompact
	}
	v := p.newValue(kind, start, flags)
	if object {
		if members := p.members[base:]; len(members) > 0 {
			n := len(members)
			pointers := make([]*Value, 2*n)
			state := &orderedMapState{keys: pointers[:n:n], values: pointers[n:], indices: index}
			for i, m := range members {
				state.keys[i], state.values[i] = m.key, m.value
			}
			v.members.state = state
			p.members = p.members[:base]
		}
	} else if items := p.items[base:]; len(items) > 0 {
		if depth == 0 {
			// The root array is the last user of the stack.
			v.items = items[:len(items):len(items)]
			p.items = nil
		} else {
			v.items = make([]*Value, len(items))
			copy(v.items, items)
			p.items = p.items[:base]
		}
	}
	return v, nil
}

// addMember records a parsed member of the object whose pending members start at base.
// A repeated key keeps its first position and token and takes the new value.
func (p *parser) addMember(base int, index map[string]int, key, value *Value) map[string]int {
	name := key.name()
	members := p.members[base:]
	if index != nil {
		if i, ok := index[name]; ok {
			members[i].value = value
			p.duplicates++
			return index
		}
		index[name] = len(members)
	} else {
		for i := range members {
			if members[i].name == name {
				members[i].value = value
				p.duplicates++
				return index
			}
		}
		if len(members) == linearMembers {
			index = make(map[string]int, 2*linearMembers)
			for i := range members {
				index[members[i].name] = i
			}
			index[name] = len(members)
		}
	}
	if cap(p.members) == 0 {
		p.members = make([]member, 0, min(max(strings.Count(p.source, ":"), 4), maxChunk))
	}
	p.members = append(p.members, member{name, key, value})
	return index
}
