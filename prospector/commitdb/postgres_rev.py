"""
This module implements an abstraction layer on top of
the underlying database where pre-processed commits are stored
"""
from cgitb import lookup
import re
import traceback
import psycopg2
import psycopg2.sql
from psycopg2.extensions import parse_dsn
from psycopg2.extras import DictCursor
from git.git import Git

import log
from datamodel.commit import Commit, make_from_raw_commit

from commitdb import CommitDB

_logger = log.util.init_local_logger()


class PostgresCommitDB(CommitDB):
    """
    This class implements the database abstraction layer
    for PostgreSQL
    """

    def __init__(self):
        self.connect_string = ""
        self.connection_data = dict()
        self.connection = None

    def connect(self, connect_string=None):
        parse_connect_string(connect_string)
        self.connection = psycopg2.connect(connect_string)

    def lookup(self, repository: str, commit_id: str = None):
        # Returns the results of the query as list of Commit objects
        if not self.connection:
            raise Exception("Invalid connection")

        data = []
        try:
            cur = self.connection.cursor(cursor_factory=DictCursor)
            if commit_id:
                for cid in commit_id.split(","):
                    cur.execute(
                        "SELECT * FROM commits WHERE repository = %s AND commit_id =%s",
                        (
                            repository,
                            cid,
                        ),
                    )

                    result = cur.fetchall()

                    if len(result):
                        # Workaround for unmarshaling hunks, dict type refs
                        # lis = []
                        # for r in result[0]["hunks"]:
                        #    a, b = r.strip("()").split(",")
                        #    lis.append((int(a), int(b)))
                        result[0]["hunks"] = [
                            int(x)
                            for x in re.findall("[0-9]+", "".join(res[0]["hunks"]))
                        ]
                        result[0]["jira_refs"] = dict(
                            zip(
                                result[0]["jira_refs_id"],
                                result[0]["jira_refs_content"],
                            )
                        )
                        result[0]["ghissue_refs"] = dict(
                            zip(
                                result[0]["ghissue_refs_id"],
                                result[0]["ghissue_refs_content"],
                            )
                        )
                        # Already a list
                        # result[0]["cve_refs"] = result[0]["cve_refs"]
                        parsed_commit = Commit.parse_obj(result[0])
                        data.append(parsed_commit)
                    # else:
                    # data.append(None)
            else:
                # This never happens, but must be fixed a bit
                cur.execute(
                    "SELECT * FROM commits WHERE repository = %s",
                    (repository,),
                )
                result = cur.fetchall()
                if len(result):
                    for res in result:
                        # Workaround for unmarshaling hunks, dict type refs
                        lis = []
                        for r in res[3]:
                            a, b = r.strip("()").split(",")
                            lis.append((int(a), int(b)))
                        res[3] = lis
                        res[9] = dict.fromkeys(res[8], "")
                        res[10] = dict.fromkeys(res[9], "")
                        res[11] = dict.fromkeys(res[10], "")
                        parsed_commit = Commit.parse_obj(res)
                        data.append(parsed_commit)
            cur.close()
        except Exception:
            _logger.error("Could not lookup commit vector in database", exc_info=True)
            raise Exception("Could not lookup commit vector in database")

        return data

    def save(self, commit_obj: Commit):
        if not self.connection:
            raise Exception("Invalid connection")

        try:
            cur = self.connection.cursor()
            cur.execute(
                """INSERT INTO commits(
                    commit_id,
                    repository,
                    timestamp,
                    hunks,
                    hunk_count,
                    message,
                    diff,
                    changed_files,
                    message_reference_content,
                    jira_refs_id,
                    jira_refs_content,
                    ghissue_refs_id,
                    ghissue_refs_content,
                    cve_refs,
                    tags)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    commit_obj.commit_id,
                    commit_obj.repository,
                    commit_obj.timestamp,
                    commit_obj.hunks,
                    commit_obj.hunk_count,
                    commit_obj.message,
                    commit_obj.diff,
                    commit_obj.changed_files,
                    commit_obj.message_reference_content,
                    list(commit_obj.jira_refs.keys()),
                    list(commit_obj.jira_refs.values()),
                    list(commit_obj.ghissue_refs.keys()),
                    list(commit_obj.ghissue_refs.values()),
                    commit_obj.cve_refs,
                    commit_obj.tags,
                ),
            )

            self.connection.commit()
        except Exception:
            _logger.error("Could not save commit vector to database", exc_info=True)
            raise Exception("Could not save commit vector to database")

    def reset(self):
        """
        Resets the database by dropping its tables and recreating them afresh.
        If the database does not exist, or any tables are missing, they
        are created.
        """

        if not self.connection:
            raise Exception("Invalid connection")

        self._run_sql_script("ddl/commit.sql")
        self._run_sql_script("ddl/users.sql")

    def _run_sql_script(self, script_file):
        if not self.connection:
            raise Exception("Invalid connection")

        with open(script_file, "r") as file:
            ddl = file.read()

        cursor = self.connection.cursor()
        cursor.execute(ddl)
        self.connection.commit()

        cursor.close()


def parse_connect_string(connect_string):
    # According to:
    # https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING

    try:
        parsed_string = parse_dsn(connect_string)
    except Exception:
        raise Exception("Invalid connect string: " + connect_string)

    return parsed_string
