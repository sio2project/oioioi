# -*- mode: ruby -*-
# vi: set ft=ruby :

require 'yaml'

def default(id, fallback)
  return (if id then id else fallback end)
end

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/trusty64"
  config.vm.box_check_update = false


  CFG_FILE = 'vagrant.yml'
  settings =
    if File.file? CFG_FILE
    then YAML.load_file CFG_FILE
    else {}
    end

  oioioi_port = default(settings['port'], 8000)
  runserver_cmd = default(settings['runserver_cmd'], 'runserver')

  config.vm.network "forwarded_port", guest: oioioi_port, host: oioioi_port
  config.vm.synced_folder ".", "/sio2/oioioi/"

  config.vm.provider "virtualbox" do |vb|
    vb.customize ["modifyvm", :id, "--nictype1", "Am79C973"]
    vb.gui    = false
    vb.memory = 2048
    vb.cpus   = 1
  end

  config.ssh.username = "vagrant"
  config.ssh.password = "vagrant"
  config.ssh.shell = "bash -c 'BASH_ENV=/etc/profile exec bash'"

  config.vm.provision "shell", privileged: true, inline: <<-SHELL
    mkdir -pv /sio2/logs
    chown vagrant:vagrant /sio2
    useradd -U worker -m -d /home/worker
    chmod a+rw -R /sio2/logs
  SHELL

  config.vm.provision "shell", privileged: false, inline: <<-SHELL
    echo "* configuring .bashrc"
    echo "source /sio2/venv/bin/activate" >> ~/.bashrc
    echo "cd /sio2" >> ~/.bashrc


    echo "* installing dependencies"
    sudo apt-get update
    sudo apt-get install -y git
    sudo apt-get install -y python-pip
    sudo apt-get install -y python-dev
    sudo apt-get install -y libpq-dev
    sudo apt-get install -y postgresql
    sudo apt-get install -y postgresql-contrib
    sudo apt-get install -y postgresql-client
    sudo apt-get install -y rabbitmq-server
    sudo apt-get install -y lighttpd
    sudo apt-get install -y fpc
    sudo apt-get install -y texlive-latex-base
    sudo apt-get install -y texlive-lang-polish
    sudo apt-get install -y texlive-latex-extra
    sudo apt-get install -y texlive-fonts-recommended
    sudo apt-get install -y gcc-multilib

    sudo dpkg --add-architecture i386

    sudo apt-get update
    sudo apt-get install -y libstdc++6:i386
    sudo apt-get install -y zlib1g:i386

    sudo apt-get install -y nodejs
    sudo apt-get install -y node
    sudo apt-get install -y npm
    sudo ln -vfs /usr/bin/nodejs /usr/bin/node
    sudo ln -vfs /usr/bin/nodejs /usr/sbin/node #????
    sudo npm -g install less


    echo "* configuring rabbitmq-server"
    echo "[{rabbit, [{tcp_listeners, [5672]}, {loopback_users, []}]}]." | \
        sudo tee /etc/rabbitmq/rabbitmq.config
    echo "\"SERVER_ERL_ARGS="+K true +A 4 +P 1048576 -kernel\" | \
        sudo tee /etc/rabbitmq/rabbitmq-env.conf


    echo "* configuring postgresql"
    sudo -u postgres psql --command='create user "vagrant"'
    sudo -u postgres psql --command='alter user "vagrant" with superuser'
    sudo -u postgres psql --command='create database "vagrant" with owner "vagrant"'
    sudo -u postgres psql --command='create user "oioioi" with password '"'development'"
    sudo -u postgres psql --command='create database "oioioi" with owner "oioioi"'


    echo "* installing python dependencies"
    cd /sio2

    sudo pip install virtualenv
    virtualenv venv
    source venv/bin/activate

    cd oioioi
    easy_install distribute
    pip install -r requirements.txt
    pip install psycopg2
    cd ..


    echo "* configuring deployment"
    oioioi-create-config deployment
    cd deployment

    sed -i -e "s/django.db.backends./django.db.backends.postgresql_psycopg2/g;\
               s/'NAME': ''/'NAME': 'oioioi'/g;\
               s/'USER': ''/'USER': 'oioioi'/g;\
               s/'HOST': '',/'HOST': 'localhost',/g;\
               s/'PASSWORD': ''/'PASSWORD': 'development'/g;\
               s/#BROKER_URL/BROKER_URL/g;\
               s/USE_UNSAFE_EXEC/#USE_UNSAFE_EXEC/g;\
               s/USE_LOCAL_COMPILERS/#USE_LOCAL_COMPILERS/g;\
               s/#FILETRACKER_SERVER_ENABLED/FILETRACKER_SERVER_ENABLED/g;\
               s/#FILETRACKER_LISTEN_ADDR/FILETRACKER_LISTEN_ADDR/g;\
               s/#FILETRACKER_LISTEN_PORT/FILETRACKER_LISTEN_PORT/g;\
               s/#FILETRACKER_LISTEN_URL/FILETRACKER_LISTEN_URL/g;\
               s/#SIOWORKERS_LISTEN_ADDR/SIOWORKERS_LISTEN_ADDR/g;\
               s/#SIOWORKERS_LISTEN_PORT/SIOWORKERS_LISTEN_PORT/g;\
               s/#RUN_SIOWORKERSD.*$/RUN_SIOWORKERSD = True/g;\
               s/#USE_UNSAFE_EXEC = True/USE_UNSAFE_EXEC = False/g;\
               s/#USE_LOCAL_COMPILERS = True/USE_LOCAL_COMPILERS = False/g;\
               s/#USE_UNSAFE_CHECKER = True/USE_UNSAFE_CHECKER = False/g;\
               s/.*RUN_LOCAL_WORKERS = True/RUN_LOCAL_WORKERS = False/g"\
            -e "/INSTALLED_APPS =/a'oioioi.workers',"\
            settings.py

    echo "SIOWORKERS_BACKEND = 'oioioi.sioworkers.backends.SioworkersdBackend'" \
        >> settings.py
    echo "CELERY_RESULT_BACKEND = None" >> settings.py

    # otherwise the Debug Toolbar won't work: http://blog.joshcrompton.com/2014/01/how-to-make-django-debug-toolbar-display-when-using-vagrant/
    echo "INTERNAL_IPS = ('127.0.0.1', '10.0.2.2')" >> settings.py


    echo "* migrating databases"
    ./manage.py migrate auth
    ./manage.py migrate


    echo "* downloading sandboxes"
    cd ..
    mkdir sandboxes
    cd sandboxes

    sandboxes=$(curl -s https://downloads.sio2project.mimuw.edu.pl/sandboxes/Manifest)
    for sandbox in $sandboxes; do
      curl -s -O https://downloads.sio2project.mimuw.edu.pl/sandboxes/${sandbox}.tar.gz
    done

    cd ../deployment/
    ./manage.py download_sandboxes -q -y -c /sio2/sandboxes
    cd ..


    echo "* done, please remember to createsuperuser"

  SHELL

  config.vm.provision "shell", privileged: false, run: "always", inline: <<-SHELL
    echo "Launching OIOIOI"

    sudo /etc/init.d/rabbitmq-server start
    sudo /etc/init.d/postgresql start

    cd /sio2/deployment
    source ../venv/bin/activate

    mkdir -p ../logs/{supervisor,runserver}

    nohup ./manage.py #{runserver_cmd} 0.0.0.0:#{oioioi_port} \
        >../logs/runserver/out.log 2>../logs/runserver/err.log &
    nohup ./manage.py supervisor \
        >../logs/supervisor/out.log 2>../logs/supervisor/err.log &

    cd ..

    sudo -u worker -i bash -c "\
        source /sio2/venv/bin/activate; \
        export FILETRACKER_URL=\"http://127.0.0.1:9999\"; \
        twistd --pidfile=/home/worker/worker.pid \
            -l /sio2/logs/worker.log worker -n worker -c 2 127.0.0.1"

    echo "Done!"
  SHELL
end
