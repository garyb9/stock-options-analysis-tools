import os
import psutil
from datetime import datetime
from dateutil.parser import parse

def start_timer():
    return datetime.now()

def get_timer(start):
    return str(datetime.now() - start)

def print_time(start):
    print('Runtime in seconds => ' + str(datetime.now() - start))

def print_mem():
    process = psutil.Process(os.getpid())
    print('MB used => ' + str(process.memory_info().rss / 10**6))   # in MB

def print_run_data(start):
    print_mem()
    print_time(start)

def is_date(string, fuzzy=False):
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try:
        parse(string, fuzzy=fuzzy)
        return True

    except ValueError:
        return False
