PHP_ARG_ENABLE([ordered-json], [whether to enable ordered_json],
  [AS_HELP_STRING([--enable-ordered-json], [Enable the ordered_json native JSON parser])], [yes])

if test "$PHP_ORDERED_JSON" != "no"; then
  AS_CASE([$host_os], [darwin*], [
    AC_ARG_VAR([MACOSX_DEPLOYMENT_TARGET], [Minimum macOS version for the extension])
    AS_IF([test -z "$MACOSX_DEPLOYMENT_TARGET"], [
      AC_COMPUTE_INT([ordered_json_macos_version],
        [__ENVIRONMENT_MAC_OS_X_VERSION_MIN_REQUIRED__], [],
        [AC_MSG_ERROR([Cannot determine the compiler's macOS deployment target; set MACOSX_DEPLOYMENT_TARGET])])
      AS_IF([test "$ordered_json_macos_version" -ge 100000], [
        MACOSX_DEPLOYMENT_TARGET="$((ordered_json_macos_version / 10000)).$((ordered_json_macos_version / 100 % 100)).$((ordered_json_macos_version % 100))"
      ], [
        MACOSX_DEPLOYMENT_TARGET="$((ordered_json_macos_version / 100)).$((ordered_json_macos_version / 10 % 10)).$((ordered_json_macos_version % 10))"
      ])
    ])
    AC_MSG_NOTICE([macOS deployment target: $MACOSX_DEPLOYMENT_TARGET])
    dnl A loadable bundle does not use the dynamic-library single-module flag.
    LT_MULTI_MODULE=yes
  ])
  PHP_NEW_EXTENSION([ordered_json], [ordered_json.c hydrate.c], [$ext_shared])
fi
