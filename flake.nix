{
  description = "The main component of the SIO2 project";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/release-22.11";
  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.filetracker = {
    url = "github:Stowarzyszenie-Talent/filetracker";
    inputs.nixpkgs.follows = "nixpkgs";
  };
  inputs.sioworkers = {
    url = "github:Stowarzyszenie-Talent/sioworkers";
    inputs.nixpkgs.follows = "nixpkgs";
    inputs.filetracker.follows = "filetracker";
  };
  inputs.extra-container = {
    url = "github:erikarvstedt/extra-container";
    inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, flake-utils, filetracker, sioworkers, extra-container }:
    let
      overlays = [
        # HACK: This seems broken in this version of nixpkgs
        (final: prev: {
          pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
            (python-final: python-prev: {
              # of course this is broken in nixpkgs...
              jsonschema = python-prev.jsonschema.overrideAttrs
                (old: {
                  propagatedBuildInputs = old.propagatedBuildInputs ++ [
                    (python-prev.buildPythonPackage rec {
                      pname = "pkgutil-resolve-name";
                      version = "1.3.10";

                      src = python-prev.fetchPypi {
                        pname = "pkgutil_resolve_name";
                        inherit version;
                        hash = "sha256-NX1snmp1VlPP14iTgXwIU682XdUeyX89NYqBk3O70XQ=";
                      };
                    })
                  ];
                });
            })
          ];
        })

        sioworkers.overlays.default
        filetracker.overlays.default
      ];

      module = { pkgs, lib, config, ... }: import ./nix/module.nix {
        # Use our version of nixpkgs so that the module works consistently across different nixpkgs versions
        pkgs = import nixpkgs {
          inherit (pkgs) system; inherit overlays;
        };
        inherit lib config;
      };
    in
    {
      lib = import ./nix/lib { inherit (nixpkgs) lib; };
      nixosModules.default = {
        nixpkgs.overlays = overlays;

        imports = [
          filetracker.nixosModules.default
          sioworkers.nixosModules.default
          module
        ];
      };
    } // (flake-utils.lib.eachSystem [ "x86_64-linux" ] (system:
      let
        pkgs = import nixpkgs {
          inherit system overlays;
        };
      in
      {
        packages.default = pkgs.python38Packages.callPackage ./nix/package.nix { };
        packages.extra-container = extra-container.lib.buildContainers {
          inherit nixpkgs system;

          # Only set this if the `system.stateVersion` of your container
          # host is < 22.05
          # legacyInstallDirs = true;

          config.containers.oioioi = {
            extra = {
              # Sets
              # privateNetwork = true
              # hostAddress = "${addressPrefix}.1"
              # localAddress = "${addressPrefix}.2"
              # addressPrefix = "10.221.0";
              addressPrefix = "10.250.0";
              # Enable internet access for the container
              enableWAN = true;
              # Always allow connections from hostAddress
              firewallAllowHost = true;
              # Make the container's localhost reachable via localAddress
              exposeLocalhost = true;
            };

            # sio2jail requires this capability
            additionalCapabilities = [ "CAP_PERFMON" ];

            extraFlags = [ "--system-call-filter=perf_event_open" ];

            config = { system, ... }: {
              imports = [
                self.nixosModules.default
                ./nix/container.nix
              ];
            };
          };
        };
      }));
}
