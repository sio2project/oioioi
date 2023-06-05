{ pkgs, stdenvNoCC, ... }:

let
  node2nixPackages = pkgs.callPackage ./node-packages.nix {
    nodeEnv = pkgs.callPackage ./node-env.nix { };
  };
  lib = node2nixPackages.package;
  bin = pkgs.writers.writeBashBin "notifications-server" ''
    ${pkgs.nodejs}/bin/node -- ${lib}/lib/node_modules/notifications-server/ns-main.js "$@"
  '';
in
pkgs.symlinkJoin { name = pkgs.lib.getName lib; paths = [ lib bin ]; } 
