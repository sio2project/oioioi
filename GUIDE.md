# TAG - New Joiner onboarding - 2022 edition
A few useful tips for TAG new joiners. SIO2Project is a growing project mainly maintained by the TAG team.
The project's architecture was previously held on self-served platforms such as Gerrit, Hudson etc.
By the end of academic year 2022 most of the architecture was moved to GitHub.

* Gerrit (code review) -> GitHub code review
* Hudson (automated jobs) -> GitHub Actions

There are still some deployment jobs left on Hudson, but GitHub Secrets can be a bright future for OIOIOI.
All the tickets raised during development are still in Jira, and it is not intended to change that.

## Prepare your development environment
First things first - the best way to run OIOIOI (web service of SIO2Project) is to use Docker.
Any other installation method described in documentation does not work, so you just need to follow
instructions in `README.rst`. Using `docker-compose` works only on Linux and MacOS - Windows is not supported.

Install Docker and docker-compose on your computer - if you don't know how just type in `How to install Docker on XZY`,
where `XYZ` is your operating system. Do the same for `docker-compose`.

Remember to add user to docker group
```bash
sudo groupadd docker
gpasswd -a $USER docker
newgrp docker
```

All the commands below are being run in `oioioi` directory (main directory of the repository).
In order to use `easy_toolbox.py` alternative method, check python package requirements in `easy_toolbox.py`. 

To build OIOIOI image run 
```bash
OIOIOI_UID=$(id -u) docker-compose -f docker-compose-dev.yml -f extra/docker/docker-compose-dev-noserver.yml build
```
or
```bash
./easy_toolbox.py build  
```

Set your containers up and running
```bash
OIOIOI_UID=$(id -u) docker-compose -f docker-compose-dev.yml -f extra/docker/docker-compose-dev-noserver.yml up -d
```
or
```bash
./easy_toolbox.py up
```

Wait some time for the migration to finish (no more than a few minutes).

Run your web service
```bash
OIOIOI_UID=$(id -u) docker-compose -f docker-compose-dev.yml -f extra/docker/docker-compose-dev-noserver.yml exec web python3 manage.py runserver 0.0.0.0:8000
```
or
```bash
./easy_toolbox.py run
```

Now visit `localhost:8000` and start exploring OIOIOI.

## Run unit tests
In order to run unit tests Docker installation is required.
To do it just run
```bash
docker-compose -f docker-compose-dev.yml -f extra/docker/docker-compose-dev-noserver.yml exec "web" ../oioioi/test.sh
```
or
```bash
./easy_toolbox.py test
```

## Run e2e tests
In order to run Cypress tests a few more steps are required.
- Clear the database
- Create superuser (admin, admin)
- Run the service
- Run the tests

All of these steps can be done by running
```bash
./easy_toolbox.py flush-db && ./easy_toolbox.py add-superuser && ./easy_toolbox.py cypress-apply-settings && ./easy_toolbox.py run
```
and (in new terminal)
```bash
./test_cypress.sh [-g]
```

Normally these tests are being run on GitHub Actions as a nightly test workflow, but in the future it is intended
to create separate testing environment for Cypress using SQLite database and data from fixtures files.

## Contributing
In order to contribute to OIOIOI just `fork` the repository, clone the copy, make changes as in normal repository
and when the change is ready, create a push request to master branch of `sio2project/oioioi`.

## GitHub Actions
As mentioned above GitHub Actions replaced most of the Hudson jobs. Right now the available workflows are:
- Unit tests
- Nightly tests (unit tests with testes marked as 'slow')
- Bi-Nightly Cypress e2e tests
- Documentation generator
- Transifex translations downloader
- Transifex translations uploader

## Deployment
No changes can be seen on `szkopul.edu.pl` without deployment. 
@twalen is responsible for conducting the deployments, and they are usually done during
maintenance window (see `szkopul.edu.pl` main page for details).

During deployment translation files are being uploaded and downloaded. The translation manager is 
[Transifex](https://www.transifex.com/sio2project/sio2project/dashboard/). When you add localized text 
to OIOIOI it is uploaded to Transifex with GitHub Action and later, when translated, downloaded,
compiled and saved to the codebase. (Both of these jobs need to be run manually).

## Ticketing
All the ticketing is still done via [Jira](https://jira.sio2project.mimuw.edu.pl/).