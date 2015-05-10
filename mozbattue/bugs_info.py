import sys
from mozbattue.utils import intermittents_by_time


def bug_list(raw_bugs, filter=None, sort_by=()):
    bugs = []
    for bugid, bug in raw_bugs.iteritems():
        intermittents = bug['intermittents']
        oldest = intermittents_by_time(intermittents)[0]
        bugs.append({
            'id': bugid,
            'nb': len(intermittents),
            'date': oldest['timestamp'],
            'rev': oldest['revision'],
            'status': bug['status'],
            'assigned_to': bug['assigned_to'],
        })
    if filter:
        bugs = [b for b in bugs if filter(b)]
    for key, reverse in reversed(sort_by):
        bugs = sorted(bugs, key=lambda b: b[key], reverse=reverse)
    return bugs


class TableRenderer(object):
    def __init__(self, cols, sep='  '):
        self.cols = cols
        self.data = []
        self.sep = sep

    def add_row(self, *data):
        self.data.append(data)

    def render(self, stream=sys.stdout):
        # calculate column sizes
        col_data = [[c] for c in self.cols]
        for row in self.data:
            for i, d in enumerate(row):
                col_data[i].append(d)
        col_sizes = []
        for d in col_data:
            col_sizes.append(max([len(d1) for d1 in d]))

        fmt = self.sep.join(["%%-%ds"] * len(col_sizes))
        fmt = fmt % tuple(col_sizes)
        # print header
        stream.write(fmt % tuple(self.cols))
        stream.write('\n\n')
        for row in self.data:
            stream.write(fmt % tuple(row))
            stream.write('\n')
