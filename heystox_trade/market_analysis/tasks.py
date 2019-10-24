from celery import Celery
from celery.decorators import task

@task
def add(x,y):
    total = x + y
    return total
# app = Celery('tasks', broker='redis://localhost')