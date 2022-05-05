#!/bin/bash

docker kill $(docker ps -a -q)
docker rm $(docker ps -a -q)
docker volume prune