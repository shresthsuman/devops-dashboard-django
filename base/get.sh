#!/bin/bash
# execute this script this way in your shell : curl -fsSL -u $USER https://git.t-systems-mms.eu/projects/ip16dash/repos/base/browse/get.sh?raw | bash
USER=${USER}
PATH_HERE=`pwd`
PATH_BASE="${PATH_HERE}ip16dash"
mkdir -p ${PATH_BASE}
cd $PATH_BASE

# repos
REPOS_DASHBOARD=(
   base
   dashboard-backend
   dashboard-frontend
)

# foreach repo, check if folder exists, if not, clone the repo
for repo in "${REPOS_DASHBOARD[@]}"
do
    REPO_FOLDER=${repo}
    if [ ! -d "${PATH_BASE}/${REPO_FOLDER}" ]; then
        git clone https://${USER}@git.t-systems-mms.eu/scm/ip16dash/${repo}.git
        if [ "${ARCH}" == "Cygwin" ]; then
            cd ${PATH_BASE}/${REPO_FOLDER}
            git config --local core.filemode false
            cd ${PATH_HERE}
        fi
    fi
done

