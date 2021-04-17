#!/bin/bash
cd $(dirname $0)
pipenv run project/manage.py makemigrations
pipenv run project/manage.py migrate
xfce4-terminal --hold --geometry 66x16-0-0 --title=backend -e "pipenv run project/manage.py runserver" &