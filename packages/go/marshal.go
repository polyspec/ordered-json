package orderedjson

import (
	"encoding/base64"
	"fmt"
	"math"
	"reflect"
	"sort"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"
)

// Marshaler is the JSON marshaler boundary understood by Marshal. A custom
// marshaler's result is parsed by ordered-json before it is returned.
type Marshaler interface {
	MarshalJSON() ([]byte, error)
}

var timeType = reflect.TypeOf(time.Time{})

// Marshal encodes a Go value through the ordered-json value model. Struct
// fields follow declaration order; map keys are sorted because Go maps have no
// defined iteration order. The returned bytes are compact JSON.
func Marshal(value any) ([]byte, error) {
	if value == nil {
		return []byte("null"), nil
	}
	var out strings.Builder
	if err := marshalReflect(&out, reflect.ValueOf(value), "$", false, 0); err != nil {
		return nil, err
	}
	encoded := out.String()
	parsed, err := Parse(encoded)
	if err != nil {
		return nil, fmt.Errorf("ordered-json marshal produced invalid JSON: %w", err)
	}
	compact, err := parsed.Compact()
	if err != nil {
		return nil, err
	}
	return []byte(compact), nil
}

func marshalReflect(out *strings.Builder, value reflect.Value, path string, omit bool, depth int) error {
	// The depth limit matches the parser and ends cyclic values with an error.
	if depth > MaxDepth {
		return fmt.Errorf("maximum nesting depth exceeded at %d levels", depth)
	}
	if !value.IsValid() {
		out.WriteString("null")
		return nil
	}
	if omit && isEmptyValue(value) {
		return nil
	}
	// A nil pointer or interface is null before the Marshaler boundary, so a
	// nil pointer whose type implements MarshalJSON, such as *Value, is null.
	// An interface is encoded as the value it holds.
	if (value.Kind() == reflect.Pointer || value.Kind() == reflect.Interface) && value.IsNil() {
		out.WriteString("null")
		return nil
	}
	if value.Kind() == reflect.Interface {
		return marshalReflect(out, value.Elem(), path, false, depth+1)
	}
	if value.CanInterface() {
		if marshaler, ok := value.Interface().(Marshaler); ok {
			body, err := marshaler.MarshalJSON()
			if err != nil {
				return fmt.Errorf("%s: %w", path, err)
			}
			parsed, err := ParseBytes(body)
			if err != nil {
				return fmt.Errorf("%s: custom marshaler returned invalid JSON: %w", path, err)
			}
			compact, err := parsed.Compact()
			if err != nil {
				return fmt.Errorf("%s: %w", path, err)
			}
			out.WriteString(compact)
			return nil
		}
	}
	if value.Kind() == reflect.Pointer {
		return marshalReflect(out, value.Elem(), path, false, depth+1)
	}
	switch value.Kind() {
	case reflect.Bool:
		if value.Bool() {
			out.WriteString("true")
		} else {
			out.WriteString("false")
		}
	case reflect.String:
		return writeString(out, value.String())
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		out.WriteString(strconv.FormatInt(value.Int(), 10))
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64, reflect.Uintptr:
		out.WriteString(strconv.FormatUint(value.Uint(), 10))
	case reflect.Float32, reflect.Float64:
		if math.IsNaN(value.Float()) || math.IsInf(value.Float(), 0) {
			return fmt.Errorf("%s: %s has no JSON form", path, strconv.FormatFloat(value.Float(), 'g', -1, 64))
		}
		if value.Kind() == reflect.Float32 {
			out.WriteString(strconv.FormatFloat(value.Float(), 'g', -1, 32))
		} else {
			out.WriteString(strconv.FormatFloat(value.Float(), 'g', -1, 64))
		}
	case reflect.Slice:
		if value.Type().Elem().Kind() == reflect.Uint8 {
			return writeString(out, base64.StdEncoding.EncodeToString(value.Bytes()))
		}
		out.WriteByte('[')
		for i := 0; i < value.Len(); i++ {
			if i > 0 {
				out.WriteByte(',')
			}
			if err := marshalReflect(out, value.Index(i), fmt.Sprintf("%s[%d]", path, i), false, depth+1); err != nil {
				return err
			}
		}
		out.WriteByte(']')
	case reflect.Array:
		out.WriteByte('[')
		for i := 0; i < value.Len(); i++ {
			if i > 0 {
				out.WriteByte(',')
			}
			if err := marshalReflect(out, value.Index(i), fmt.Sprintf("%s[%d]", path, i), false, depth+1); err != nil {
				return err
			}
		}
		out.WriteByte(']')
	case reflect.Map:
		if value.Type().Key().Kind() != reflect.String {
			return fmt.Errorf("%s: map keys must be strings", path)
		}
		keys := value.MapKeys()
		sort.Slice(keys, func(i, j int) bool { return keys[i].String() < keys[j].String() })
		out.WriteByte('{')
		for i, key := range keys {
			if i > 0 {
				out.WriteByte(',')
			}
			if err := writeString(out, key.String()); err != nil {
				return err
			}
			out.WriteByte(':')
			if err := marshalReflect(out, value.MapIndex(key), path+"."+key.String(), false, depth+1); err != nil {
				return err
			}
		}
		out.WriteByte('}')
	case reflect.Struct:
		members, err := structMembers(value)
		if err != nil {
			return fmt.Errorf("%s: %w", path, err)
		}
		out.WriteByte('{')
		for i, member := range members {
			if i > 0 {
				out.WriteByte(',')
			}
			if err := writeString(out, member.name); err != nil {
				return err
			}
			out.WriteByte(':')
			if err := marshalReflect(out, member.value, path+"."+member.name, false, depth+1); err != nil {
				return err
			}
		}
		out.WriteByte('}')
	default:
		return fmt.Errorf("%s: unsupported Go value %s", path, value.Type())
	}
	return nil
}

type structMember struct {
	name  string
	value reflect.Value
}

// structMembers lists the encoded fields of a struct in declaration order. An
// anonymous field without a `json` name contributes its own fields, matching Go
// field promotion, and a repeated name is an error instead of a lost field.
func structMembers(value reflect.Value) ([]structMember, error) {
	var members []structMember
	seen := make(map[string]struct{})
	var walk func(reflect.Value) error
	walk = func(current reflect.Value) error {
		currentType := current.Type()
		for i := 0; i < currentType.NumField(); i++ {
			field := currentType.Field(i)
			name, skip, omitEmpty, omitZero := marshalFieldName(field)
			if skip {
				continue
			}
			_, tagged := field.Tag.Lookup("json")
			if field.Anonymous && !tagged {
				embeddedValue := current.Field(i)
				for embeddedValue.Kind() == reflect.Pointer && !embeddedValue.IsNil() {
					embeddedValue = embeddedValue.Elem()
				}
				if embeddedValue.Kind() == reflect.Struct && embeddedValue.Type() != timeType {
					if err := walk(embeddedValue); err != nil {
						return err
					}
					continue
				}
			}
			if field.PkgPath != "" {
				continue
			}
			if omitEmpty && isEmptyValue(current.Field(i)) {
				continue
			}
			if omitZero && current.Field(i).IsZero() {
				continue
			}
			if _, repeated := seen[name]; repeated {
				return fmt.Errorf("duplicate field name %q", name)
			}
			seen[name] = struct{}{}
			members = append(members, structMember{name: name, value: current.Field(i)})
		}
		return nil
	}
	if err := walk(value); err != nil {
		return nil, err
	}
	return members, nil
}

// marshalFieldName reports the encoded name of a field, whether it is skipped,
// and the two omission rules: omitempty drops empty scalars and containers,
// omitzero drops a field that holds its type's zero value.
func marshalFieldName(field reflect.StructField) (string, bool, bool, bool) {
	tag, exists := field.Tag.Lookup("json")
	if !exists {
		return field.Name, false, false, false
	}
	parts := strings.Split(tag, ",")
	if parts[0] == "-" && len(parts) == 1 {
		return "", true, false, false
	}
	name := field.Name
	if parts[0] != "" {
		name = parts[0]
	}
	omitEmpty, omitZero := false, false
	for _, option := range parts[1:] {
		switch option {
		case "omitempty":
			omitEmpty = true
		case "omitzero":
			omitZero = true
		}
	}
	return name, false, omitEmpty, omitZero
}

func isEmptyValue(value reflect.Value) bool {
	if !value.IsValid() {
		return true
	}
	switch value.Kind() {
	case reflect.Array, reflect.Map, reflect.Slice, reflect.String:
		return value.Len() == 0
	case reflect.Bool:
		return !value.Bool()
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return value.Int() == 0
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64, reflect.Uintptr:
		return value.Uint() == 0
	case reflect.Float32, reflect.Float64:
		return value.Float() == 0
	case reflect.Interface, reflect.Pointer:
		return value.IsNil()
	}
	return false
}

func writeString(out *strings.Builder, value string) error {
	if !utf8.ValidString(value) {
		return fmt.Errorf("invalid UTF-8 string")
	}
	out.WriteByte('"')
	for _, r := range value {
		switch r {
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
			if r < 0x20 {
				out.WriteString(`\u00`)
				out.WriteString(fmt.Sprintf("%02x", r))
			} else {
				out.WriteRune(r)
			}
		}
	}
	out.WriteByte('"')
	return nil
}
