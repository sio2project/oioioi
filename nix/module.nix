{ pkgs, lib, config }:

with (import ./lib { inherit lib; });
let
  cfg = config.services.oioioi;
  # The string "s" if cfg.useSSL is true, "" otherwise
  sIfSSL = if cfg.useSSL then "s" else "";
  baseSettings = {
    # TODO: How do we handle updating this?
    CONFIG_VERSION = 49;
    DEBUG = false;

    SITE_NAME = "OIOIOI";
    SITE_ID = 1;
    PUBLIC_ROOT_URL = "http${sIfSSL}://${cfg.domain}";

    DISABLE_QUIZZES = false;
    PROBLEM_STATISTICS_AVAILABLE = true;
    CONTEST_MODE = pythonExpression ''ContestMode.neutral'';
    REGISTRATION_RULES_CONSENT = pythonExpression ''_("talent terms accepted")'';

    # SERVER is managed by a more high level module below, same with DATABASES

    TIME_ZONE = config.time.timeZone;
    LANGUAGE_CODE = "en";

    COMPRESS_OFFLINE = true;

    CAPTCHA_FLITE_PATH = "${pkgs.flite}/bin/flite";
    CAPTCHA_SOX_PATH = "${pkgs.sox}/bin/sox";

    # This shouldn't be written to, if it is then we've encountered a bug.
    MEDIA_ROOT = "/var/empty";

    # Managed by systemd
    STATIC_ROOT = "/var/lib/sio2/static";
    FILETRACKER_CACHE_ROOT = "/var/cache/sio2-filetracker-cache";

    NOTIFICATIONS_SERVER_ENABLED = true;
    NOTIFICATIONS_SERVER_URL = "http${sIfSSL}://${cfg.domain}/";

    INSTALLED_APPS = pythonExpression ''${toPythonValue { } [
      "oioioi.participants"
      "oioioi.testrun"
      "oioioi.scoresreveal"
      "oioioi.confirmations"
      "oioioi.ctimes"
      "oioioi.suspendjudge"
      "oioioi.submitservice"
      "oioioi.timeline"
      "oioioi.statistics"
      "oioioi.notifications"
      "oioioi.globalmessage"
      "oioioi.phase"
      "oioioi.supervision"
      "oioioi.talent"
    ]} + INSTALLED_APPS'';

    MIDDLEWARE = overrideAssignment "+=" [
      "oioioi.supervision.middleware.supervision_middleware" # needed for supervision
      "oioioi.contests.middleware.CurrentContestMiddleware"
    ];

    SUBMITTABLE_LANGUAGES = pythonStatements ''
      SUBMITTABLE_LANGUAGES.pop('Java');
      SUBMITTABLE_LANGUAGES.pop('Python');
      SUBMITTABLE_EXTENSIONS.pop('Java');
      SUBMITTABLE_EXTENSIONS.pop('Python');
    '';

    SECRET_KEY = pythonStatements ''
      import uuid
      from pathlib import Path

      SECRET_KEY_PATH = Path("/var/lib/sio2/secret_key")
      if SECRET_KEY_PATH.exists():
        SECRET_KEY = SECRET_KEY_PATH.read_text().strip()
      else:
        SECRET_KEY = str(uuid.uuid4())
        SECRET_KEY_PATH.touch(0o600)
        SECRET_KEY_PATH.write_text(SECRET_KEY)
    '';

    ADMINS = [ ];
    MANAGERS = pythonExpression "ADMINS";

    EMAIL_USE_TLS = false;
    EMAIL_HOST = "localhost";
    EMAIL_PORT = 25;
    EMAIL_HOST_USER = "";
    EMAIL_HOST_PASSWORD = "";
    EMAIL_SUBJECT_PREFIX = "[OIOIOI] ";

    DEFAULT_FROM_EMAIL = "oioioi@${cfg.domain}";
    SERVER_EMAIL = pythonExpression "DEFAULT_FROM_EMAIL";

    SEND_USER_ACTIVATION_EMAIL = false;

    AVAILABLE_COMPILERS = {
      "C" = {
        "gcc10_2_1_c99" = { "display_name" = "gcc=10.2.1 std=gnu99 -O3"; };
      };
      "C++" = {
        "g++10_2_1_cpp17" = { "display_name" = "g++=10.2.1 std=c++17 -O3"; };
      };
      "Pascal" = {
        "fpc2_6_2" = { "display_name" = "fpc=2.6.2"; };
      };
      "Output-only" = {
        "output-only" = { "display_name" = "output-only"; };
      };
    };

    DEFAULT_COMPILERS = {
      "C" = "gcc10_2_1_c99";
      "C++" = "g++10_2_1_cpp17";
      "Pascal" = "fpc2_6_2";
      "Output-only" = "output-only";
    };

    USE_SINOLPACK_MAKEFILES = false;

    ALLOWED_HOSTS = [ "*" ];
  };
in
{
  options.services.oioioi = {
    enable = lib.mkEnableOption "OIOIOI, the main component of the SIO2 contesting system";

    domain = lib.mkOption {
      default = config.networking.fqdn;
      defaultText = lib.literalExpression "config.networking.fqdn";
      type = lib.types.str;
      description = lib.mkDoc ''
        Domain name of the oioioi instance. This should be set to a domain that resolves to this computer!

        Used for the default value of PUBLIC_ROOT_URL in settings, for nginx vhost configuration and notifications server URL.
      '';
    };

    nginx = lib.mkOption {
      default = null;
      description = lib.mdDoc ''
        Options for customising the oioioi nginx virtual host.
      '';
      # FIXME: Typecheck this
      type = lib.types.nullOr lib.types.attrs;
    };

    useSSL = lib.mkOption {
      default = false;
      description = lib.mdDoc ''
        Enable SSL in nginx and some oioioi components.

        For this to work SSL has to be set up properly in nginx.
      '';
    };

    rabbitmqUrl = lib.mkOption {
      # Using 127.0.0.1 instead of localhost here, as that resolves
      # to ::1, which apparently doesn't work properly.
      default = "amqp://oioioi:oioioi@127.0.0.1:${builtins.toString config.services.rabbitmq.port}//";
      description = "The RabbitMQ URL in amqp format SIO2 processes should connect to";
      type = lib.types.str;
    };

    filetrackerUrl = lib.mkOption {
      default = "http://127.0.0.1:${config.services.filetracker.port}/";
      description = "The Filetracker URL SIO2 processes should connect to";
      type = lib.types.str;
    };

    defaultFiletrackerEnsureFiles = lib.mkOption {
      default = true;
      description = "Fill services.filetracker.ensureFiles with sensible defaults for sio2";
      type = lib.types.bool;
    };

    uwsgi = lib.mkOption {
      default = { };
      description = "uwsgi settings";
      type = mkOptionSubmodule {
        concurrency = lib.mkOption {
          default = "auto";
          description = "The number of uwsgi processes to spawn";
          type = with lib.types; oneOf [ (strMatching "auto") ints.positive ];
        };
      };
    };

    unpackmgr = lib.mkOption {
      default = { };
      description = "unpackmgr settings";
      type = mkOptionSubmodule {
        concurrency = lib.mkOption {
          default = 1;
          description = "unpackmgr concurrency";
          type = lib.types.ints.positive;
        };
      };
    };

    evalmgr = lib.mkOption {
      default = { };
      description = "evalmgr settings";
      type = mkOptionSubmodule {
        concurrency = lib.mkOption {
          default = 1;
          description = "evalmgr concurrency";
          type = lib.types.ints.positive;
        };
      };
    };

    extraSettings = lib.mkOption {
      default = [ ];
      description = "Extra settings written to settings.py";
      # TODO: This could be a DAG.
      type = with lib.types; let element = oneOf [ lines attrs ]; in coercedTo element (x: [ x ]) (listOf element);
    };
  };

  config =
    let
      python = pkgs.python38;
      package = python.pkgs.callPackage ./package.nix { };
      uwsgi = pkgs.uwsgi.override { plugins = [ "python3" ]; python3 = python; };
      # FIXME: This could probably be acomplished without this hackery
      celery = builtins.head (builtins.filter (x: lib.getName x == "celery") package.propagatedBuildInputs);

      writePython38 = pkgs.writers.makePythonWriter python pkgs.python38Packages /* FIXME: build packages? */ pkgs.python38Packages;
      writePython38Bin = name: writePython38 "/bin/${name}";

      finalSimpleSettings = baseSettings // (builtins.foldl' (a: b: a // b) { } (builtins.filter builtins.isAttrs cfg.extraSettings)) // {
        SERVER = "uwsgi";
        BROKER_URL = cfg.rabbitmqUrl;

        DATABASES.default = {
          ENGINE = "django.db.backends.postgresql";
          ATOMIC_REQUESTS = true;
          NAME = "sio2";
          USER = "sio2";
          PASSWORD = "";
          HOST = "";
        };
      };
      finalSettingsText = lib.concatMapStrings (x: if lib.hasSuffix "\n" x then x else x + "\n") ([
        "# Settings header\n"
        (builtins.readFile ./settings-header.py)
        "\n# Simple settings\n"
        (toPythonVars { } finalSimpleSettings)
        "\n# String values from extraSettings\n"
      ] ++ (builtins.filter builtins.isString cfg.extraSettings) ++ [
        "\n# Settings footer\n"
        (builtins.readFile ./settings-footer.py)
      ]);
      settingsDir = pkgs.runCommandLocal "settings-py-dir" { } ''
        mkdir -p $out
        ln -s ${pkgs.writeText "settings.py" finalSettingsText} $out/settings.py
      '';

      PYTHONPATH = "${settingsDir}:${python.pkgs.makePythonPath [ package ]}:/etc/sio2/";
      DJANGO_SETTINGS_MODULE = "settings";
      writePythonSio = name: script: writePython38 name { } ''
        # flake8: noqa
        import sys
        import os
        sys.path = ${toPythonValue {} (lib.splitString ":" PYTHONPATH)} + sys.path
        os.environ["DJANGO_SETTINGS_MODULE"] = ${toPythonValue {} DJANGO_SETTINGS_MODULE}

        ${script}
      '';
      writePythonSioBin = name: writePythonSio "/bin/${name}";

      managePy = writePythonSioBin "sio-manage" ''
        import sys
        from django.core.management import execute_from_command_line

        execute_from_command_line(sys.argv)
      '';
      wsgiPy = writePythonSio "wsgi.py" ''
        from django.core.wsgi import get_wsgi_application
        application = get_wsgi_application()
        import io
        input = io.StringIO()
        errors = io.StringIO()
        def noop(status, hh, exc_info=None):
            pass
        application({
            'CONTENT_LENGTH': '0',
            'CONTENT_TYPE': ' ',
            'DOCUMENT_ROOT': ' ',
            'HTTP_HOST': ' ',
            'PATH_INFO': '/api/ping',
            'REMOTE_ADDR': '127.0.0.1',
            'REMOTE_PORT': '60420',
            'REQUEST_METHOD': 'GET',
            'REQUEST_URI': '/api/ping',
            'SERVER_NAME': ' ',
            'SERVER_PORT': '80',
            'SERVER_PROTOCOL': 'HTTP/1.0',
            'uwsgi.node': ' ',
            'uwsgi.version': ' ',
            'wsgi.multiprocess': True,
            'wsgi.multithread': True,
            'wsgi.run_once': False,
            'wsgi.url_scheme': 'http',
            'wsgi.version': (1, 0),
            'wsgi.input': input,
            'wsgi.errors': errors,
        }, noop)
      '';
      notificationsServer = pkgs.callPackage ./notifications-server { };
    in
    lib.mkIf cfg.enable {
      users.extraUsers.sio2 = {
        isSystemUser = true;
        group = "sio2";
      };
      services.filetracker.ensureFiles = lib.mkIf cfg.defaultFiletrackerEnsureFiles {
        "/sandboxes/compiler-gcc.10_2_1.tar.gz" = pkgs.fetchurl {
          url = "https://downloads.sio2project.mimuw.edu.pl/sandboxes/compiler-gcc.10_2_1.tar.gz";
          hash = "sha256-+QO7/ZqLWRvFCF9KdVqrZ6ZsBB96bkRgYVUUezvAf8A=";
        };
        "/sandboxes/compiler-fpc.2_6_2.tar.gz" = pkgs.fetchurl {
          url = "https://downloads.sio2project.mimuw.edu.pl/sandboxes/compiler-fpc.2_6_2.tar.gz";
          hash = "sha256-bci/e++hKvWhVgK3uAHuhp5bl3salIj/j9/aYFZ8uKQ=";
        };
        "/sandboxes/exec-sandbox.tar.gz" = pkgs.fetchurl {
          url = "https://downloads.sio2project.mimuw.edu.pl/sandboxes/exec-sandbox.tar.gz";
          hash = "sha256-v482YOlf63OlgTwK5HvAuFgDFf739GvFXCbyX9nvRb4=";
        };
        "/sandboxes/proot-sandbox_amd64.tar.gz" = pkgs.fetchurl {
          url = "https://downloads.sio2project.mimuw.edu.pl/sandboxes/proot-sandbox_amd64.tar.gz";
          hash = "sha256-u6CSak326pAa7amYqYuHIqFu1VppItOXjFyFZgpf39w=";
        };
        "/sandboxes/talent_sio2jail_exec-sandbox-1.4.3.tar.gz" = pkgs.fetchurl {
          url = "https://otsrv.net/sandboxes/talent_sio2jail_exec-sandbox-1.4.3.tar.gz";
          hash = "sha256-WfEEY7giimcWcBzZFgcdtUO+EXUTumR9+BmXBwc10ss=";
        };
      };
      users.extraGroups.sio2 = { };

      environment.systemPackages = [ managePy ];

      services.nginx =
        if cfg.nginx != null then {
          enable = lib.mkDefault true;
          virtualHosts."oioioi" = {
            forceSSL = cfg.useSSL;
          } // cfg.nginx // {
            serverName = cfg.domain;

            locations."/static/CACHE/" = {
              alias = "/var/lib/sio2/static/CACHE/";
              extraConfig = ''
                gzip_static on;
                expires 1y;
              '';
            };

            locations."/static/" = {
              alias = "/var/lib/sio2/static/";
              extraConfig = ''
                gzip on;
                gzip_vary on;
                gzip_min_length 1024;
                gzip_proxied expired no-cache no-store private auth;
                gzip_types text/plain text/css application/javascript text/javascript;
                expires 1d;
              '';
            };

            locations."/socket.io/".extraConfig = ''
              proxy_pass http://127.0.0.1:7887;
              proxy_http_version 1.1;
              proxy_set_header Upgrade $http_upgrade;
              proxy_set_header Connection "Upgrade";
            '';

            locations."/".extraConfig = ''
              uwsgi_pass unix:///var/run/sio2/uwsgi.sock;
              include ${pkgs.nginx}/conf/uwsgi_params;
              uwsgi_read_timeout 1800;
            '';

            extraConfig = ''
              charset utf-8;

              client_max_body_size 1g;

              limit_req_status 429;
              keepalive_requests 1000;
              keepalive_timeout 360s 360s;
            '';
          };
        } else { };

      services.postgresql = {
        enable = true;
        ensureDatabases = [ "sio2" ];
        ensureUsers = [
          {
            name = "sio2";
            ensurePermissions = {
              "DATABASE sio2" = "ALL PRIVILEGES";
            };
          }
        ];
      };

      # FIXME: This should be disabled if rabbitmqUrl is changed from the default
      services.rabbitmq = {
        enable = true;
      };

      system.activationScripts = {
        copy-sio2-etc-defaults = ''
          if [[ ! -e /etc/sio2 ]]; then
            mkdir -m=775 -p /etc/sio2
            cp --no-preserve=all ${../oioioi/deployment/basic_settings.py.template} /etc/sio2/basic_settings.py
          fi
        '';
        oioioi-create-symlink = ''
          [ -d /var/run/sio2 ] || mkdir /var/run/sio2 || exit 1
          ln -sf ${wsgiPy} /var/run/sio2/wsgi.py || exit 1
        '';
      };

      services.sioworkersd.enable = true;

      users.extraGroups.sio2-filetracker = { };
      services.filetracker-cache-cleaner.paths = [ "/var/cache/sio2-filetracker-cache" ];
      services.sioworker.filetrackerCache = "/var/cache/sio2-filetracker-cache";

      systemd.tmpfiles.rules = [
        "d /var/cache/sio2-filetracker-cache 2770 root sio2-filetracker - -"
        "A /var/cache/sio2-filetracker-cache - - - - u::rwx,d:g::rwx,o::---"
      ];

      systemd.targets = {
        oioioi = {
          enable = true;
          wantedBy = [ "multi-user.target" ];
          description = "all OIOIOI services (grouped)";
        };
      };

      systemd.services =
        let
          mkSioProcess = { name, requiresDatabase ? false, requiresFiletracker ? false, ... }@x:
            let extraRequires = (lib.optionals requiresDatabase [ "postgresql.service" "sio2-migrate.service" ]) ++ (lib.optional requiresFiletracker "filetracker.service") ++ [ "sio2-rabbitmq.service" ];
            in
            {
              enable = true;
              description = "${name}, a part of SIO2";
              requires = (x.requires or [ ]) ++ extraRequires;
              partOf = [ "oioioi.target" ] ++ (x.partOf or [ ]);
              wantedBy = [ "oioioi.target" ] ++ (x.wantedBy or [ ]);
              after = [ "oioioi.target" ] ++ (x.wants or [ ]) ++ (x.requires or [ ]) ++ (x.after or [ ]) ++ extraRequires;

              environment = {
                # This is required for services that don't go through manage.py
                inherit DJANGO_SETTINGS_MODULE;
                inherit PYTHONPATH;
                FILETRACKER_FILE_MODE = "770";
              } // (x.environment or { });

              serviceConfig = {
                Type = "simple";

                ReadWritePaths = (lib.optional requiresFiletracker "/var/cache/sio2-filetracker-cache") ++ (x.ReadWritePaths or [ ]);
                SupplementaryGroups = (lib.optional requiresFiletracker "sio2-filetracker") ++ (x.SupplementaryGroups or [ ]);

                User = "sio2";
                Group = "sio2";
              } // {
                PrivateTmp = true;
                ProtectSystem = "strict";
                RemoveIPC = true;
                NoNewPrivileges = true;
                RestrictSUIDSGID = true;
                ProtectKernelTunables = true;
                ProtectControlGroups = true;
                ProtectKernelModules = true;
                ProtectKernelLogs = true;
                PrivateDevices = true;
              } // (builtins.removeAttrs (x.serviceConfig or { }) [ "ReadWritePaths" "SupplementaryGroups" ]);
            } // (builtins.removeAttrs x [ "name" "requiresDatabase" "requiresFiletracker" "requires" "after" "serviceConfig" "environment" ]);
        in
        {
          # The sioworker service has to be modified this way so it has access to the shared filetracker cache.
          sioworker = {
            serviceConfig = {
              ReadWritePaths = [ "/var/cache/sio2-filetracker-cache" ];
              SupplementaryGroups = [ "sio2-filetracker" ];
            };
            # This is required so that filetracker creates files with the 770 mode instead of 700 and the sio2-filetracker group has access to the files, this is also replicated in other sio2 services.
            environment.FILETRACKER_FILE_MODE = "770";
          };

          sio2-migrate = {
            enable = true;
            description = "SIO2 database migrator";
            after = [ "postgresql.service" ];
            requires = [ "postgresql.service" ];

            script =
              let
                hash = collectUniqueString [
                  (builtins.toString package)
                  (collectUniqueString finalSimpleSettings.DATABASES)
                ];
              in
              ''
                hashfile=/var/lib/sio2/last-migrate-hash
                if [[ ! -e "$hashfile" || $(cat "$hashfile") != "$hash" ]]; then
                  ${managePy}/bin/sio-manage migrate
                  echo -n "${hash}" >"$hashfile"
                fi
              '';

            serviceConfig = {
              Type = "simple";
              ReadOnlyPaths = "/";
              ReadWritePaths = [ "/tmp" ];
              StateDirectory = "sio2";
              User = "sio2";
              Group = "sio2";
            };
          };

          sio2-rabbitmq = {
            enable = true;
            description = "SIO2 rabbitmq setup";
            after = [ "rabbitmq.service" ];
            requires = [ "rabbitmq.service" ];

            path = [ pkgs.rabbitmq-server ];

            script = ''
              function rmqctl() {
                HOME=/tmp rabbitmqctl --erlang-cookie $(cat /var/lib/rabbitmq/.erlang.cookie) "$@"
              }

              if ! rmqctl list_users | grep oioioi; then
                rmqctl add_user oioioi oioioi
                rmqctl set_permissions oioioi '.*' '.*' '.*'
              fi
            '';

            serviceConfig = {
              Type = "simple";
              ReadOnlyPaths = "/";
              PrivateTmp = true;
            };
          };

          sio2-uwsgi = mkSioProcess rec {
            name = "uwsgi";
            requiresFiletracker = true;
            requiresDatabase = true;

            restartTriggers = [ script ];
            reloadIfChanged = true;

            wants = [ "notifications-server.service" ];

            # These units all have to be in the same namespace due to celery requiring a shared /tmp.
            unitConfig.JoinsNamespaceOf = [ "evalmgr.service" "unpackmgr.service" "receive_from_workers.service" ];

            script = ''
              exec ${uwsgi}/bin/uwsgi --plugin ${uwsgi}/lib/uwsgi/python3_plugin.so \
              -s /var/run/sio2/uwsgi.sock --umask=000 --master-fifo /var/run/sio2/uwsgi.fifo \
              --processes=${if cfg.uwsgi.concurrency == "auto" then "$(nproc)" else builtins.toString cfg.uwsgi.concurrency} \
              --lazy-apps -M --max-requests=5000 --disable-logging --need-app \
              --enable-threads --socket-timeout=30 --ignore-sigpipe \
              --ignore-write-errors --disable-write-exception \
              --wsgi-file=/var/run/sio2/wsgi.py
            '';

            reload = ''
              ${managePy}/bin/sio-manage collectstatic --no-input
              ${managePy}/bin/sio-manage compress --force
              ${managePy}/bin/sio-manage compilejsi18n
              echo c > /var/run/sio2/uwsgi.fifo
            '';
            serviceConfig = {
              ReadWritePaths = [ "/dev/shm" ];
              ExecStartPre = [
                "${managePy}/bin/sio-manage collectstatic --no-input"
                "${managePy}/bin/sio-manage compress --force"
                "${managePy}/bin/sio-manage compilejsi18n"
              ];
              KillSignal = "SIGINT";

              RuntimeDirectory = "sio2";
              StateDirectory = "sio2";
            };
          };

          notifications-server = mkSioProcess {
            name = "notifications-server";

            serviceConfig = {
              ExecStart = ''
                ${notificationsServer}/bin/notifications-server --port 7887 --amqp ${lib.escapeShellArg cfg.rabbitmqUrl} --url ${finalSimpleSettings.NOTIFICATIONS_SERVER_URL}
              '';
            };
          };

          rankingsd = mkSioProcess {
            name = "rankingsd";
            requiresDatabase = true;

            serviceConfig = {
              ExecStart = ''
                ${managePy}/bin/sio-manage rankingsd
              '';

              StateDirectory = "sio2";
            };
          };

          mailnotifyd = mkSioProcess {
            name = "mailnotifyd";
            requiresDatabase = true;

            serviceConfig = {
              ExecStart = ''
                ${managePy}/bin/sio-manage mailnotifyd
              '';

              StateDirectory = "sio2";
            };
          };

          unpackmgr = mkSioProcess {
            name = "unpackmgr";
            requiresFiletracker = true;
            requiresDatabase = true;

            wants = [ "evalmgr.service" ];

            unitConfig.JoinsNamespaceOf = [ "sio2-uwsgi.service" "evalmgr.service" "receive_from_workers.service" ];

            serviceConfig = {
              ExecStart = ''
                ${celery}/bin/celery -A oioioi.celery worker -n "%%h-unpackmgr" -E -Q unpackmgr -c ${builtins.toString cfg.unpackmgr.concurrency}
              '';

              StateDirectory = "sio2";
            };
          };

          evalmgr = mkSioProcess {
            name = "evalmgr";
            requiresFiletracker = true;
            requiresDatabase = true;

            wants = [ "sioworkersd.service" "receive_from_workers.service" ];

            unitConfig.JoinsNamespaceOf = [ "sio2-uwsgi.service" "unpackmgr.service" "receive_from_workers.service" ];

            serviceConfig = {
              ExecStart = ''
                ${celery}/bin/celery -A oioioi.celery worker -n "%%h-evalmgr" -E -Q evalmgr -c ${builtins.toString cfg.evalmgr.concurrency}
              '';

              StateDirectory = "sio2";
            };
          };

          receive_from_workers = mkSioProcess {
            name = "receive_from_workers";
            requiresDatabase = true;

            unitConfig.JoinsNamespaceOf = [ "sio2-uwsgi.service" "unpackmgr.service" "evalmgr.service" ];

            serviceConfig = {
              ExecStart = ''
                ${managePy}/bin/sio-manage start_receive_from_workers
              '';

              StateDirectory = "sio2";
            };
          };
        };
    };
}
