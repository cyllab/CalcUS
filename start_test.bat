if not exist "data\" mkdir data
docker-compose down --remove-orphans
docker-compose -f test-compose.yml -f test-compose.override.yml build
docker-compose -f test-compose.yml -f test-compose.override.yml up
pause
