{ lib }:

rec {
  mkSimpleOption = description: type: lib.mkOption {
    inherit description type;
  };
  mkOptionSubmodule = options: lib.types.submodule {
    inherit options;
  };

  # Kind of like a hash, but not really
  collectUniqueString = thing:
    if builtins.typeOf thing == "set" then
      builtins.concatStringsSep "" (lib.mapAttrsToList (name: value: (collectUniqueString value) + (builtins.hashString "sha256" name)) thing)
    else if builtins.typeOf thing == "list" then
      builtins.concatStringsSep " " (builtins.map collectUniqueString thing)
    else if builtins.typeOf thing == "number" || builtins.typeOf thing == "bool" then
      builtins.toString thing
    else if builtins.typeOf thing == "string" then
      builtins.hashString "sha256" thing
    else
      builtins.abort "collectUniqueString: unsupported type ${builtins.typeOf thing}";
}
