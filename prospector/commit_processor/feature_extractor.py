from typing import Tuple
from urllib.parse import urlparse

import requests_cache

from datamodel.advisory import AdvisoryRecord
from datamodel.commit import Commit
from datamodel.commit_features import CommitWithFeatures
from git.git import Git

from .requests_filter import ALLOWED_SITES

DAYS_BEFORE = 180
DAYS_AFTER = 365
DAY_IN_SECONDS = 86400


def extract_features(
    commit: Commit, advisory_record: AdvisoryRecord
) -> CommitWithFeatures:
    references_vuln_id = extract_references_vuln_id(commit, advisory_record)
    time_between_commit_and_advisory_record = (
        extract_time_between_commit_and_advisory_record(commit, advisory_record)
    )
    commit_reachable_from_given_tag = False
    repo = Git(advisory_record.repository_url)
    repo.clone()

    for version in advisory_record.versions:
        version_tag = repo.get_tag_for_version(version)
        if is_commit_reachable_from_given_tag(commit, advisory_record, version_tag[0]):
            commit_reachable_from_given_tag = True
            break

    changes_relevant_path = extract_changes_relevant_path(commit, advisory_record)
    other_CVE_in_message = extract_other_CVE_in_message(commit, advisory_record)
    referred_to_by_pages_linked_from_advisories = (
        extract_referred_to_by_pages_linked_from_advisories(commit, advisory_record)
    )
    referred_to_by_nvd = extract_referred_to_by_nvd(commit, advisory_record)
    commit_feature = CommitWithFeatures(
        commit=commit,
        references_vuln_id=references_vuln_id,
        time_between_commit_and_advisory_record=time_between_commit_and_advisory_record,
        changes_relevant_path=changes_relevant_path,
        other_CVE_in_message=other_CVE_in_message,
        referred_to_by_pages_linked_from_advisories=referred_to_by_pages_linked_from_advisories,
        referred_to_by_nvd=referred_to_by_nvd,
        commit_reachable_from_given_tag=commit_reachable_from_given_tag,
    )
    return commit_feature


def extract_references_vuln_id(commit: Commit, advisory_record: AdvisoryRecord) -> bool:
    return advisory_record.vulnerability_id in commit.cve_refs


def extract_time_between_commit_and_advisory_record(
    commit: Commit, advisory_record: AdvisoryRecord
) -> int:
    return commit.timestamp - advisory_record.published_timestamp


def extract_changes_relevant_path(
    commit: Commit, advisory_record: AdvisoryRecord
) -> Tuple[str]:
    """
    Decides whether any of the changed paths (by a commit) are in the list
    of relevant paths (mentioned in the advisory record)
    """
    return tuple(set(advisory_record.paths) & set(commit.changed_files))


def extract_other_CVE_in_message(
    commit: Commit, advisory_record: AdvisoryRecord
) -> Tuple[str]:
    return tuple(set(commit.cve_refs) - {advisory_record.vulnerability_id})


def is_commit_in_given_interval(
    version_timestamp: int, commit_timestamp: int, day_interval: int
) -> bool:
    """
    Return True if the commit is in the given interval before or after the timestamp
    """

    if day_interval == 0:
        return version_timestamp == commit_timestamp
    elif day_interval > 0:
        return (
            version_timestamp + day_interval * DAY_IN_SECONDS >= commit_timestamp
            and version_timestamp <= commit_timestamp
        )
    else:
        return (
            version_timestamp + day_interval * DAY_IN_SECONDS <= commit_timestamp
            and version_timestamp >= commit_timestamp
        )


def extract_referred_to_by_nvd(
    commit: Commit, advisory_record: AdvisoryRecord
) -> Tuple[str]:
    return tuple(
        filter(
            lambda reference: commit.commit_id in reference, advisory_record.references
        )
    )


def is_commit_reachable_from_given_tag(
    commit: Commit, advisory_record: AdvisoryRecord, version_tag: str
) -> bool:
    """
    Return True if the commit is reachable from the given tag
    """
    repo = Git(advisory_record.repository_url)
    repo.clone()

    commit_id = commit.commit_id
    tag_id = repo.get_commit_id_for_tag(version_tag)

    if not repo.get_commits_between_two_commit(
        commit_id, tag_id
    ) and not repo.get_commits_between_two_commit(tag_id, commit_id):
        return False

    return True


def extract_referred_to_by_pages_linked_from_advisories(
    commit: Commit, advisory_record: AdvisoryRecord
) -> Tuple[str]:
    allowed_references = filter(
        lambda reference: urlparse(reference).hostname in ALLOWED_SITES,
        advisory_record.references,
    )
    session = requests_cache.CachedSession("requests-cache")
    return tuple(
        filter(
            lambda reference: commit.commit_id[:8] in session.get(reference).text,
            allowed_references,
        )
    )
