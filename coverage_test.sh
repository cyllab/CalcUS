#!/bin/bash

coverage run -p --concurrency=multiprocessing manage.py test | tee test_output
coverage combine
