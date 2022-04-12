if not exist "data\" mkdir data
docker-compose down --remove-orphans
docker image prune -f
git pull
docker-compose -f dev-compose.yml build
docker-compose -f dev-compose.yml -f docker-compose.override.yml up
pause
