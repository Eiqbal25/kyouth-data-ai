SELECT source_id, job_title, LENGTH(description) AS len
FROM jobs
ORDER BY len DESC
LIMIT 1;