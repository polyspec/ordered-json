/* This is a generated file, edit the .stub.php file instead.
 * Stub hash: 322d4d9e8c247991326243f0c506a17ef975b43c */

ZEND_BEGIN_ARG_WITH_RETURN_TYPE_INFO_EX(arginfo_ordered_json_scan, 0, 1, IS_ARRAY, 0)
	ZEND_ARG_TYPE_INFO(0, source, IS_STRING, 0)
	ZEND_ARG_TYPE_INFO_WITH_DEFAULT_VALUE(0, maxDepth, IS_LONG, 0, "256")
ZEND_END_ARG_INFO()

ZEND_BEGIN_ARG_WITH_RETURN_TYPE_INFO_EX(arginfo_ordered_json_hydrate, 0, 3, IS_ARRAY, 0)
	ZEND_ARG_TYPE_INFO(0, source, IS_STRING, 0)
	ZEND_ARG_TYPE_INFO(0, node, IS_ARRAY, 0)
	ZEND_ARG_TYPE_INFO(0, index, IS_LONG, 0)
ZEND_END_ARG_INFO()

ZEND_BEGIN_ARG_WITH_RETURN_TYPE_INFO_EX(arginfo_ordered_json_compact_node, 0, 2, IS_STRING, 0)
	ZEND_ARG_TYPE_INFO(0, source, IS_STRING, 0)
	ZEND_ARG_TYPE_INFO(0, node, IS_ARRAY, 0)
	ZEND_ARG_TYPE_INFO_WITH_DEFAULT_VALUE(0, index, IS_LONG, 0, "0")
ZEND_END_ARG_INFO()

ZEND_FUNCTION(ordered_json_scan);
ZEND_FUNCTION(ordered_json_hydrate);
ZEND_FUNCTION(ordered_json_compact_node);

static const zend_function_entry ext_functions[] = {
	ZEND_FE(ordered_json_scan, arginfo_ordered_json_scan)
	ZEND_FE(ordered_json_hydrate, arginfo_ordered_json_hydrate)
	ZEND_FE(ordered_json_compact_node, arginfo_ordered_json_compact_node)
	ZEND_FE_END
};
