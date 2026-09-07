PHP_ARG_ENABLE([ordered-json], [whether to enable ordered_json],
  [AS_HELP_STRING([--enable-ordered-json], [Enable the ordered_json native JSON parser])], [yes])

if test "$PHP_ORDERED_JSON" != "no"; then
  PHP_NEW_EXTENSION([ordered_json], [ordered_json.c], [$ext_shared])
fi
