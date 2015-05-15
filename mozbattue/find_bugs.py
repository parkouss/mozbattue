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

    def bug_already_up2date(self, bug):
        pass

    def finished(self, result):
        pass


class BugsyFinder(object):
    RE_EXTRACT_BUG_INFO = \
        re.compile("^(buildname|revision|start_time|submit_timestamp): (.+)")

    def __init__(self, reporter=None, previous_bugs=None):
        self.bugzilla = bugsy.Bugsy()
        self.reporter = reporter or BugsyReporter()
        self.previous_bugs = previous_bugs

    def _get_intermittents(self, bug):
        intermittents = []
        for comment in bug.get_comments():
            intermittent = {}
            for line in comment.text.splitlines():
                res = self.RE_EXTRACT_BUG_INFO.match(line)
                if not res:
                    continue
                key, value = res.groups()
                intermittent[key] = value
            if 'start_time' in intermittent:
                intermittent['timestamp'] = intermittent.pop('start_time')
            if 'submit_timestamp' in intermittent:
                intermittent['timestamp'] = \
                    intermittent.pop('submit_timestamp')
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
            .include_fields('assigned_to', 'last_change_time') \
            .search()

        self.reporter.got_bugs(bugs)
        result = {}
        for bug in bugs:
            bug_dict = bug.to_dict()
            self.reporter.bug_analysis_started(bug)

            if self.previous_bugs:
                prev_bug = self.previous_bugs.get(str(bug.id))
                if prev_bug and (bug_dict['last_change_time'] ==
                                 prev_bug['last_change_time']):
                    self.reporter.bug_already_up2date(bug)
                    result[bug.id] = prev_bug
                    continue
            intermittents = self._get_intermittents(bug)

            result[bug.id] = {
                'intermittents': intermittents,
                'status': bug.status,
                'product': bug.product,
                'assigned_to': bug_dict['assigned_to'],
                'last_change_time': bug_dict['last_change_time'],
            }
            self.reporter.bug_analyzed(bug, intermittents)
        self.reporter.finished(result)
        return result


class BugsyPrintReporter(BugsyReporter):
    def __init__(self, stream=sys.stdout):
        self.stream = stream
        self.nb_bugs = 0
        self.current_bug = 0
        self.upd2date = set()

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

    def bug_already_up2date(self, bug):
        self.upd2date.add(bug.id)

    def finished(self, result):
        # keep only bugs that have intermittents
        res = [k for k, v in result.iteritems() if v['intermittents']]
        # remove the bugs without intermittents from the up2date list
        upd2date = self.upd2date - set([k for k, v in result.iteritems()
                                        if not v['intermittents']])
        if self.nb_bugs != len(res):
            self.output("Found %d bugs without intermittents data - "
                        "we won't use them\n", self.nb_bugs - len(res))
        up2date_str = ''
        if upd2date:
            up2date_str = ' (%d already up to date)' % len(upd2date)
        self.output("Finished analysis - kept %d new intermittents%s\n",
                    len([bid for bid in res if bid not in upd2date]),
                    up2date_str)
