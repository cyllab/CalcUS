#!/bin/bash

coverage run -p --concurrency=multiprocessing manage.py test
coverage combine
coverage report
