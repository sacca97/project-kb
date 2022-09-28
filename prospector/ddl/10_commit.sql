-- public.commits definition

-- Drop table

DROP TABLE IF EXISTS public.commits;
CREATE TABLE public.commits (
	commit_id varchar(40) NOT NULL,
	repository varchar NOT NULL,
	timestamp int,
	-- preprocessed data
	hunks varchar[] NULL,
	hunk_count int,
	message varchar NULL,
	diff varchar[] NULL,
	changed_files varchar[] NULL,
	message_reference_content varchar[] NULL,
	jira_refs varchar[] NULL,
	ghissue_refs_id varchar[] NULL,
	ghissue_refs_content varchar[] NULL,
	cve_refs varchar[] NULL,
	tags varchar[] NULL,
	CONSTRAINT commits_pkey PRIMARY KEY (commit_id, repository)
);
CREATE INDEX IF NOT EXISTS commit_index ON public.commits USING btree (commit_id);
CREATE UNIQUE INDEX IF NOT EXISTS commit_repository_index ON public.commits USING btree (commit_id, repository);
CREATE INDEX IF NOT EXISTS repository_index ON public.commits USING btree (repository);

CREATE OR REPLACE FUNCTION public.commits_insert(
	_commit_id varchar(40),
	_repository varchar,
	_timstamp int,
	_hunks varchar[],
	_hunks_count int,
	_message varchar,
	_diff varchar[],
	_changed_files varchar[],
	_message_reference_content varchar[],
	_jira_refs varchar[],
	_ghissue_refs_id varcha[]r,
	_ghissue_refs_content varchar[],
	_cve_refs varchar[],
	_tags varchar[]
	) RETURNS void AS 
$$
	BEGIN
		INSERT INTO public.commits (commit_id, repository, timestamp, hunks, hunk_count, message, diff, changed_files, message_reference_content, jira_refs, ghissue_refs_id, ghissue_refs_content, cve_refs, tags)
		VALUES (_commit_id, _repository, _timstamp, _hunks, _hunks_count, _message, _diff, _changed_files, _message_reference_content, _jira_refs, _ghissue_refs_id, _ghissue_refs_content, _cve_refs, _tags)
		ON CONFLICT ON CONSTRAINT commits_pkey DO UPDATE SET (commit_id, repository, timestamp, hunks, hunk_count, message, diff, changed_files, message_reference_content, jira_refs, ghissue_refs_id, ghissue_refs_content, cve_refs, tags) = (EXCLUDED.commit_id, EXCLUDED.repository, EXCLUDED.timestamp, EXCLUDED.hunks, EXCLUDED.hunk_count, EXCLUDED.message, EXCLUDED.diff, EXCLUDED.changed_files, EXCLUDED.message_reference_content, EXCLUDED.jira_refs, EXCLUDED.ghissue_refs_id, EXCLUDED.ghissue_refs_content, EXCLUDED.cve_refs, EXCLUDED.tags);
	END;
$$ LANGUAGE plpgsql;

