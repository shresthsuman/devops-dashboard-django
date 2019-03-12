# DevOps-Dashboard development environment

This repository is the entrypoint for development, it will provide an nginx
proxy, helper scripts and a vagrant box.

If you can run docker nativily on your workstation, you can ignore the
vagrant parts. The vagrantbox is just a helper if you can't use docker.

## pre requirements

* A shell (like git bash)

AND one of the following

* docker

OR

* virtualbox  (https://virtualbox.org)
* vagrant (https://vagrantup.com)

Vagrant will configure the VM with all needs and set the proxy stuff.

## Notes for Windows Users

To correctly handle line endings in the repository the following configuration command must be run __once__:
```
git config --global core.autocrlf input
```

## common usage (for native docker and vagrant)

You need to clone all repositories, or just run the get script:

### get script

We provide a little helper:

```
curl -fsSL -u $USER https://git.t-systems-mms.eu/projects/ip16dash/repos/base/browse/get.sh?raw | bash
```
In some cases this script won't work on MMS workstations, currently there is no
idea why.

### manually clone

```
mkdir ip16dash

cd ip16dash

git clone https://git.t-systems-mms.eu/scm/ip16dash/base.git
git clone https://git.t-systems-mms.eu/scm/ip16dash/dashboard-backend.git
git clone https://git.t-systems-mms.eu/scm/ip16dash/dashboard-frontend.git

cd base
```

## Usage with vagrant

If you need to use vagrant, just follow these steps:

```
# you need to be inside the base folder

vagrant up

# wait until the vm is ready

vagrant ssh

cd /shared/base

./start.sh
```

After everything has been build, you can connect to your env via https://localhost:8443

## usage with docker nativly

If you can run docker nativly, you just need to run the start script

```
# Create the shared network as it is marked as external
docker network create dashboard-net

cd base
./start.sh
```

### If you are using the Windows Subsystem Linux (WSL)

you need to create the `/etc/wsl.conf` with the contents
```bash
[automount]
root = /
```

After a while you can connect to your env via https://localhost

### Docker for Windows Drive Sharing in MMS-LAN
If you are unable to enable sharing of the disk drive, make sure that your Network settings define the correct subnet:  
Settings > Network > Subnet Address: 192.168.199.0  
([related TeamWeb page](http://teamweb.mms-at-work.de/display/comw10/2017/02/08/Docker+Shared+Drives+von+Firewall+blockiert))  
If it still doesn't work, see [this blog post](https://blog.olandese.nl/2017/05/03/solve-docker-for-windows-error-a-firewall-is-blocking-file-sharing-between-windows-and-the-containers/).

## helper scripts in detail

| script     | does...                                        |
|------------|------------------------------------------------|
| get.sh     | clone all repositories, call via curl          |
| pull.sh    | update all repositories, call from base folder |
| restart.sh | stop docker compose and start it again         |
| start.sh   | start all docker compose definitions           |
| stop.sh    | stops docker                                   |

## nginx proxy

The nginx proxy is definied in the base folder. If you want to add/edit/remove
a service, you need to update the `nginx/services.yml`. This will generate
an nginx config during the docker build process. If you need more details,
have a look into `nginx/nginx.rb`.