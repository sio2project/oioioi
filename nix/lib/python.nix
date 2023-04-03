{ lib }:

rec {
  pythonExpression = x: {
    __type = "raw python expression";
    value = x;
  };
  pythonStatements = x: {
    __type = "raw python statements";
    value = x;
  };
  overrideAssignment = op: x: {
    __pythonOperator = op;
    value = x;
  };

  toPythonValue = { depth ? 0 }@args: value:
    let
      mkIndentRec = depth: if depth > 0 then "  " + (mkIndentRec (depth - 1)) else "";
      deeperArgs = args // { depth = depth + 1; };
      indent = mkIndentRec depth;
      deeperIndent = mkIndentRec (depth + 1);
    in
    with builtins;
    if lib.isAttrs value then
      if value ? __type then
        if value.__type == "raw python expression" then
          value.value
        else
          abort "toPythonValue: unsupported special __type ${value.__type}"
      else
        ''{${lib.concatStringsSep "," (
  lib.mapAttrsToList (key: value: "\n${deeperIndent}${toPythonValue {} key}: ${toPythonValue deeperArgs value}") value
  )}${if value == {} then " " else "\n${indent}"}}''
    else if isList value then
      if builtins.length value == 0 then
        "[ ]"
      else
        "[${lib.concatStrings (map (x: "\n${deeperIndent}${toPythonValue deeperArgs x},") value)}\n${indent}]"
    else if isString value then
      "\"${builtins.replaceStrings [ "\"" "\n" "\t" "\r" "\\" ] [ "\\\"" "\\n" "\\t" "\\r" "\\\\" ] value}\""
    else if isInt value then
      toString value
    else if isBool value then
      (if value then "True" else "False")
    else if value == null then
      "None"
    else if isFunction value then
      abort "toPythonValue: cannot convert a function to a python value"
    else
      abort "toPythonValue: argument is not of an supported type ${builtins.typeOf value}";

  toPythonVars = { depth ? 0 }@args: value: lib.concatStringsSep "\n" (lib.mapAttrsToList
    (k: v:
      if builtins.isAttrs v then
        if (v.__type or "") == "raw python statements" then
          v.value
        else if v?__pythonOperator then
          "${k} ${v.__pythonOperator} ${toPythonValue args v.value};"
        else
          "${k} = ${toPythonValue args v};"
      else
        "${k} = ${toPythonValue args v};")
    value);
}
