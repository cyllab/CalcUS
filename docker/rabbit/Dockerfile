FROM rabbitmq

ENV RABBITMQ_USER calcus
ENV RABBITMQ_PASSWORD rabbitmqcalcuspassword
ENV RABBITMQ_PID_FILE /var/lib/rabbitmq/mnesia/rabbitmq

ADD init.sh /init.sh
RUN chmod +x /init.sh

CMD ["/init.sh"]
