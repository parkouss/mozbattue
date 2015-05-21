import argparse
import os
import sys
import logging

from mozbattue.utils import MozBattueError, load_bugs_from_file, dump_bugs, \
    intermittents_by_time, Config, LOG, get_default_conf_path, \
    create_filter_intermittents, intermittents_groupedby_bname, \
    split_build_name
from mozbattue.bugs_info import BugTable, IntermittentTable, BugTableComment, \
    IntermittentsGroupedByNameTable
from mozbattue.find_bugs import BugsyFinder, BugsyPrintReporter
from mozbattue.trigger import trigger_jobs


def do_update(opts):
    # load previous bugs if any
    previous_bugs = None
    try:
        previous_bugs = load_bugs_from_file(opts.intermittents_json_file,
                                            kept_no_intermittents=True)
    except:
        pass

    finder = BugsyFinder(reporter=BugsyPrintReporter(),
                         previous_bugs=previous_bugs)
    bugs = finder.find(days_ago=opts.days_ago)

    json_dir = os.path.dirname(opts.intermittents_json_file)
    if not os.path.isdir(json_dir):
        os.makedirs(json_dir)

    with open(opts.intermittents_json_file, 'w') as f:
        dump_bugs(bugs, f)


def read_bugs(opts):
    return load_bugs_from_file(
        opts.intermittents_json_file,
        filter_intermittents=create_filter_intermittents(
            opts.intermittents_filter_buildname
        )
    )


def do_list(opts):
    raw_bugs = read_bugs(opts)

    def filter(bug):
        if bug['product'] in opts.filter_products:
            return False
        if not opts.show_assigned_to:
            if bug['assigned_to'] != 'nobody@mozilla.org':
                return False
        if not opts.show_resolved:
            if bug['status'] == 'RESOLVED':
                return False
        return bug['nb'] >= opts.min_intermittents

    table = BugTable(raw_bugs, opts.visible_columns)
    table.raw_filter(filter)
    table.string_sort(opts.sort_by)
    if opts.limit > 0:
        table.data = table.data[:opts.limit]

    table.render()

    print
    print ("Listing %d/%d intermittent bugs."
           % (len(table.data), len(raw_bugs)))


def do_list_colums(opts):
    table = BugTableComment()
    table.render()
    print


def do_show(opts):
    raw_bugs = read_bugs(opts)
    if opts.bugid not in raw_bugs:
        sys.exit("Unable to find bug %s." % opts.bugid)
    intermittents = \
        intermittents_by_time(raw_bugs[opts.bugid]['intermittents'])
    oldest = intermittents[0]

    print "Oldest intermittent on %r: %s (%s)" % (oldest['buildname'],
                                                  oldest['timestamp'],
                                                  oldest['revision'])
    print

    print "buildnames by number of occurrences:"
    table = IntermittentsGroupedByNameTable()
    for data in intermittents_groupedby_bname(intermittents):
        table.add_row(data)
    table.render()

    print

    if opts.full:
        print "List of intermittents:"
        IntermittentTable(intermittents).render()


def do_trigger(opts):
    raw_bugs = read_bugs(opts)
    if opts.bugid not in raw_bugs:
        sys.exit("Unable to find bug %s." % opts.bugid)
    intermittents = \
        intermittents_by_time(raw_bugs[opts.bugid]['intermittents'])
    oldest = intermittents[0]

    if opts.buildname:
        # let's find the oldest intermittent for this buildname
        for intermittent in intermittents:
            if opts.buildname == intermittent['buildname']:
                oldest = intermittent
                break
    else:
        # we can use the mostly triggered testname as good default
        most_triggered_bname = \
            intermittents_groupedby_bname(intermittents)[0]['buildname']
        test_name = split_build_name(most_triggered_bname)['testname']
        for i in intermittents:
            if split_build_name(i['buildname'])['testname'] == test_name:
                oldest = i
                break

    url = trigger_jobs(oldest['buildname'],
                       oldest['revision'],
                       back_revisions=abs(opts.back_revisions),
                       times=opts.times, dry_run=opts.dry_run)

    print "Use the following treeherder url to keep track of the builds:"
    print
    print url
    print
    print 'Note that the builds on treeherder will appear in a few minutes.'


def do_generate_conf(opts):
    with open(opts.conf_file, 'w') as fw:
        with open(get_default_conf_path()) as fr:
            fw.write(fr.read())
    print '%r wrote.' % opts.conf_file


def parse_args(argv=None):
    intermittent_file = 'intermittents.json'
    parser = argparse.ArgumentParser()

    parser.add_argument('--conf-file', default="mozbattue.ini",
                        help="path of the configuration file. (default: "
                             "%(default)r)")

    subparsers = parser.add_subparsers()

    update = subparsers.add_parser(
        'update',
        help="Find intermittent bugs from bugzilla and store them locally",
        description="This query bugzilla to find intermittent bugs, and "
                    "store the results in a local file (%r) so the data "
                    "can be reused by other commands." % intermittent_file
    )
    update.add_argument('-d', '--days-ago',
                        default=27,
                        type=int,
                        help="Number of days from now to search bugs for "
                             "(default: %(default)r)")
    update.set_defaults(func=do_update)

    list = subparsers.add_parser(
        'list',
        help="list stored bugs",
        description="List the stored intermittent bugs, ordering and "
                    "filtering them to find the most important ones easily."
    )

    list.add_argument('-l', '--limit',
                      default=0,
                      type=int,
                      help="Limit the number of bugs shown "
                           "(default: %(default)r - no limit)")
    list.set_defaults(func=do_list)

    list_columns = subparsers.add_parser(
        'list-columns',
        help="list the columns available for the list command")
    list_columns.set_defaults(func=do_list_colums)

    show = subparsers.add_parser(
        'show',
        help="show details of one stored bug",
        description="Print detailed information about one bug, such as the "
                    "revision, date and buildname of the oldest intermittent."
    )
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
    trigger.add_argument("bugid")
    trigger.add_argument("back_revisions", type=int,
                         help="Number of revisions to go back")
    trigger.add_argument("-t", "--times", type=int,
                         default=30,
                         help="Number of build for the revision "
                              " (default: %(default)r")
    trigger.add_argument("-b", "--buildname",
                         help="Specify a buildname to trigger")
    trigger.add_argument("--dry-run", action="store_true",
                         help="flag to test without actual push")
    trigger.set_defaults(func=do_trigger)

    generate_conf = subparsers.add_parser(
        'generate-conf',
        help="generate the default configuration file so you can customize it",
    )
    generate_conf.add_argument('--conf-file', default='mozbattue.ini',
                               help="output file path to write the conf.")
    generate_conf.set_defaults(func=do_generate_conf)

    return parser.parse_args(argv)


def main(argv=None):
    opts = parse_args()

    logging.basicConfig(level=logging.INFO)
    logging.getLogger('requests').setLevel(logging.WARNING)

    conf = Config()
    # always load the default configuration file
    conf.read(get_default_conf_path())
    if os.path.isfile(opts.conf_file):
        LOG.info("Reading conf file %r", opts.conf_file)
        conf.read(opts.conf_file)
    opts.__dict__.update(conf.as_dict())
    opts.intermittents_json_file = \
        os.path.realpath(os.path.expanduser(opts.intermittents_json_file))
    try:
        opts.func(opts)
    except KeyboardInterrupt:
        sys.exit('Interrupted\n')
    except MozBattueError as exc:
        sys.exit(str(exc))

if __name__ == '__main__':
    main()
