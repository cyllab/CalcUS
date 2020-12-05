#!/bin/sh

#Change the password in case the user already exists
( rabbitmqctl wait --timeout 60 $RABBITMQ_PID_FILE ; \
rabbitmqctl add_user $CALCUS_RABBITMQ_USERNAME $CALCUS_RABBITMQ_PASSWORD 2>/dev/null ; \
rabbitmqctl set_user_tags $CALCUS_RABBITMQ_USERNAME  administrator ; \
rabbitmqctl change_password  $CALCUS_RABBITMQ_USERNAME $CALCUS_RABBITMQ_PASSWORD 2>/dev/null
rabbitmqctl set_permissions -p / $CALCUS_RABBITMQ_USERNAME  ".*" ".*" ".*" ;) &

rabbitmq-server $@
