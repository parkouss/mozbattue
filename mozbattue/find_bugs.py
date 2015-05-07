import bugsy
import datetime
import re
import sys


class BugsyReporter(object):
    def started(self):
        pass

    def got_bugs(self, bugs):
        pass

    def bug_analysis_started(self, bug):
        pass

    def bug_analyzed(self, bug, intermittents):
        pass

    def finished(self, result):
        pass


class BugsyFinder(object):
    RE_EXTRACT_BUG_INFO = \
        re.compile("^(buildname|revision|start_time|submit_timestamp): (.+)")

    def __init__(self, reporter=None):
        self.bugzilla = bugsy.Bugsy()
        self.reporter = reporter or BugsyReporter()

    def _get_intermittents(self, bug):
        intermittents = []
        for comment in bug.get_comments():
            intermittent = {}
            for line in  comment.text.splitlines():
                res = self.RE_EXTRACT_BUG_INFO.match(line)
                if not res:
                    continue
                key, value = res.groups()
                intermittent[key] = value
            if 'start_time' in intermittent:
                intermittent['timestamp'] = intermittent.pop('start_time')
            if 'submit_timestamp' in intermittent:
                intermittent['timestamp'] = intermittent.pop('submit_timestamp')
            if len(intermittent) == 3:
                # all intermittent info is here
                intermittent['timestamp'] = \
                    datetime.datetime.strptime(intermittent['timestamp'],
                                               '%Y-%m-%dT%H:%M:%S')
                intermittents.append(intermittent)
        return intermittents

    def find(self, days_ago=7, date_limit=None):
        if date_limit is None:
            date_limit = datetime.date.today()
        start_date = date_limit - datetime.timedelta(days=days_ago)
        self.reporter.started()
        bugs = self.bugzilla.search_for \
            .keywords("intermittent-failure") \
            .change_history_fields(['[Bug creation]']) \
            .timeframe(str(start_date), str(date_limit)) \
            .search()

        self.reporter.got_bugs(bugs)
        result = {}
        for bug in bugs:
            self.reporter.bug_analysis_started(bug)
            intermittents = self._get_intermittents(bug)
            if intermittents:
                result[bug.id] = intermittents
            self.reporter.bug_analyzed(bug, intermittents)
        self.reporter.finished(result)
        return result


class BugsyPrintReporter(BugsyReporter):
    def __init__(self, stream=sys.stdout):
        self.stream = stream
        self.nb_bugs = 0
        self.current_bug = 0

    def output(self, txt, *args):
        if args:
            txt = txt % args
        self.stream.write(txt)
        self.stream.flush()

    def started(self):
        self.output('Looking for bugs...\n')

    def got_bugs(self, bugs):
        self.nb_bugs = len(bugs)
        self.output("Found %d bugs\n", self.nb_bugs)

    def bug_analysis_started(self, bug):
        self.current_bug += 1
        self.output("Analyzing bug %s (%d/%d)\r", bug.id, self.current_bug,
                    self.nb_bugs)

    def finished(self, result):
        self.output("Finished analysis - kept %d intermittents\n",
                    len(result))
