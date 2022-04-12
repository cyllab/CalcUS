if not exist "data\" mkdir data
docker-compose down
docker-compose pull
docker image prune -f
docker-compose up --remove-orphans
pause
