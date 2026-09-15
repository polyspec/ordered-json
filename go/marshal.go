package orderedjson

import (
	"encoding/base64"
	"fmt"
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
	if err := marshalReflect(&out, reflect.ValueOf(value), "$", false); err != nil {
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

func marshalReflect(out *strings.Builder, value reflect.Value, path string, omit bool) error {
	if !value.IsValid() {
		out.WriteString("null")
		return nil
	}
	if omit && isEmptyValue(value) {
		return nil
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
	if value.Kind() == reflect.Pointer || value.Kind() == reflect.Interface {
		if value.IsNil() {
			out.WriteString("null")
			return nil
		}
		return marshalReflect(out, value.Elem(), path, false)
	}
	if value.Type() == timeType {
		if value.Interface().(time.Time).IsZero() {
			out.WriteString("null")
			return nil
		}
		return writeString(out, value.Interface().(time.Time).Format(time.RFC3339Nano))
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
			if err := marshalReflect(out, value.Index(i), fmt.Sprintf("%s[%d]", path, i), false); err != nil {
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
			if err := marshalReflect(out, value.Index(i), fmt.Sprintf("%s[%d]", path, i), false); err != nil {
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
			if err := marshalReflect(out, value.MapIndex(key), path+"."+key.String(), false); err != nil {
				return err
			}
		}
		out.WriteByte('}')
	case reflect.Struct:
		out.WriteByte('{')
		written := 0
		typeOfValue := value.Type()
		for i := 0; i < value.NumField(); i++ {
			field := typeOfValue.Field(i)
			if field.PkgPath != "" {
				continue
			}
			name, skip, omitEmpty := marshalFieldName(field)
			if skip || (omitEmpty && isEmptyValue(value.Field(i))) {
				continue
			}
			if written > 0 {
				out.WriteByte(',')
			}
			if err := writeString(out, name); err != nil {
				return err
			}
			out.WriteByte(':')
			if err := marshalReflect(out, value.Field(i), path+"."+name, false); err != nil {
				return err
			}
			written++
		}
		out.WriteByte('}')
	default:
		return fmt.Errorf("%s: unsupported Go value %s", path, value.Type())
	}
	return nil
}

func marshalFieldName(field reflect.StructField) (string, bool, bool) {
	tag, exists := field.Tag.Lookup("json")
	if !exists {
		return field.Name, false, false
	}
	parts := strings.Split(tag, ",")
	if parts[0] == "-" {
		return "", true, false
	}
	name := field.Name
	if parts[0] != "" {
		name = parts[0]
	}
	omitEmpty := false
	for _, option := range parts[1:] {
		if option == "omitempty" || option == "omitzero" {
			omitEmpty = true
		}
	}
	return name, false, omitEmpty
}

func isEmptyValue(value reflect.Value) bool {
	if !value.IsValid() {
		return true
	}
	if value.Type() == timeType {
		return value.Interface().(time.Time).IsZero()
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
