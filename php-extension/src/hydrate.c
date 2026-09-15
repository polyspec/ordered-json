/* Child value hydration: creates OrderedJson\Value instances for the children of a container. */
#include "ordered_json_internal.h"

ZEND_DECLARE_MODULE_GLOBALS(ordered_json)

PHP_GINIT_FUNCTION(ordered_json) {
#if defined(ZTS) && defined(COMPILE_DL_ORDERED_JSON)
    ZEND_TSRMLS_CACHE_UPDATE();
#endif
    memset(ordered_json_globals, 0, sizeof(*ordered_json_globals));
}
PHP_RSHUTDOWN_FUNCTION(ordered_json) {
    OJ_G(value_class).ce = NULL;
    return SUCCESS;
}

static const oj_value_class *oj_find_value_class(void) {
    oj_value_class *vc = &OJ_G(value_class);
    if (vc->ce) return vc;
    zend_string *name = zend_string_init("OrderedJson\\Value", sizeof("OrderedJson\\Value") - 1, 0);
    zend_class_entry *ce = zend_lookup_class_ex(name, NULL, ZEND_FETCH_CLASS_NO_AUTOLOAD);
    zend_string_release(name);
    if (!ce) return NULL;
    static const char *names[] = {"source", "tape", "index"};
    uint32_t *offsets[] = {&vc->source, &vc->tape, &vc->index};
    for (int i = 0; i < 3; i++) {
        zend_property_info *info = zend_hash_str_find_ptr(&ce->properties_info, names[i], strlen(names[i]));
        if (!info || (info->flags & ZEND_ACC_STATIC)) return NULL;
        *offsets[i] = info->offset;
    }
    vc->ce = ce;
    return vc;
}
/* Create a Value without calling its constructor; it shares the source and tape. */
static void oj_new_value(zval *out, const oj_value_class *vc, zval *source, zval *tape, zend_long index) {
    object_init_ex(out, vc->ce);
    zend_object *object = Z_OBJ_P(out);
    zval *slot = OBJ_PROP(object, vc->source);
    ZVAL_COPY(slot, source);
    Z_PROP_FLAG_P(slot) = 0;
    slot = OBJ_PROP(object, vc->tape);
    ZVAL_COPY(slot, tape);
    Z_PROP_FLAG_P(slot) = 0;
    slot = OBJ_PROP(object, vc->index);
    ZVAL_LONG(slot, index);
    Z_PROP_FLAG_P(slot) = 0;
}
/* Whether s[start, end) is string token contents whose escapes are complete. */
static bool oj_escapes_complete(const unsigned char *s, size_t start, size_t end) {
    for (size_t i = start; i < end; i++) {
        if (s[i] != '\\') continue;
        if (i + 1 >= end) return false;
        if (s[i + 1] == 'u') {
            if (end - i < 6) return false;
            for (int k = 2; k < 6; k++) if (oj_hex(s[i + k]) < 0) return false;
            i += 5;
        } else {
            i++;
        }
    }
    return true;
}

/* Child values of the container at index: the item list of an array, or [members, keys] of an
 * object keyed by decoded member name, matching the pure PHP hydration. */
PHP_FUNCTION(ordered_json_hydrate) {
    zend_string *source;
    zval *node;
    zend_long index;
    ZEND_PARSE_PARAMETERS_START(3, 3)
        Z_PARAM_STR(source)
        Z_PARAM_ARRAY(node)
        Z_PARAM_LONG(index)
    ZEND_PARSE_PARAMETERS_END();
    const oj_value_class *vc = oj_find_value_class();
    if (!vc) {
        zend_throw_error(NULL, "Class OrderedJson\\Value with source, tape and index properties is not loaded");
        RETURN_THROWS();
    }
    zval source_value, item, members, keys;
    ZVAL_STR(&source_value, source);
    oj_tape t = {NULL, Z_ARRVAL_P(node), zend_hash_num_elements(Z_ARRVAL_P(node))};
    const unsigned char *s = (const unsigned char *)ZSTR_VAL(source);
    zend_long meta;
    if (index < 0 || !oj_slot(&t, (size_t)index, &meta) || meta < 0) goto invalid;
    size_t limit = (size_t)(meta >> OJ_LINK_SHIFT);
    if (limit < (size_t)index + 3 || limit > t.count) goto invalid;
    if ((meta & OJ_KIND_MASK) == OJ_ARRAY) {
        if (limit == (size_t)index + 3) RETURN_EMPTY_ARRAY();
        array_init(&members);
        for (size_t i = (size_t)index + 3; i < limit;) {
            zend_long item_meta;
            if (!oj_slot(&t, i, &item_meta) || item_meta < 0) goto invalid_items;
            size_t next = (item_meta & OJ_KIND_MASK) <= OJ_ARRAY ? (size_t)(item_meta >> OJ_LINK_SHIFT) : i + 3;
            if (next <= i || next > limit) goto invalid_items;
            oj_new_value(&item, vc, &source_value, node, (zend_long)i);
            add_next_index_zval(&members, &item);
            i = next;
        }
        RETURN_COPY_VALUE(&members);
invalid_items:
        zval_ptr_dtor(&members);
        goto invalid;
    }
    if ((meta & OJ_KIND_MASK) != OJ_OBJECT) goto invalid;
    if (limit == (size_t)index + 3) {
        ZVAL_EMPTY_ARRAY(&members);
        ZVAL_EMPTY_ARRAY(&keys);
    } else {
        array_init(&members);
        array_init(&keys);
    }
    for (size_t i = (size_t)index + 3; i < limit;) {
        zend_long key_meta, key_start, key_end, value_meta;
        if (!oj_slot(&t, i, &key_meta) || !oj_slot(&t, i + 1, &key_start) || !oj_slot(&t, i + 2, &key_end)
            || !oj_slot(&t, i + 3, &value_meta) || key_meta < 0 || value_meta < 0 || (key_meta & OJ_KIND_MASK) != OJ_STRING
            || key_start < 0 || key_end < key_start + 2 || (zend_ulong)key_end > ZSTR_LEN(source)) goto invalid_members;
        size_t next = (value_meta & OJ_KIND_MASK) <= OJ_ARRAY ? (size_t)(value_meta >> OJ_LINK_SHIFT) : i + 6;
        size_t target = (size_t)(key_meta >> OJ_LINK_SHIFT);
        if (next <= i + 3 || next > limit || target <= i || target >= limit) goto invalid_members;
        if (!(key_meta & OJ_SKIP)) {
            size_t start = (size_t)key_start + 1, end = (size_t)key_end - 1;
            zend_string *name;
            if (key_meta & OJ_ESCAPED) {
                if (!oj_escapes_complete(s, start, end)) goto invalid_members;
                name = zend_string_alloc(end - start, 0);
                ZSTR_LEN(name) = oj_decode_name(s, start, end, (unsigned char *)ZSTR_VAL(name));
                ZSTR_VAL(name)[ZSTR_LEN(name)] = '\0';
            } else {
                name = zend_string_init((const char *)s + start, end - start, 0);
            }
            oj_new_value(&item, vc, &source_value, node, (zend_long)i);
            zend_symtable_update(Z_ARRVAL(keys), name, &item);
            oj_new_value(&item, vc, &source_value, node, (zend_long)target);
            zend_symtable_update(Z_ARRVAL(members), name, &item);
            zend_string_release(name);
        }
        i = next;
    }
    array_init_size(return_value, 2);
    add_next_index_zval(return_value, &members);
    add_next_index_zval(return_value, &keys);
    return;
invalid_members:
    zval_ptr_dtor(&members);
    zval_ptr_dtor(&keys);
invalid:
    zend_argument_value_error(2, "must be a descriptor from ordered_json_scan() for argument #1 ($source)");
    RETURN_THROWS();
}
