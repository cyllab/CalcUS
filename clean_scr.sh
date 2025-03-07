#!/bin/bash

find scr/ -type d -mtime +15 | xargs rm -r
