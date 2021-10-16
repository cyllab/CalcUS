#!/bin/bash

coverage run -p --concurrency=multiprocessing manage.py test 2>&1 | tee test_run
coverage combine
coverage html
coverage report
