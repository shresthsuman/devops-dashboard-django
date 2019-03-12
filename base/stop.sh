#!/bin/bash
# run this script from inside the vagrant box to start all dashboard services and the lb

# put all dashboard services here
# do sort them abc, except base has to be started at last!
SERVICES=(
    dashboard-backend
    dashboard-frontend
    base
)

pwd=`pwd`
# iterate over services and start them up
for s in "${SERVICES[@]}"
do
    cd $pwd/../${s}
    docker-compose stop &
done
