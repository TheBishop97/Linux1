#!/bin/sh
set -e

host=""
shift
cmd=""

echo "Waiting for postgres at ..."

until pg_isready -h "" -p 5432; do
  sleep 2
done

echo "Postgres is ready! Executing command..."
exec 
