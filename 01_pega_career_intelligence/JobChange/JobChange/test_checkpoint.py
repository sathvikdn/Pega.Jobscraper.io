"""Offline regressions for durable Windows discovery checkpoints."""
import copy
import errno
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import campaign

TARGET = {"target_id": "gcc-citi", "name": "Citi", "category": "gcc", "keywords": ["citi"], "location": "India"}


def snapshot(marker):
    return {"status": "running", "marker": marker, "targets": [{**TARGET, "status": "results", "jobs": [{"id": marker, "url": "https://example.com/jobs/" + marker}]}]}


class CheckpointTests(unittest.TestCase):
    def test_transient_access_denial_retries_and_preserves_primary_until_success(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "preloaded_search.json"
            campaign.save_campaign(snapshot("previous"), path)
            previous = path.read_bytes()
            original_replace = Path.replace
            attempts = []

            def busy_then_replace(staged, destination):
                attempts.append(staged)
                self.assertEqual(staged.parent, path.parent)
                self.assertEqual(json.loads(staged.read_text(encoding="utf-8"))["marker"], "latest")
                self.assertEqual(path.read_bytes(), previous)
                if len(attempts) < 3:
                    raise PermissionError(errno.EACCES, "Temporary reader lock")
                return original_replace(staged, destination)

            with patch.object(campaign, "SAVE_RETRY_DELAYS", (0, 0)), patch.object(Path, "replace", new=busy_then_replace):
                campaign.save_campaign(snapshot("latest"), path)
            self.assertEqual(len(attempts), 3)
            self.assertEqual(campaign.load_campaign(path)["marker"], "latest")
            self.assertFalse(attempts[-1].exists())

    def test_persistent_access_denial_preserves_primary_and_complete_recovery_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "preloaded_search.json"
            campaign.save_campaign(snapshot("previous"), path)
            previous = path.read_bytes()
            denied = PermissionError(errno.EACCES, "Persistent reader lock")
            with patch.object(campaign, "SAVE_RETRY_DELAYS", (0, 0)), patch.object(Path, "replace", side_effect=denied) as replace:
                with self.assertRaises(campaign.CheckpointSaveError) as raised:
                    campaign.save_campaign(snapshot("latest"), path)
            self.assertEqual(replace.call_count, 3)
            self.assertIs(raised.exception.__cause__, denied)
            self.assertEqual(path.read_bytes(), previous)
            recovery = Path(raised.exception.recovery_path)
            self.assertEqual(recovery.parent, path.parent)
            self.assertNotEqual(recovery, path.with_name(path.name + ".tmp"))
            saved = json.loads(recovery.read_text(encoding="utf-8"))
            self.assertEqual(saved["marker"], "latest")
            self.assertEqual(saved["coverage"]["jobs"], 1)
            self.assertEqual(saved["targets"][0]["jobs"][0]["id"], "latest")

    def test_each_failed_save_keeps_a_distinct_recovery_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "preloaded_search.json"
            campaign.save_campaign(snapshot("previous"), path)
            recoveries = []
            with patch.object(campaign, "SAVE_RETRY_DELAYS", ()), patch.object(Path, "replace", side_effect=PermissionError("Busy")):
                for marker in ("first", "second"):
                    with self.assertRaises(campaign.CheckpointSaveError) as raised:
                        campaign.save_campaign(snapshot(marker), path)
                    recoveries.append(Path(raised.exception.recovery_path))
            self.assertNotEqual(recoveries[0], recoveries[1])
            self.assertEqual([json.loads(p.read_text(encoding="utf-8"))["marker"] for p in recoveries], ["first", "second"])
            self.assertEqual(campaign.load_campaign(path)["marker"], "previous")

    def test_nonsharing_filesystem_error_is_not_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "preloaded_search.json"
            campaign.save_campaign(snapshot("previous"), path)
            previous = path.read_bytes()
            failure = OSError(errno.ENOSPC, "No space left on device")
            with patch.object(campaign, "SAVE_RETRY_DELAYS", (0, 0)), patch.object(Path, "replace", side_effect=failure) as replace, patch.object(campaign.time, "sleep") as sleep:
                with self.assertRaises((campaign.CheckpointSaveError, OSError)) as raised:
                    campaign.save_campaign(snapshot("latest"), path)
            self.assertEqual(replace.call_count, 1)
            sleep.assert_not_called()
            self.assertIs(raised.exception.__cause__ or raised.exception, failure)
            self.assertEqual(path.read_bytes(), previous)

    def test_windows_sharing_violation_codes_are_retried(self):
        for code in (5, 32, 33):
            with self.subTest(winerror=code), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "preloaded_search.json"
                campaign.save_campaign(snapshot("previous"), path)
                original_replace = Path.replace
                attempts = []
                error = OSError("Windows file sharing conflict")
                error.winerror = code

                def retry(staged, destination):
                    attempts.append(staged)
                    if len(attempts) == 1:
                        raise error
                    return original_replace(staged, destination)

                with patch.object(campaign, "SAVE_RETRY_DELAYS", (0,)), patch.object(Path, "replace", new=retry):
                    campaign.save_campaign(snapshot("latest"), path)
                self.assertEqual(len(attempts), 2)
                self.assertEqual(campaign.load_campaign(path)["marker"], "latest")

    @unittest.skipUnless(os.name == "nt", "Windows denies replacement while a normal reader holds the destination")
    def test_actual_windows_reader_releases_and_checkpoint_finishes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "preloaded_search.json"
            campaign.save_campaign(snapshot("previous"), path)
            held_reader = path.open("rb")
            failures = []
            original_replace = Path.replace

            def observe_replace(staged, destination):
                try:
                    return original_replace(staged, destination)
                except OSError as error:
                    failures.append(error)
                    raise

            release = threading.Timer(0.1, held_reader.close)
            release.start()
            try:
                with patch.object(Path, "replace", new=observe_replace):
                    campaign.save_campaign(snapshot("latest"), path)
            finally:
                release.join(timeout=2)
                held_reader.close()
            self.assertTrue(failures, "The regression must exercise a real blocked Windows replacement")
            self.assertTrue(any(isinstance(error, PermissionError) or getattr(error, "winerror", None) in (5, 32, 33) for error in failures))
            self.assertEqual(campaign.load_campaign(path)["marker"], "latest")

    def test_discovery_save_failure_stops_workers_before_teardown_and_releases_lock(self):
        targets = [TARGET, {**TARGET, "target_id": "gcc-other", "name": "Other", "keywords": ["other"]}]
        stop = threading.Event()
        second_started = threading.Event()
        stopped_before_teardown = []

        def checked(target, client):
            if target["target_id"] == TARGET["target_id"]:
                self.assertTrue(second_started.wait(2))
                return {**target, "status": "no_matches", "checked_at": "2026-09-08", "diagnostics": [], "jobs": []}
            second_started.set()
            stopped_before_teardown.append(stop.wait(2))
            raise campaign.Cancelled()

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "preloaded_search.json"
            real_save = campaign.save_campaign
            calls = []
            failure = OSError(errno.EACCES, "Checkpoint replacement failed")

            def fail_second_save(document, destination):
                calls.append(copy.deepcopy(document))
                if len(calls) == 2:
                    raise failure
                return real_save(document, destination)

            with patch.object(campaign, "save_campaign", side_effect=fail_second_save), patch.object(campaign, "check_target", side_effect=checked), patch.object(campaign.PublicClient, "get", side_effect=AssertionError("Network is forbidden in checkpoint tests")):
                with self.assertRaises(OSError) as raised:
                    campaign.run_campaign(data=targets, output_path=path, stop_event=stop, workers=2)
            self.assertIs(raised.exception, failure)
            self.assertTrue(stop.is_set())
            self.assertEqual(stopped_before_teardown, [True])
            self.assertEqual(len(calls), 2, "Failure must not trigger a final save over the last valid checkpoint")
            self.assertEqual(campaign.load_campaign(path)["coverage"]["checked"], 0)
            self.assertFalse(campaign.campaign_is_locked(path))

    def test_enrichment_save_failure_stops_workers_before_teardown_and_releases_lock(self):
        stop = threading.Event()
        second_started = threading.Event()
        stopped_before_teardown = []
        jobs = [campaign.make_job("Pega Developer", "Citi", "India", "https://example.com/jobs/" + str(number), "Employer", "2026-09-08") for number in (1, 2)]

        def enrich(job, client):
            if job["url"].endswith("/1"):
                self.assertTrue(second_started.wait(2))
                return {**job, "job_detail_status": "read"}
            second_started.set()
            stopped_before_teardown.append(stop.wait(2))
            raise campaign.Cancelled()

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "preloaded_search.json"
            campaign.save_campaign({"status": "complete", "targets": [{**TARGET, "status": "results", "jobs": jobs}]}, path)
            real_save = campaign.save_campaign
            calls = []
            failure = OSError(errno.EACCES, "Checkpoint replacement failed")

            def fail_second_save(document, destination):
                calls.append(copy.deepcopy(document))
                if len(calls) == 2:
                    raise failure
                return real_save(document, destination)

            with patch.object(campaign, "save_campaign", side_effect=fail_second_save), patch.object(campaign, "enrich_job", side_effect=enrich), patch.object(campaign.PublicClient, "get", side_effect=AssertionError("Network is forbidden in checkpoint tests")):
                with self.assertRaises(OSError) as raised:
                    campaign.enrich_campaign(output_path=path, stop_event=stop, workers=2)
            self.assertIs(raised.exception, failure)
            self.assertTrue(stop.is_set())
            self.assertEqual(stopped_before_teardown, [True])
            self.assertEqual(len(calls), 2, "Failure must not trigger a final save over the last valid checkpoint")
            saved = campaign.load_campaign(path)
            self.assertEqual(saved["detail_enrichment"]["checked"], 0)
            self.assertEqual(len(saved["targets"][0]["jobs"]), 2)
            self.assertFalse(campaign.campaign_is_locked(path))


if __name__ == "__main__":
    unittest.main()

