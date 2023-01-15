#!/bin/bash
set -e

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

LOGFILE="oioioi.log"
true >"$LOGFILE"

echot() {
  echo "$@" | tee >>"$LOGFILE"
}

if (( $# == 0 )); then
  set -- "start"
fi

command_exists() {
  command -v "$@" >/dev/null 2>&1
}

user="$(id -un 2>/dev/null || true)"
run_as_root=""
if [ "$user" != "root" ]; then
  if command_exists sudo; then
    run_as_root='sudo'
  else
    cat >&2 <<-'EOF'
Error: this program needs the ability to run commands as root.
We are unable to find "sudo" available to make this happen.
EOF
    exit 1
  fi
fi

run_docker="$run_as_root"
if groups | grep -q docker -; then
  run_docker="";
fi
OIOIOI_CONFIGDIR="${XDG_CONFIG_HOME:-$HOME/.config}"/oioioi
docker_compose_fun_verbose() {
  $run_docker env "PATH==$PATH" "OIOIOI_CONFIGDIR=$OIOIOI_CONFIGDIR" "OIOIOI_VERSION=$OIOIOI_VERSION" docker-compose -p oioioi "$@"
}
docker_compose_fun() {
  docker_compose_fun_verbose "$@" >>"$LOGFILE" 2>&1
}

activate_python() {
  source .venv/bin/activate
  OIOIOI_VERSION="$(python helpers/read_manifest.py version)"
}

# get_distribution() adapted from docker sources
get_distribution() {
  lsb_dist=""
  if [ -r /etc/os-release ]; then
    lsb_dist="$(. /etc/os-release && echo "$ID")"
  fi
  lsb_dist="$(echo "$lsb_dist" | tr '[:upper:]' '[:lower:]')"

  # Check if this is a forked Linux distro
  # Check for lsb_release command existence, it usually exists in forked distros
  if command_exists lsb_release; then
    # Check if the `-u` option is supported
    set +e
    lsb_release -a -u >/dev/null 2>&1
    lsb_release_exit_code=$?
    set -e

    # Check if the command has exited successfully, it means we're in a forked distro
    if [ "$lsb_release_exit_code" = "0" ]; then
      # Get the upstream release info
      lsb_dist=$(lsb_release -a -u 2>&1 | tr '[:upper:]' '[:lower:]' | grep -E 'id' | cut -d ':' -f 2 | tr -d '[:space:]')
    else
      if [ -r /etc/debian_version ] && [ "$lsb_dist" != "ubuntu" ] && [ "$lsb_dist" != "raspbian" ]; then
        if [ "$lsb_dist" = "osmc" ]; then
          # OSMC runs Raspbian
          lsb_dist=raspbian
        else
          # We're Debian and don't even know it!
          lsb_dist=debian
        fi
      fi
    fi
  fi

  # Returning an empty string here should be alright since the
  # case statements don't act unless you provide an actual value
  echo "$lsb_dist"
}

install_python_venv() {
  user="$(id -un 2>/dev/null || true)"

  sh_c='sh -c'
  if [ "$user" != 'root' ]; then
    if command_exists sudo; then
      sh_c='sudo -E sh -c'
    elif command_exists su; then
      sh_c='su -c'
    else
      cat >&2 <<-'EOF'
Error: this installer needs the ability to run commands as root.
We are unable to find either "sudo" or "su" available to make this happen.
EOF
      exit 1
    fi
  fi

  # perform some rudimentary platform detection
  lsb_dist=$(get_distribution)

  # run setup for each distro accordingly
  case "$lsb_dist" in
    ubuntu|debian|raspbian)
      $sh_c 'apt-get install -y python3-venv' >>"$LOGFILE" 2>&1
    ;;
    *)
      # all other supported distros should have ensure-pip already installed
      cat >&2 <<-'EOF'
Python venv module with ensure-pip is required. Please check your distro
documentation on instructions how to install it.
EOF
      exit 1
    ;;
  esac
}


case "$1" in
  install)
    echot "Installation has started. Please wait..."
    # install python venv module
    python3 -c "import venv" >/dev/null 2>&1 || install_python_venv
    # create and activate venv
    python3 -m venv .venv
    activate_python
    # install python dependencies
    pip install -r requirements.txt >>"$LOGFILE" 2>&1
    # install docker
    command_exists docker || python helpers/install_docker.py >>"$LOGFILE" 2>&1
    # create basic settings
    mkdir -p "$OIOIOI_CONFIGDIR"
    clear
    python helpers/create_settings.py "$OIOIOI_CONFIGDIR"
    clear
    echot "Downloading images..."
    docker_compose_fun pull
    echot "Initializing the database..."
    docker_compose_fun run --rm web ./manage.py migrate
    docker_compose_fun run --rm web ./manage.py loaddata /sio2/oioioi/oioioi/admin_admin_fixture.json
    docker_compose_fun stop
    echot "Your admin password is \"admin\". Don't forget to change it!"
  ;;

  start)
    activate_python
    docker_compose_fun up -d
  ;;

  stop)
    activate_python
    docker_compose_fun stop
  ;;

  clean-start)
    activate_python
    docker_compose_fun up -d --force-recreate
  ;;

  delete-data)
    activate_python
    docker_compose_fun down -v
  ;;

  update)
    activate_python
    echot "Clearing old containers..."
    docker_compose_fun down
    # updating oioioi
    python helpers/update_oioioi.py "$PWD" "$OIOIOI_VERSION" "$2"
    case "$?" in
      0)
        exec ./oioioi.sh update2 "$OIOIOI_VERSION"
      ;;
      3)
        echot "Already on a newer version."
        exit 0
      ;;
      *)
        echot "Can not find a new version."
        exit 1
      ;;
    esac
  ;;

  update2)
    OIOIOI_OLD_VERSION="$2"
    rm -rf .venv
    python3 -m venv .venv
    activate_python
    # install python dependencies
    pip install -r requirements.txt >>"$LOGFILE" 2>&1
    clear
    # update basic settings
    python helpers/create_settings.py "$OIOIOI_CONFIGDIR"
    clear
    echot "Redownloading images..."
    docker_compose_fun pull
    echot "Reinitializing the database..."
    docker_compose_fun run --rm web ./manage.py migrate
    docker_compose_fun stop
    echot "Updated from $OIOIOI_OLD_VERSION to $OIOIOI_VERSION."
  ;;

  *)
    echot "Invalid command!"
  ;;
esac
