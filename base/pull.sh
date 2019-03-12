#!/bin/bash
USER=${USER}
PATH_BASE=`pwd`

# repos
REPOS=(
   dashboard-backend
   dashboard-frontend
)

# iterate projects
for p in "${REPOS[@]}"
do
    echo ">>>> pulling ${p}"
    REPO_FOLDER=${p}
    cd ${PATH_BASE}/../${REPO_FOLDER}
    git pull
done

cd ${PATH_BASE}
