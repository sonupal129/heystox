# Heystox Trading

# Welcome to Heystox!

Hi!, Myself Sonu Pal python django developer and author of this app **Heystox**. is a equity/future trading software for intraday and week teading. I build with technologies like python,django,celery,redis and database is PSQL.


# Setup - DEV

1. Copy repo using git clone [repo].
2. Install python3 in system, create virtual env and install requirements.txt,
3. create database and update database credential in settings.py
4. Now we are good to go.

# Setup - Prod

1. Installation is same as DEV.
2. Add [local.py](www.google.com) file to overwrite dev setting to prod setting.
3. Install PG- Bouncer for postgres database to handle multiple connection request.
4. Install redis & supervisor. setup celery worker, beat & flower on supervisor, Using the [settings file](https://docs.google.com/document/d/1roeeR9gQgih32hz-N_qJDhgihkW7ui55qnAjHJZftNY/edit?usp=sharing).
5. Install nginx, gunicorn and setup them accordingly.  [settings file](https://docs.google.com/document/d/1roeeR9gQgih32hz-N_qJDhgihkW7ui55qnAjHJZftNY/edit?usp=sharing)
6. Now we are good to go.

## Thank You


