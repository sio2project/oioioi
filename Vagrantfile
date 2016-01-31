# -*- mode: ruby -*-
# vi: set ft=ruby :

# We need Facter in order to determine processor architecture.
unless Vagrant.has_plugin?("facter")
    system "vagrant plugin install facter"
    exec "vagrant #{ARGV.join(' ')}"
end

# All Vagrant configuration is done below. The "2" in Vagrant.configure
# configures the configuration version (we support older styles for
# backwards compatibility). Please don't change it unless you know what
# you're doing.
Vagrant.configure(2) do |config|
  # The most common configuration options are documented and commented below.
  # For a complete reference, please see the online documentation at
  # https://docs.vagrantup.com.

  # Every Vagrant development environment requires a box. You can search for
  # boxes at https://atlas.hashicorp.com/search.

  processor = Facter.value(:processor0)
  architecture = Facter.value(:architecture)
  if architecture.include? "i386" or processor.include? "AMD"
    # Obviously, we need 32-bit system if we have 32-bit processor.
    # Less obviously, there is a bug on 64-bit AMD processors with 64-bit
    # guest that results in system error while running solutions.
    # Similar issues:
    # https://groups.google.com/forum/#!msg/snipersim/gbGr1VbM2aw/xywdv0ZILL0J
    # https://groups.yahoo.com/neo/groups/pinheads/conversations/topics/9404
    # https://github.com/olimpiada/oitimetool-bin/issues/1
    config.vm.box = "ubuntu/trusty32"
  else
    config.vm.box = "ubuntu/trusty64"
  end

  # Disable automatic box update checking. If you disable this, then
  # boxes will only be checked for updates when the user runs
  # `vagrant box outdated`. This is not recommended.
  # config.vm.box_check_update = false

  # Create a forwarded port mapping which allows access to a specific port
  # within the machine from a port on the host machine. In the example below,
  # accessing "localhost:8080" will access port 80 on the guest machine.
  # config.vm.network "forwarded_port", guest: 80, host: 8080
  config.vm.network "forwarded_port", guest: 8000, host: 8000 # SIO2 dev server
  config.vm.network "forwarded_port", guest: 7887, host: 7887 # notifications-server
  config.vm.network "forwarded_port", guest: 5432, host: 8001 # postgres

  # Create a private network, which allows host-only access to the machine
  # using a specific IP.
  # config.vm.network "private_network", ip: "192.168.33.10"

  # Create a public network, which generally matched to bridged network.
  # Bridged networks make the machine appear as another physical device on
  # your network.
  # config.vm.network "public_network"

  # Share an additional folder to the guest VM. The first argument is
  # the path on the host to the actual folder. The second argument is
  # the path on the guest to mount the folder. And the optional third
  # argument is a set of non-required options.
  config.vm.synced_folder ".", "/sio2/oioioi"

  # Provider-specific configuration so you can fine-tune various
  # backing providers for Vagrant. These expose provider-specific options.
  # Example for VirtualBox:
  #
  config.vm.provider "virtualbox" do |vb|
  #   # Display the VirtualBox GUI when booting the machine
  #   vb.gui = true
  #
  #   # Customize the amount of memory on the VM:
      vb.memory = "2048"

      vb.cpus = 4
  end
  #
  # View the documentation for the provider you are using for more
  # information on available options.

  # Define a Vagrant Push strategy for pushing to Atlas. Other push strategies
  # such as FTP and Heroku are also available. See the documentation at
  # https://docs.vagrantup.com/v2/push/atlas.html for more information.
  # config.push.define "atlas" do |push|
  #   push.app = "YOUR_ATLAS_USERNAME/YOUR_APPLICATION_NAME"
  # end

  # Enable provisioning with a shell script. Additional provisioners such as
  # Puppet, Chef, Ansible, Salt, and Docker are also available. Please see the
  # documentation for more information about their specific syntax and use.

  config.ssh.shell = "bash -c 'BASH_ENV=/etc/profile exec bash'"

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

    sudo chown vagrant:vagrant /sio2
  SHELL



  config.vm.provision "shell", privileged: false, inline: <<-SHELL

    export DEBIAN_FRONTEND=noninteractive
    header_spacer="================="

    # convenient .bashrc
    echo "$header_spacer Configuring .bashrc"
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
    install_dep node-less
    install_dep rabbitmq-server
    install_dep lighttpd
    install_dep gcc-multilib
    sudo dpkg --add-architecture i386
    sudo apt-get update
    install_dep libstdc++6:i386
    install_dep zlib1g:i386

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

    echo "$header_spacer Installing OIOIOI"
    sudo pip install virtualenv
    cd /sio2/
    virtualenv venv
    source venv/bin/activate
    cd oioioi
    pip install -r requirements.txt
    pip install psycopg2
    cd ..
    oioioi-create-config deployment
    cd deployment

    echo "$header_spacer Configuring OIOIOI"
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

    pip install sioworkers

    echo "$header_spacer Preparing database"
    ./manage.py migrate
    echo "$header_spacer Downloading sandboxes"
    # -y agrees to the license, -q disables interactive progress bars
    ./manage.py download_sandboxes -y -q

    echo "Setup finished"
    echo "Please log in, go to /sio2/deployment, and run ./manage.py createsuperuser"
    echo "THIS MACHINE HAS BEEN CONFIGURED FOR DEVELOPMENT PURPOSES ONLY. NEVER USE IT IN PRODUCTION ENVIRONMENT" 1>&2
  SHELL

  # Launches OIOIOI
  config.vm.provision "shell", privileged: false, run: "always", inline: <<-SHELL
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
