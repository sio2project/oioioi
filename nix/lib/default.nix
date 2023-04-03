{ lib }:

let
  python = import ./python.nix { inherit lib; };
  utils = import ./utils.nix { inherit lib; };
in
python // utils
