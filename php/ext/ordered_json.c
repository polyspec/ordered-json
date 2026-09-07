#ifdef HAVE_CONFIG_H
#include "config.h"
#endif
#include "php.h"
#include "Zend/zend_exceptions.h"
#include "ext/standard/info.h"
#include <stdint.h>
#include <stdbool.h>

#define ORDERED_JSON_VERSION "0.1.0"
#define ORDERED_JSON_MAX_DEPTH 256

typedef struct {
    const unsigned char *source;
    size_t length, pos, error_offset;
    zend_long max_depth;
    const char *message;
} oj_parser;

static zend_class_entry *oj_error_ce;

static bool oj_fail(oj_parser *p, const char *message) {
    p->message = message;
    p->error_offset = p->pos;
    return false;
}
static int oj_peek(oj_parser *p) { return p->pos < p->length ? p->source[p->pos] : -1; }
static bool oj_ws_char(int ch) { return ch == ' ' || ch == '\t' || ch == '\n' || ch == '\r'; }
static void oj_ws(oj_parser *p) { while (oj_ws_char(oj_peek(p))) p->pos++; }
static bool oj_expect(oj_parser *p, int ch, const char *message) {
    if (oj_peek(p) != ch) return oj_fail(p, message);
    p->pos++;
    return true;
}

/* Decode only scalar UTF-8: reject overlong encodings, surrogate bytes and > U+10FFFF. */
static bool oj_utf8(const unsigned char *s, size_t n, size_t *pos, uint32_t *point) {
    if (*pos >= n) return false;
    unsigned char first = s[*pos];
    if (first < 0x80) { *point = first; (*pos)++; return true; }
    int width;
    uint32_t cp, minimum;
    if (first >= 0xc2 && first <= 0xdf) { width = 2; cp = first & 31; minimum = 0x80; }
    else if (first >= 0xe0 && first <= 0xef) { width = 3; cp = first & 15; minimum = 0x800; }
    else if (first >= 0xf0 && first <= 0xf4) { width = 4; cp = first & 7; minimum = 0x10000; }
    else return false;
    if (n - *pos < (size_t)width) return false;
    for (int i = 1; i < width; i++) {
        unsigned char ch = s[*pos + i];
        if ((ch & 0xc0) != 0x80) return false;
        cp = (cp << 6) | (ch & 63);
    }
    if (cp < minimum || cp > 0x10ffff || (cp >= 0xd800 && cp <= 0xdfff)) return false;
    *point = cp; *pos += width;
    return true;
}
static int oj_hex(int ch) {
    if (ch >= '0' && ch <= '9') return ch - '0';
    if (ch >= 'a' && ch <= 'f') return ch - 'a' + 10;
    if (ch >= 'A' && ch <= 'F') return ch - 'A' + 10;
    return -1;
}
static bool oj_string(oj_parser *p, zval *out) {
    ZVAL_UNDEF(out);
    size_t start = p->pos;
    if (!oj_expect(p, '"', "Expected string")) return false;
    zval units;
    array_init(&units);
    while (p->pos < p->length) {
        int ch = p->source[p->pos++];
        if (ch == '"') {
            array_init(out);
            add_assoc_string(out, "kind", "string");
            add_assoc_long(out, "start", (zend_long)start);
            add_assoc_long(out, "end", (zend_long)p->pos);
            add_assoc_zval(out, "units", &units);
            return true;
        }
        if (ch < 32) { oj_fail(p, "Unescaped control character"); goto fail; }
        if (ch == '\\') {
            int escape = oj_peek(p);
            if (escape < 0) { oj_fail(p, "Unfinished escape"); goto fail; }
            p->pos++;
            zend_long unit;
            if (escape == 'u') {
                unit = 0;
                for (int i = 0; i < 4; i++) {
                    int d = oj_hex(oj_peek(p));
                    if (d < 0) { oj_fail(p, "Invalid Unicode escape"); goto fail; }
                    unit = (unit << 4) | d;
                    p->pos++;
                }
            } else {
                switch (escape) {
                    case '"': case '\\': case '/': unit = escape; break;
                    case 'b': unit = 8; break; case 'f': unit = 12; break;
                    case 'n': unit = 10; break; case 'r': unit = 13; break;
                    case 't': unit = 9; break;
                    default: oj_fail(p, "Invalid escape"); goto fail;
                }
            }
            add_next_index_long(&units, unit);
        } else if (ch < 128) { add_next_index_long(&units, ch); }
        else {
            uint32_t point;
            p->pos--;
            if (!oj_utf8(p->source, p->length, &p->pos, &point)) {
                oj_fail(p, "Invalid UTF-8"); goto fail;
            }
            if (point <= 0xffff) add_next_index_long(&units, point);
            else {
                point -= 0x10000;
                add_next_index_long(&units, 0xd800 | (point >> 10));
                add_next_index_long(&units, 0xdc00 | (point & 1023));
            }
        }
    }
    oj_fail(p, "Unterminated string");
fail:
    zval_ptr_dtor(&units);
    return false;
}
static bool oj_digit(int ch) { return ch >= '0' && ch <= '9'; }
static bool oj_digits(oj_parser *p) {
    if (!oj_digit(oj_peek(p))) return oj_fail(p, "Expected digit");
    while (oj_digit(oj_peek(p))) p->pos++;
    return true;
}
static bool oj_value(oj_parser *p, zend_long depth, zval *out) {
    ZVAL_UNDEF(out);
    oj_ws(p);
    size_t start = p->pos;
    int ch = oj_peek(p);
    if (ch == '"') return oj_string(p, out);
    array_init(out);
    add_assoc_long(out, "start", (zend_long)start);
    if (ch == '{' || ch == '[') {
        if (depth >= p->max_depth) { oj_fail(p, "Maximum nesting depth exceeded"); goto fail; }
        bool object = ch == '{';
        int close = object ? '}' : ']';
        add_assoc_string(out, "kind", object ? "object" : "array");
        zval children;
        array_init(&children);
        p->pos++; oj_ws(p);
        if (oj_peek(p) != close) {
            while (true) {
                if (object) {
                    zval key, value, member;
                    if (!oj_string(p, &key)) goto children_fail;
                    oj_ws(p);
                    if (!oj_expect(p, ':', "Expected colon")) { zval_ptr_dtor(&key); goto children_fail; }
                    if (!oj_value(p, depth + 1, &value)) { zval_ptr_dtor(&key); goto children_fail; }
                    array_init(&member);
                    add_assoc_zval(&member, "key", &key);
                    add_assoc_zval(&member, "value", &value);
                    add_next_index_zval(&children, &member);
                } else {
                    zval item;
                    if (!oj_value(p, depth + 1, &item)) goto children_fail;
                    add_next_index_zval(&children, &item);
                }
                oj_ws(p);
                if (oj_peek(p) == close) break;
                if (!oj_expect(p, ',', "Expected comma or closing delimiter")) goto children_fail;
                oj_ws(p);
            }
        }
        p->pos++;
        add_assoc_zval(out, object ? "members" : "items", &children);
        goto done;
children_fail:
        zval_ptr_dtor(&children);
        goto fail;
    } else if (ch == '-' || oj_digit(ch)) {
        add_assoc_string(out, "kind", "number");
        if (oj_peek(p) == '-') p->pos++;
        if (oj_peek(p) == '0') p->pos++;
        else if (!oj_digits(p)) goto fail;
        if (oj_peek(p) == '.') { p->pos++; if (!oj_digits(p)) goto fail; }
        if (oj_peek(p) == 'e' || oj_peek(p) == 'E') {
            p->pos++;
            if (oj_peek(p) == '+' || oj_peek(p) == '-') p->pos++;
            if (!oj_digits(p)) goto fail;
        }
    } else {
        const char *literals[] = {"true", "false", "null"};
        size_t lengths[] = {4, 5, 4};
        bool found = false;
        for (int i = 0; i < 3; i++) {
            if (p->length - p->pos >= lengths[i] && memcmp(p->source + p->pos, literals[i], lengths[i]) == 0) {
                p->pos += lengths[i]; found = true;
                add_assoc_string(out, "kind", i == 2 ? "null" : "boolean");
                break;
            }
        }
        if (!found) { oj_fail(p, "Expected JSON value"); goto fail; }
    }
done:
    add_assoc_long(out, "end", (zend_long)p->pos);
    return true;
fail:
    zval_ptr_dtor(out);
    ZVAL_UNDEF(out);
    return false;
}

static bool oj_parse(zend_string *source, zend_long max_depth, zval *out) {
    oj_parser p = {(const unsigned char *)ZSTR_VAL(source), ZSTR_LEN(source), 0, 0, max_depth, NULL};
    size_t cursor = 0;
    uint32_t point;
    while (cursor < p.length) {
        p.pos = cursor;
        if (!oj_utf8(p.source, p.length, &cursor, &point)) {
            oj_fail(&p, "Invalid UTF-8"); goto fail;
        }
    }
    p.pos = 0;
    if (!oj_value(&p, 0, out)) goto fail;
    oj_ws(&p);
    if (p.pos != p.length) {
        zval_ptr_dtor(out); ZVAL_UNDEF(out);
        oj_fail(&p, "Unexpected trailing input"); goto fail;
    }
    add_assoc_long(out, "start", 0);
    add_assoc_long(out, "end", (zend_long)p.length);
    return true;
fail:;
    zend_object *exception = zend_throw_exception(oj_error_ce, p.message, 0);
    zend_update_property_long(oj_error_ce, exception, "offset", sizeof("offset") - 1, (zend_long)p.error_offset);
    return false;
}

ZEND_BEGIN_ARG_WITH_RETURN_TYPE_INFO_EX(arginfo_ordered_json_scan, 0, 1, IS_ARRAY, 0)
    ZEND_ARG_TYPE_INFO(0, source, IS_STRING, 0)
    ZEND_ARG_TYPE_INFO_WITH_DEFAULT_VALUE(0, maxDepth, IS_LONG, 0, "256")
ZEND_END_ARG_INFO()
ZEND_BEGIN_ARG_WITH_RETURN_TYPE_INFO_EX(arginfo_ordered_json_compact, 0, 1, IS_STRING, 0)
    ZEND_ARG_TYPE_INFO(0, source, IS_STRING, 0)
    ZEND_ARG_TYPE_INFO_WITH_DEFAULT_VALUE(0, maxDepth, IS_LONG, 0, "256")
ZEND_END_ARG_INFO()

PHP_FUNCTION(ordered_json_scan) {
    zend_string *source;
    zend_long max_depth = ORDERED_JSON_MAX_DEPTH;
    ZEND_PARSE_PARAMETERS_START(1, 2)
        Z_PARAM_STR(source)
        Z_PARAM_OPTIONAL
        Z_PARAM_LONG(max_depth)
    ZEND_PARSE_PARAMETERS_END();
    if (max_depth < 0 || max_depth > ORDERED_JSON_MAX_DEPTH) {
        zend_argument_value_error(2, "must be between 0 and 256"); RETURN_THROWS();
    }
    if (!oj_parse(source, max_depth, return_value)) RETURN_THROWS();
}

PHP_FUNCTION(ordered_json_compact) {
    zend_string *source;
    zend_long max_depth = ORDERED_JSON_MAX_DEPTH;
    ZEND_PARSE_PARAMETERS_START(1, 2)
        Z_PARAM_STR(source)
        Z_PARAM_OPTIONAL
        Z_PARAM_LONG(max_depth)
    ZEND_PARSE_PARAMETERS_END();
    if (max_depth < 0 || max_depth > ORDERED_JSON_MAX_DEPTH) {
        zend_argument_value_error(2, "must be between 0 and 256"); RETURN_THROWS();
    }
    zval node;
    if (!oj_parse(source, max_depth, &node)) RETURN_THROWS();
    zval_ptr_dtor(&node);
    zend_string *out = zend_string_alloc(ZSTR_LEN(source), 0);
    size_t length = 0;
    bool quoted = false, escaped = false;
    for (size_t i = 0; i < ZSTR_LEN(source); i++) {
        unsigned char ch = (unsigned char)ZSTR_VAL(source)[i];
        if (quoted) {
            ZSTR_VAL(out)[length++] = ch;
            if (escaped) escaped = false;
            else if (ch == '\\') escaped = true;
            else if (ch == '"') quoted = false;
        } else if (!oj_ws_char(ch)) {
            ZSTR_VAL(out)[length++] = ch;
            if (ch == '"') quoted = true;
        }
    }
    ZSTR_VAL(out)[length] = '\0'; ZSTR_LEN(out) = length;
    RETURN_STR(out);
}

static const zend_function_entry ordered_json_functions[] = {
    PHP_FE(ordered_json_scan, arginfo_ordered_json_scan)
    PHP_FE(ordered_json_compact, arginfo_ordered_json_compact)
    PHP_FE_END
};
PHP_MINIT_FUNCTION(ordered_json) {
    zend_class_entry ce;
    INIT_CLASS_ENTRY(ce, "OrderedJsonNativeParseError", NULL);
    oj_error_ce = zend_register_internal_class_ex(&ce, zend_ce_exception);
    zend_declare_property_long(oj_error_ce, "offset", sizeof("offset") - 1, 0, ZEND_ACC_PUBLIC);
    REGISTER_STRING_CONSTANT("ORDERED_JSON_VERSION", ORDERED_JSON_VERSION, CONST_CS | CONST_PERSISTENT);
    return SUCCESS;
}
PHP_MINFO_FUNCTION(ordered_json) {
    php_info_print_table_start();
    php_info_print_table_row(2, "ordered_json support", "enabled");
    php_info_print_table_row(2, "version", ORDERED_JSON_VERSION);
    php_info_print_table_end();
}
zend_module_entry ordered_json_module_entry = {
    STANDARD_MODULE_HEADER,
    "ordered_json", ordered_json_functions,
    PHP_MINIT(ordered_json), NULL, NULL, NULL, PHP_MINFO(ordered_json),
    ORDERED_JSON_VERSION, STANDARD_MODULE_PROPERTIES
};
#ifdef COMPILE_DL_ORDERED_JSON
#ifdef ZTS
ZEND_TSRMLS_CACHE_DEFINE()
#endif
ZEND_GET_MODULE(ordered_json)
#endif
