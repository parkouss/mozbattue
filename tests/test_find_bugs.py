import datetime
import unittest
from mock import patch, Mock
from bugsy.bug import Bug

from mozbattue import find_bugs


def create_time_frame(now=None, days_ago=7):
    date_limit = now or datetime.date.today()
    start_date = date_limit - datetime.timedelta(days=days_ago)
    return str(start_date), str(date_limit)


class FakeComment(object):
    def __init__(self, text):
        self.text = text


class FakeBug(Bug):
    def __init__(self, comments=(), **kwargs):
        kwargs.setdefault('assigned_to', 'nobody')
        kwargs.setdefault('last_change_time', 'any')
        kwargs.setdefault('product', 'core')
        kwargs.setdefault('status', 'NEW')
        Bug.__init__(self, None, **kwargs)
        self._comments = comments

    def get_comments(self):
        return [FakeComment(t) for t in self._comments]


def expected_bug_result(bugs):
    result = {}
    for bug in bugs:
        result[bug.id] = {
            'assigned_to': 'nobody',
            'intermittents': [],
            'last_change_time': 'any',
            'product': 'core',
            'status': 'NEW'
        }
    return result


class TestBugsyFinder(unittest.TestCase):
    @patch('bugsy.Bugsy')
    def setUp(self, Bugsy):
        bugsy = Mock()
        Bugsy.return_value = bugsy

        bugsy.search_for = search = Mock()
        bugsy.search_for.keywords.return_value = search
        bugsy.search_for.change_history_fields.return_value = search
        bugsy.search_for.timeframe.return_value = search
        bugsy.search_for.include_fields.return_value = search

        self.reporter = Mock()

        self.finder = find_bugs.BugsyFinder(reporter=self.reporter)
        self.bugsy = bugsy

    def test_find_query(self):
        self.bugsy.search_for.search.return_value = []

        result = self.finder.find(days_ago=7)

        self.assertEquals(result, {})
        search = self.bugsy.search_for
        search.keywords.assert_called_with('intermittent-failure')
        search.change_history_fields.assert_called_with(['[Bug creation]'])
        search.timeframe.assert_called_with(*create_time_frame(days_ago=7))
        search.include_fields.assert_called_with('assigned_to',
                                                 'last_change_time')

        search.search.assert_called_with()

    def test_find_query_custom_date(self):
        self.bugsy.search_for.search.return_value = []

        self.finder.find(days_ago=2, date_limit=datetime.date(2015, 5, 12))

        search = self.bugsy.search_for
        search.timeframe.assert_called_with('2015-05-10', '2015-05-12')
        search.search.assert_called_with()

    def test_find_with_no_comment(self):
        bugs = [FakeBug(id=1)]
        self.bugsy.search_for.search.return_value = bugs

        result = self.finder.find()

        self.assertEquals(result, expected_bug_result(bugs))

    def test_find_with_useless_comment(self):
        bugs = [FakeBug(id=1, comments=['hello', 'world'])]
        self.bugsy.search_for.search.return_value = bugs

        result = self.finder.find()

        expected = expected_bug_result(bugs)
        self.assertEquals(result, expected)
        # check the reporter calls
        self.reporter.got_bugs.assert_called_with(bugs)
        self.reporter.bug_analysis_started.assert_called_with(bugs[0])
        self.reporter.bug_analyzed.assert_called_with(bugs[0], [])
        self.reporter.finished.assert_called_with(expected)

    def test_find_with_comment(self):
        bugs = [FakeBug(id=1, comments=["""
buildname: mybuildname
revision: myrevision
useless: justtobesure
start_time: 2015-04-15T03:16:25
"""])]
        self.bugsy.search_for.search.return_value = bugs

        result = self.finder.find()

        expected = expected_bug_result(bugs)
        expected[1]['intermittents'].append({
            'buildname': 'mybuildname',
            'revision': 'myrevision',
            'timestamp': datetime.datetime(2015, 4, 15, 3, 16, 25)
        })

        self.assertEquals(result, expected)
        # check the reporter calls
        self.reporter.got_bugs.assert_called_with(bugs)
        self.reporter.bug_analysis_started.assert_called_with(bugs[0])
        self.reporter.bug_analyzed.assert_called_with(
            bugs[0],
            expected[1]['intermittents']
        )
        self.reporter.finished.assert_called_with(expected)
