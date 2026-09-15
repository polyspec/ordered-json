/* Definitions shared by the parser (ordered_json.c) and child value hydration (hydrate.c). */
#ifndef ORDERED_JSON_INTERNAL_H
#define ORDERED_JSON_INTERNAL_H

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif
#include "php.h"
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

/* A descriptor is a tape of three integers per value in document order:
 * meta, start and end. meta = kind | flags | link << OJ_LINK_SHIFT. A container
 * links past its subtree; an object key links to the value of its member. */
#define OJ_OBJECT 1
#define OJ_ARRAY 2
#define OJ_STRING 3
#define OJ_NUMBER 4
#define OJ_BOOLEAN 5
#define OJ_NULL 6
#define OJ_KIND_MASK 7
/* The value serializes to exactly its source token. */
#define OJ_COMPACT 8
/* The string token contains escape sequences. */
#define OJ_ESCAPED 16
/* A repeated object key; the first key of that name links to the final value. */
#define OJ_SKIP 32
#define OJ_LINK_SHIFT 8

/* A read-only view of a tape held either in C memory or in a PHP array. */
typedef struct {
    const zend_long *slots;
    HashTable *array;
    size_t count;
} oj_tape;

static inline bool oj_slot(const oj_tape *t, size_t index, zend_long *value) {
    if (index >= t->count) return false;
    if (t->slots) {
        *value = t->slots[index];
        return true;
    }
    zval *slot = zend_hash_index_find(t->array, index);
    if (!slot || Z_TYPE_P(slot) != IS_LONG) return false;
    *value = Z_LVAL_P(slot);
    return true;
}
static inline int oj_hex(int ch) {
    if (ch >= '0' && ch <= '9') return ch - '0';
    if (ch >= 'a' && ch <= 'f') return ch - 'a' + 10;
    if (ch >= 'A' && ch <= 'F') return ch - 'A' + 10;
    return -1;
}
static inline size_t oj_put_point(unsigned char *out, size_t n, uint32_t cp) {
    if (cp < 0x80) out[n++] = (unsigned char)cp;
    else if (cp < 0x800) {
        out[n++] = (unsigned char)(0xc0 | (cp >> 6));
        out[n++] = (unsigned char)(0x80 | (cp & 63));
    } else if (cp < 0x10000) {
        out[n++] = (unsigned char)(0xe0 | (cp >> 12));
        out[n++] = (unsigned char)(0x80 | ((cp >> 6) & 63));
        out[n++] = (unsigned char)(0x80 | (cp & 63));
    } else {
        out[n++] = (unsigned char)(0xf0 | (cp >> 18));
        out[n++] = (unsigned char)(0x80 | ((cp >> 12) & 63));
        out[n++] = (unsigned char)(0x80 | ((cp >> 6) & 63));
        out[n++] = (unsigned char)(0x80 | (cp & 63));
    }
    return n;
}
/* Decoded key identity of validated string contents: UTF-8, with lone surrogates as WTF-8.
 * The result is never longer than the contents. */
static inline size_t oj_decode_name(const unsigned char *s, size_t i, size_t end, unsigned char *out) {
    size_t n = 0;
    uint32_t pending = 0;
    while (i < end) {
        uint32_t unit;
        if (s[i] == '\\') {
            unsigned char escape = s[i + 1];
            if (escape == 'u') {
                unit = 0;
                for (int k = 2; k < 6; k++) unit = (unit << 4) | (uint32_t)oj_hex(s[i + k]);
                i += 6;
            } else {
                switch (escape) {
                    case 'b': unit = 8; break;
                    case 'f': unit = 12; break;
                    case 'n': unit = 10; break;
                    case 'r': unit = 13; break;
                    case 't': unit = 9; break;
                    default: unit = escape;
                }
                i += 2;
            }
        } else if (s[i] < 0x80) {
            unit = s[i++];
        } else {
            size_t width = s[i] < 0xe0 ? 2 : (s[i] < 0xf0 ? 3 : 4);
            if (pending) { n = oj_put_point(out, n, pending); pending = 0; }
            memcpy(out + n, s + i, width);
            n += width; i += width;
            continue;
        }
        if (pending) {
            if (unit >= 0xdc00 && unit <= 0xdfff) {
                n = oj_put_point(out, n, 0x10000 + ((pending - 0xd800) << 10) + (unit - 0xdc00));
                pending = 0;
                continue;
            }
            n = oj_put_point(out, n, pending);
            pending = 0;
        }
        if (unit >= 0xd800 && unit <= 0xdbff) pending = unit;
        else n = oj_put_point(out, n, unit);
    }
    if (pending) n = oj_put_point(out, n, pending);
    return n;
}

/* Property slots of OrderedJson\Value, which ordered_json_hydrate() fills directly. */
typedef struct {
    zend_class_entry *ce;
    uint32_t source, tape, index;
} oj_value_class;

/* The class lookup is cached for the request; user classes are freed when it ends. */
ZEND_BEGIN_MODULE_GLOBALS(ordered_json)
    oj_value_class value_class;
ZEND_END_MODULE_GLOBALS(ordered_json)
ZEND_EXTERN_MODULE_GLOBALS(ordered_json)
#define OJ_G(v) ZEND_MODULE_GLOBALS_ACCESSOR(ordered_json, v)
#if defined(ZTS) && defined(COMPILE_DL_ORDERED_JSON)
ZEND_TSRMLS_CACHE_EXTERN()
#endif

PHP_GINIT_FUNCTION(ordered_json);
PHP_RSHUTDOWN_FUNCTION(ordered_json);
PHP_FUNCTION(ordered_json_hydrate);

#endif
