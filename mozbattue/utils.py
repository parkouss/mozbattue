import json
import datetime
import logging
import re
import os
import ConfigParser

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
JSON_FORMAT_VERSION = '1.2'

LOG = logging.getLogger('mozbattue')


def get_default_conf_path():
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'mozbattue.ini'
    )


class MozBattueError(Exception):
    pass


def load_bugs(stream, kept_no_intermittents=False, filter_intermittents=None):
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

    if filter_intermittents:
        for bugid, bug in bugs.items():
            intermittents = [i for i in bug['intermittents']
                             if filter_intermittents(i)]
            bug['intermittents'] = intermittents

    if not kept_no_intermittents:
        for bugid, bug in bugs.items():
            if not bug['intermittents']:
                del bugs[bugid]

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


def load_bugs_from_file(fname, kept_no_intermittents=False,
                        filter_intermittents=None):
    try:
        with open(fname) as f:
            return load_bugs(f, kept_no_intermittents=kept_no_intermittents,
                             filter_intermittents=filter_intermittents)
    except IOError, exc:
        raise MozBattueError("Unable to load bug data from %r: %s"
                             % (fname, exc))


def intermittents_by_time(intermittents):
    return sorted(intermittents, key=lambda i: i['timestamp'])


class IntermittentFilter(object):
    def __init__(self):
        self.regexes = []

    def add_filter_regex(self, regex):
        if isinstance(regex, basestring):
            regex = re.compile(regex)
        self.regexes.append(regex)

    def __call__(self, intermittent):
        for regex in self.regexes:
            if regex.match(intermittent['buildname']):
                return False
        return True


def comma_set(conf, section, option):
    value = conf.get(section, option)
    values = [v.strip() for v in value.split(',')]
    return set(v for v in values if v)


class Config(ConfigParser.ConfigParser):
    opts_conv = {
        'display-list': {
            'min_intermittents': ConfigParser.ConfigParser.getint,
            'show_resolved': ConfigParser.ConfigParser.getboolean,
            'show_assigned_to': ConfigParser.ConfigParser.getboolean,
            'filter_products': comma_set,
        }
    }

    def convert(self, section, option):
        try:
            conv = self.opts_conv[section][option]
        except KeyError:
            conv = ConfigParser.ConfigParser.get
        return conv(self, section, option)

    def get_default(self, section, name, default=None):
        try:
            return self.get(section, name)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default

    def create_filter_intermittents(self):
        regexes = self.get_default("display", 'intermittents_filter_buildname')
        if regexes:
            filter = IntermittentFilter()
            for regex in regexes.splitlines():
                if regex:
                    filter.add_filter_regex(regex)
            return filter
        return None

    def get_defaults(self, section):
        try:
            options = self.options(section)
        except ConfigParser.NoSectionError:
            return {}
        result = {}
        for opt in options:
            result[opt] = self.convert(section, opt)
        return result
