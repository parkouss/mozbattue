import sys
from mozbattue.utils import intermittents_by_time, MozBattueError


class Column(object):
    def __init__(self, renderer=str, desc=''):
        self.renderer = renderer
        self.desc = desc

    def render_value(self, value):
        return self.renderer(value)


class Table(object):
    columns = {}

    def __init__(self, visible_columns=()):
        self.data = []
        self.visible_columns = visible_columns or self.columns.keys()

    def add_row(self, row):
        self.data.append(row)

    def sort(self, sort_by=()):
        for key, reverse in reversed(sort_by):
            self.data = sorted(self.data, key=lambda b: b[key],
                               reverse=reverse)

    def string_sort(self, string_sort):
        sort_by = []
        for k in string_sort.split(','):
            k = k.strip()
            reverse = False
            if k.startswith('>'):
                k = k[1:]
                reverse = True
            elif k.startswith('<'):
                k = k[1:]
            if k not in self.columns:
                raise MozBattueError("Unable to sort by unknown column %r" % k)
            sort_by.append((k, reverse))
        self.sort(sort_by)

    def raw_filter(self, filter):
        self.data = [d for d in self.data if filter(d)]

    def render(self, stream=sys.stdout, sep='  '):
        renderer = TableRenderer(self.visible_columns, sep=sep)
        for row in self.data:
            data_row = []
            for column_name in self.visible_columns:
                col = self.columns[column_name]
                data_row.append(col.render_value(row[column_name]))
            renderer.add_row(*data_row)
        renderer.render(stream=stream)


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


class BugTable(Table):
    columns = {
        'id': Column(str, desc='Id of the bug'),
        'nb': Column(str, desc='Number of intermittent occurences found'),
        'date': Column(str, desc='Date of the first intermittent occurence'),
        'rev': Column(str,
                      desc='Revision of the first intermittent occurence'),
        'status': Column(str, desc='Status of the bug'),
        'assigned_to': Column(str, desc='Assignment of the bug'),
        'product': Column(str, desc='Product of the bug'),
        'average_day': Column(lambda v: '%.2f' % v,
                              desc="Average number of intermittents occurences"
                                   " in one day"),
    }

    def __init__(self, raw_bugs, visible_columns=()):
        Table.__init__(self, visible_columns=visible_columns)
        for bugid, bug in raw_bugs.iteritems():
            intermittents = intermittents_by_time(bug['intermittents'])
            oldest, newest = intermittents[0], intermittents[-1]
            daterange = newest['timestamp'] - oldest['timestamp']
            self.add_row({
                'id': bugid,
                'nb': len(intermittents),
                'date': oldest['timestamp'],
                'rev': oldest['revision'],
                'status': bug['status'],
                'assigned_to': bug['assigned_to'],
                'product': bug['product'],
                'average_day': len(intermittents) / float(daterange.days or 1),
            })


class BugTableComment(Table):
    columns = {
        'column name': Column(str),
        'description': Column(str),
    }

    def __init__(self):
        Table.__init__(self, visible_columns=('column name', 'description'))
        for name in sorted(BugTable.columns):
            self.add_row({
                'column name': name,
                'description': BugTable.columns[name].desc
            })


class IntermittentTable(Table):
    columns = {
        'date': Column(str),
        'revision': Column(str),
        'buildname': Column(lambda v: repr(str(v))),
    }

    def __init__(self, intermittents, visible_columns=()):
        Table.__init__(self, visible_columns=visible_columns)
        for i in intermittents:
            self.add_row({
                'date': i['timestamp'],
                'revision': i['revision'],
                'buildname': i['buildname'],
            })


class IntermittentsGroupedByNameTable(Table):
    columns = {
        'buildname': Column(lambda v: repr(str(v))),
        'occurences': Column(str),
    }

    def __init__(self):
        Table.__init__(self, visible_columns=('occurences', 'buildname'))
