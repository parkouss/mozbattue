# mainly stolen from mozci trigger.py file

import urllib
from mozci.mozci import query_builders, query_repo_url_from_buildername, \
    query_repo_name_from_buildername, trigger_job
from mozci.sources.pushlog import query_revision_info, query_pushid_range
from mozbattue.utils import LOG


def sanitize_buildername(buildername):
    buildername = buildername.strip()
    builders = query_builders()
    for builder in builders:
        if buildername.lower() == builder.lower():
            buildername = builder

    return buildername


def trigger_jobs(buildername, revision, back_revisions=30, times=30,
                 dry_run=False):
    buildername = sanitize_buildername(buildername)
    repo_url = query_repo_url_from_buildername(buildername)
    repo_name = query_repo_name_from_buildername(buildername)

    if back_revisions >= 0:
        # find the revision *back_revisions* before the one we got
        push_info = query_revision_info(repo_url, revision)
        end_id = int(push_info["pushid"])  # newest revision
        start_id = end_id - back_revisions
        revlist = query_pushid_range(repo_url=repo_url,
                                     start_id=start_id,
                                     end_id=end_id)
        revision = revlist[-1]

    requests = \
        trigger_job(revision, buildername, times=times, dry_run=dry_run)
    if any(req.status_code != 202 for req in requests):
        LOG.warn('WARNING: not all requests succeded')

    return ('https://treeherder.mozilla.org/#/jobs?%s' % urllib.urlencode({
        'repo': repo_name,
        'revision': revision,
        'filter-searchStr': buildername
    }))
