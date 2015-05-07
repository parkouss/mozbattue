import json
import datetime

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'


class MozBattueError(Exception):
    pass


def load_bugs(stream):
    bugs = json.load(stream)
    for intermittents in bugs.itervalues():
        for intermittent in intermittents:
            intermittent['timestamp'] = \
                datetime.datetime.strptime(intermittent['timestamp'],
                                           DATETIME_FORMAT)
    return bugs

def dump_bugs(bugs, stream):
    def default(obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime(DATETIME_FORMAT)
        return obj
    json.dump(bugs, stream, sort_keys=True, indent=4,
              separators=(',', ': '), default=default)


def load_bugs_from_file(fname):
    try:
        with open(fname) as f:
            return load_bugs(f)
    except IOError, exc:
        raise MozBattueError("Unable to load bug data from %r: %s"
                             % (fname, exc))


def intermittents_by_time(intermittents):
    return sorted(intermittents, key=lambda i:i['timestamp'])
