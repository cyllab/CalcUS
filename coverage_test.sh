#!/bin/bash

coverage run --concurrency=multiprocessing manage.py test | tee test_output
coverage combine
