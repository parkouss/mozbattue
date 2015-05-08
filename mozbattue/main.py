import argparse
import sys
import logging

from mozbattue.utils import MozBattueError, load_bugs_from_file, dump_bugs, \
    intermittents_by_time
from mozbattue.bugs_info import bug_list, TableRenderer
from mozbattue.find_bugs import BugsyFinder, BugsyPrintReporter
from mozbattue.trigger import trigger_jobs

def do_update(opts):
    finder = BugsyFinder(reporter=BugsyPrintReporter())
    bugs = finder.find(days_ago=opts.days_ago)
    with open(opts.output, 'w') as f:
        dump_bugs(bugs, f)


def do_list(opts):
    raw_bugs = load_bugs_from_file(opts.input)

    sort_by = []
    for k in opts.sort_by.split(','):
        k = k.strip()
        reverse = False
        if k.startswith('-'):
            k = k[1:]
            reverse = True
        elif k.startswith('+'):
            k = k[1:]
        sort_by.append((k, reverse))

    def filter(bug):
        return bug['nb'] >= opts.min_intermittents

    bugs = bug_list(raw_bugs, sort_by=sort_by, filter=filter)
    if opts.limit > 0:
        bugs = bugs[:opts.limit]

    renderer = TableRenderer(('id', 'nb', 'date'))

    for b in bugs:
        renderer.add_row(str(b['id']), str(b['nb']), str(b['date']))

    renderer.render()

    print
    print ("Listing %d/%d intermittent bugs."
           % (len(bugs), len(raw_bugs)))


def do_show(opts):
    raw_bugs = load_bugs_from_file(opts.input)
    if opts.bugid not in raw_bugs:
        sys.exit("Unable to find bug %s." % opts.bugid)
    intermittents = intermittents_by_time(raw_bugs[opts.bugid])
    oldest = intermittents[0]

    print "Oldest intermittent on %s (%s)" % (oldest['timestamp'],
                                              oldest['revision'])
    print

    if opts.full:
        print "List of intermittents:"

        renderer = TableRenderer(('date', 'revision', 'buildname'))
        for i in intermittents:
            renderer.add_row(str(i['timestamp']), str(i['revision']),
                             repr(str(i['buildname'])))
        renderer.render()
    else:
        i_for_revision = [i for i in intermittents
                          if i['revision'] == oldest['revision']]
        print "Was triggered by:"
        renderer = TableRenderer(('date', 'buildname'))
        for i in i_for_revision:
            renderer.add_row(str(i['timestamp']), repr(str(i['buildname'])))
        renderer.render()


def do_trigger(opts):
    raw_bugs = load_bugs_from_file(opts.input)
    if opts.bugid not in raw_bugs:
        sys.exit("Unable to find bug %s." % opts.bugid)
    intermittents = intermittents_by_time(raw_bugs[opts.bugid])
    oldest = intermittents[0]

    url = trigger_jobs(oldest['buildname'], oldest['revision'],
                       back_revisions=abs(opts.back_revisions),
                       times=opts.times, dry_run=opts.dry_run)

    print "Use the following treeherder url to keep track of the builds:"
    print
    print url
    print
    print 'Note that the builds on treeherder will appear in a few minutes.'


def parse_args(argv=None):
    intermittent_file = 'intermittents.json'
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers()

    update = subparsers.add_parser(
        'update',
        help="Find intermittent bugs from bugzilla and store them locally",
        description="This query bugzilla to find intermittent bugs, and "
                    "store the results in a local file (%r) so the data "
                    "can be reused by other commands." % intermittent_file
    )
    update.add_argument('-o', '--output',
                        default=intermittent_file,
                        help="file to store the intermittent bugs data "
                               "(default: %(default)r)")
    update.add_argument('-d', '--days-ago',
                        default=27,
                        type=int,
                        help="Number of days from now to search bugs for "
                             "(default: %(default)r)")
    update.set_defaults(func=do_update)

    def add_input_opt(p):
        p.add_argument('-i', '--input',
                       default=intermittent_file,
                       help="file path where bugs data is stored "
                            "(default: %(default)r)")

    list = subparsers.add_parser(
        'list',
        help="list stored bugs",
        description="List the stored intermittent bugs, ordering and "
                    "filtering them to find the most important ones easily."
    )
    add_input_opt(list)
    list.add_argument('-s', '--sort-by',
                      default='-nb,id',
                      help="sorts the list. Possible criteria are id, nb "
                           "or date which are respectively the bug id, the "
                           "number of intermittents and the date of the "
                           "first intermittent occurence. By default the "
                           "sort is ascending, this can be inversed by "
                           "adding '-' before the criteria name. "
                           "(default: %(default)r)")
    list.add_argument('-m', '--min-intermittents',
                      default=10,
                      type=int,
                      help="Minimum number of intermittent instances "
                           "required to list a bug (default: %(default)r)")
    list.add_argument('-l', '--limit',
                      default=0,
                      type=int,
                      help="Limit the number of bugs shown "
                           "(default: %(default)r - no limit)")
    list.set_defaults(func=do_list)

    show = subparsers.add_parser(
        'show',
        help="show details of one stored bug",
        description="Print detailed information about one bug, such as the "
                    "revision, date and buildname of the oldest intermittent."
    )
    add_input_opt(show)
    show.add_argument("-f", '--full', action='store_true',
                      help="Show all details")
    show.add_argument("bugid")
    show.set_defaults(func=do_show)

    trigger = subparsers.add_parser(
        'trigger',
        help="trigger builds",
        description="Trigger a build from the oldest revision found in the "
                    "intermittent bug. For example, "
                    "'%(prog)s --times 20 12345 -15' would trigger a build "
                    "for the 15th revision before the oldest one in bug "
                    "12345 20 times."
    )
    add_input_opt(trigger)
    trigger.add_argument("bugid")
    trigger.add_argument("back_revisions", type=int,
                         help="Number of revisions to go back")
    trigger.add_argument("-t", "--times", type=int,
                         default=30,
                         help="Number of build for the revision "
                              " (default: %(default)r")
    trigger.add_argument("--dry-run", action="store_true",
                         help="flag to test without actual push")
    trigger.set_defaults(func=do_trigger)

    return parser.parse_args(argv)


def main(argv=None):
    opts = parse_args()
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('requests').setLevel(logging.WARNING)
    try:
        opts.func(opts)
    except KeyboardInterrupt:
        sys.exit('Interrupted\n')
    except MozBattueError as exc:
        sys.exit(str(exc))
