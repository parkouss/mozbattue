import unittest
from StringIO import StringIO

from mozbattue import bugs_info


class MyTable(bugs_info.Table):
    columns = {
        'one': bugs_info.Column(str),
        'two': bugs_info.Column(str),
        'three': bugs_info.Column(repr),
    }
    visible_columns = ('one', 'two')


class TestTable(unittest.TestCase):
    def setUp(self):
        self.table = MyTable()

    def assert_table_output(self, expected):
        io = StringIO()
        self.table.render(stream=io)
        # trim right spaces
        result = '\n'.join([l.rstrip() for l in io.getvalue().splitlines()])
        self.assertEquals(result + '\n', expected)

    def test_basic(self):
        self.table.add_row({'one': 1, 'two': '2'})
        self.table.add_row({'one': 11, 'two': '22'})

        self.assert_table_output("""\
one  two

1    2
11   22
""")

    def test_sort(self):
        self.table.add_row({'one': 11, 'two': 22})
        self.table.add_row({'one': 1, 'two': 2})
        self.table.add_row({'one': 11, 'two': 55})

        self.table.string_sort("one, >two")

        self.assert_table_output("""\
one  two

1    2
11   55
11   22
""")
