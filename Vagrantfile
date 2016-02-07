# -*- mode: ruby -*-
# vi: set ft=ruby :

# There are two environment variables that will be used to configure the box:
# - CLEANBOX if set, then Vagrant will set up a fresh installation of the box
#            instead of using the preinstalled one.
# - JUSTBOX  if set, then provisioners won't install and configure OIOIOI,
#            but the box will have all the dependencies installed.
# So to sum up:
# CLEANBOX + JUSTBOX  gives you a machine that can be used to create a new oioioibox
# CLEANBOX            gives you an OIOIOI installation on a fresh ubuntu image
# JUSTBOX             doesn't make much sense (gives you an untouched oioioibox)
# (nothing)           deploys OIOIOI on an oioioibox

# The most common configuration options are documented and commented below.
# For a complete reference, please see the online documentation at
# https://docs.vagrantup.com.
Vagrant.configure(2) do |config|

  if ENV['CLEANBOX']
    # There is a bug on 64-bit AMD processors with 64-bit
    # guest that results in system error while running solutions.
    # Similar issues:
    # https://groups.google.com/forum/#!msg/snipersim/gbGr1VbM2aw/xywdv0ZILL0J
    # https://groups.yahoo.com/neo/groups/pinheads/conversations/topics/9404
    # https://github.com/olimpiada/oitimetool-bin/issues/1
    config.vm.box = "ubuntu/trusty64"
  else
    config.vm.box = "oioioibox"
    config.vm.box_url = "http://ripper.dasie.mimuw.edu.pl/~sio2devel/vagrant/oioioibox/oioioibox.json"
  end

  if not ENV['JUSTBOX']
    config.vm.network "forwarded_port", guest: 8000, host: 8000 # SIO2 dev server
    config.vm.network "forwarded_port", guest: 7887, host: 7887 # notifications-server
    config.vm.network "forwarded_port", guest: 5432, host: 8001 # postgres

    config.vm.synced_folder ".", "/sio2/oioioi"
  end

  config.vm.provider "virtualbox" do |vb|
      # Change the default network card - this one is much faster on macs
      vb.customize ["modifyvm", :id, "--nictype1", "Am79C973"]

      vb.memory = 2048
      vb.cpus = 4
  end

  config.ssh.shell = "bash -c 'BASH_ENV=/etc/profile exec bash'"

  # This will set up a fresh installation of oioioibox
  if ENV['CLEANBOX']
    config.vm.provision "shell", inline: <<-SHELL
      header_spacer="================="

      # fix locale
      echo "$header_spacer Configuring locale"
      sudo echo 'LANGUAGE="en_US.UTF-8"' >> /etc/environment
      sudo echo 'LC_ALL="en_US.UTF-8"' >> /etc/environment
      sudo echo 'LANG="en_US.UTF-8"' >> /etc/environment
      export LANGUAGE=en_US.UTF-8
      export LANG=en_US.UTF-8
      export LC_ALL=en_US.UTF-8
      sudo locale-gen en_US.UTF-8
      sudo dpkg-reconfigure locales

      mkdir /sio2
      sudo chown vagrant:vagrant /sio2
    SHELL

    config.vm.provision "shell", privileged: false, inline: <<-SHELL
      export DEBIAN_FRONTEND=noninteractive
      header_spacer="================="

      # convenient shortucts in .bashrc
      echo "Configuring .bashrc"
      echo "source /sio2/venv/bin/activate" >> ~/.bashrc
      echo "cd /sio2" >> ~/.bashrc

      # install dependencies
      sudo apt-get update
      echo "$header_spacer Installing dependencies"
      function install_dep {
        echo "Installing: $@"
        sudo apt-get -y install "$@" 2>&1 >/dev/null | sed -n '/dpkg-preconfigure: unable to re-open stdin/ !p' >&2
        if [ ${PIPESTATUS[0]} -eq 0 ]; then
            echo "Done!"
        else
            echo "Installation returned an error code. Box may be not configured properly" 1>&2
        fi
      }
      install_dep git
      install_dep python-pip
      install_dep python-dev
      install_dep libpq-dev
      install_dep postgresql postgresql-contrib
      install_dep postgresql-client
      install_dep rabbitmq-server
      install_dep lighttpd
      install_dep fpc
      install_dep texlive-latex-base
      install_dep texlive-lang-polish
      install_dep texlive-latex-extra
      install_dep texlive-fonts-recommended
      install_dep gcc-multilib
      sudo dpkg --add-architecture i386
      sudo apt-get update
      install_dep libstdc++6:i386
      install_dep zlib1g:i386

      # install Node.js and lessc
      curl -sL https://deb.nodesource.com/setup_5.x | sudo -E bash -
      sudo apt-get install -y nodejs
      sudo npm install -g less

      # configure rabbitmq
      echo "$header_spacer Configuring rabbitmq"
      echo "[{rabbit, [{loopback_users, []}]}]." | sudo tee -a /etc/rabbitmq/rabbitmq.config

      # configure postgres
      echo "$header_spacer Configuring postgresql"
      function db_cmd {
      sudo -u postgres psql --command="$1"
      }
      db_cmd 'create user "vagrant"'
      db_cmd 'alter user "vagrant" with superuser'
      db_cmd 'create database "vagrant" with owner "vagrant"'
      db_cmd 'create user "oioioi" with password '"'development'"
      db_cmd 'create database "oioioi" with owner "oioioi"'

      echo "$header_spacer Installing OIOIOI dependencies"
      sudo pip install virtualenv
      cd /sio2
      virtualenv venv
      source venv/bin/activate
      if [ -d oioioi ]; then
        TMPOIOIOI=0
      else
        TMPOIOIOI=1
        git clone https://github.com/sio2project/oioioi
      fi
      mkdir wheels
      cd oioioi
      pip wheel --wheel-dir=/sio2/wheels -r requirements.txt
      pip install psycopg2
      cd ..
      if [ $TMPOIOIOI -eq 1 ]; then
        rm -rf oioioi
      fi

      # Download sandboxes
      mkdir sandboxes
      cd sandboxes
      sandboxes=$(curl -s https://downloads.sio2project.mimuw.edu.pl/sandboxes/Manifest)
      for sandbox in $sandboxes; do
        curl -s -O https://downloads.sio2project.mimuw.edu.pl/sandboxes/${sandbox}.tar.gz
      done
    SHELL
  end

  if ENV['JUSTBOX']
    # This will force ssh key regeneration at next vagrant up - used for creating new oioioibox
    config.vm.provision "shell", privileged: false, inline: <<-SHELL
      curl -s 'https://raw.githubusercontent.com/mitchellh/vagrant/master/keys/vagrant.pub' > /home/vagrant/.ssh/authorized_keys
      echo "Insecure key placed"
    SHELL
  else
    # Sets up OIOIOI
    config.vm.provision "shell", privileged: false, inline: <<-SHELL
      source /sio2/venv/bin/activate
      cd /sio2/oioioi
      pip install --find-link=/sio2/wheels -r requirements.txt
      cd ..
      oioioi-create-config deployment
      cd deployment

      echo "Configuring OIOIOI"
      sed -i "s/'ENGINE': 'django.db.backends.'/'ENGINE': 'django.db.backends.postgresql_psycopg2'/g;\
              s/'NAME': '',/'NAME': 'oioioi',/g;\
              s/'USER': '',/'USER': 'oioioi',/g;\
              s/'PASSWORD': '',/'PASSWORD': 'development',/g;\
              s/#BROKER_URL/BROKER_URL/g;\
              s/USE_UNSAFE_EXEC/#USE_UNSAFE_EXEC/g;\
              s/USE_LOCAL_COMPILERS/#USE_LOCAL_COMPILERS/g;\
              s/#FILETRACKER_SERVER_ENABLED/FILETRACKER_SERVER_ENABLED/g;\
              s/#FILETRACKER_LISTEN_ADDR/FILETRACKER_LISTEN_ADDR/g;\
              s/#FILETRACKER_LISTEN_PORT/FILETRACKER_LISTEN_PORT/g;\
              s/'HOST': '',/'HOST': 'localhost',/g" settings.py

      echo "Preparing database"
      # This has to run first until the migration ordering problem is fixed
      ./manage.py migrate auth
      ./manage.py migrate
      echo "Downloading sandboxes"
      # -y agrees to the license, -q disables interactive progress bars
      # -c specifies the cache path
      ./manage.py download_sandboxes -y -q -c /sio2/sandboxes

      echo "Setup finished"
      echo "Please log in, go to /sio2/deployment, and run ./manage.py createsuperuser"
      echo "THIS MACHINE HAS BEEN CONFIGURED FOR DEVELOPMENT PURPOSES ONLY. NEVER USE IT IN PRODUCTION ENVIRONMENT" 1>&2
    SHELL

    # Launches OIOIOI
    config.vm.provision "shell", privileged: false, run: "always", inline: <<-SHELL
        source /sio2/venv/bin/activate
        echo "Launching OIOIOI"
        cd /sio2/deployment
        mkdir -p ../logs
        mkdir -p ../logs/supervisor
        mkdir -p ../logs/runserver
        mkdir -p ../logs/worker

        nohup ./manage.py runserver 0.0.0.0:8000 >../logs/runserver/out.log 2>../logs/runserver/err.log &
        nohup ./manage.py supervisor >../logs/supervisor/out.log 2>../logs/supervisor/err.log &
        nohup sio-celery-worker amqp://guest:guest@localhost:5672// >../logs/worker/out.log 2>../logs/worker/err.log &
        echo "Done!"
    SHELL
  end

end
