import json
import datetime

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
JSON_FORMAT_VERSION = '1.1'

class MozBattueError(Exception):
    pass


def load_bugs(stream):
    data = json.load(stream)

    # check version
    version_ok = False
    if 'metadata' in data:
        version_ok = data['metadata'].get('version') == JSON_FORMAT_VERSION
    if not version_ok:
        raise MozBattueError("The json data is no more compatible with this "
                             "version - you should update the data.")
    bugs = data['bugs']

    for bug in bugs.itervalues():
        for intermittent in bug['intermittents']:
            intermittent['timestamp'] = \
                datetime.datetime.strptime(intermittent['timestamp'],
                                           DATETIME_FORMAT)
    return bugs

def dump_bugs(bugs, stream):
    def default(obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime(DATETIME_FORMAT)
        return obj

    data = {
        'metadata': {'version': JSON_FORMAT_VERSION},
        'bugs': bugs,
    }
    json.dump(data, stream, sort_keys=True, indent=4,
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
