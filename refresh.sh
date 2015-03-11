dropdb -h localhost djangocon2015; createdb -h localhost djangocon2015 && gondor sqldump develop | ./manage.py dbshell && ./manage.py upgradedb -e
