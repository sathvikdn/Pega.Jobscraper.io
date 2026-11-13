"""Offline concurrency, cache identity and source circuit regression tests."""
import io
import sys
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / ".deps"))
sys.path.insert(0, str(HERE))
import campaign


class Response:
    def __init__(self, url, body=b"Pega developer", status=200):
        self.url, self.body, self.status = url, body, status
        self.read_limits = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def read(self, size):
        self.read_limits.append(size)
        return self.body[:size]


def until(predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        threading.Event().wait(0.005)
    raise AssertionError("Concurrent operation did not reach the expected state")


class ParallelClientTests(unittest.TestCase):
    def test_duplicate_parallel_requests_are_single_flight(self):
        client = campaign.PublicClient(spacing=0)
        barrier, entered, release = threading.Barrier(7), threading.Event(), threading.Event()
        url = "https://jobs.example/search?keywords=Pega&start=0"
        def open_request(request, **kwargs):
            entered.set()
            self.assertTrue(release.wait(3))
            return Response(request.full_url)
        def get():
            barrier.wait(3)
            return client.get(url)
        with patch.object(campaign.urllib.request, "urlopen", side_effect=open_request) as request:
            with ThreadPoolExecutor(max_workers=6) as pool:
                results = [pool.submit(get) for _ in range(6)]
                try:
                    barrier.wait(3)
                    self.assertTrue(entered.wait(2))
                    until(lambda: client.snapshot_stats()["shared_waits"] == 5)
                finally:
                    release.set()
                output = [future.result(timeout=3) for future in results]
            self.assertEqual(request.call_count, 1)
        self.assertEqual([item[0] for item in output], ["Pega developer"] * 6)
        self.assertEqual(sum(item[1].get("cache_mode") == "inflight" for item in output), 5)
        stats = client.snapshot_stats()
        self.assertEqual((stats["requests"], stats["active_requests"], stats["inflight_urls"]), (1, 0, 0))

    def test_cached_diagnostics_are_independent_and_query_is_preserved(self):
        client = campaign.PublicClient(spacing=0)
        def open_request(request, **kwargs):
            return Response(request.full_url, request.full_url.encode())
        with patch.object(campaign.urllib.request, "urlopen", side_effect=open_request) as request:
            first = client.get("https://jobs.example/search?keywords=Pega&start=0")
            first[1]["http_status"] = 999
            second = client.get("https://JOBS.example/search?keywords=Pega&start=0#results")
            third = client.get("https://jobs.example/search?keywords=Pega&start=10")
            fourth = client.get("https://jobs.example/search?keywords=Java&start=0")
        self.assertEqual(request.call_count, 3)
        self.assertEqual(second[1]["http_status"], 200)
        self.assertEqual(second[1]["cache_mode"], "run_cache")
        self.assertNotEqual(first[0], third[0])
        self.assertNotEqual(first[0], fourth[0])

    def test_independent_hosts_overlap_without_holding_the_pacing_lock(self):
        client = campaign.PublicClient()
        network_barrier = threading.Barrier(2)
        def open_request(request, **kwargs):
            network_barrier.wait(2)
            return Response(request.full_url)
        with patch.object(campaign.urllib.request, "urlopen", side_effect=open_request):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(client.get, "https://" + host + "/job") for host in ("first.example", "second.example")]
                self.assertEqual([f.result(timeout=3)[0] for f in futures], ["Pega developer"] * 2)
        self.assertEqual(client.snapshot_stats()["peak_active_requests"], 2)
        self.assertEqual(client.limiter.spacing, 2.0)

    def test_same_host_requests_keep_the_configured_spacing(self):
        client = campaign.PublicClient(spacing=0.07)
        starts = []
        def open_request(request, **kwargs):
            starts.append(time.monotonic())
            return Response(request.full_url)
        with patch.object(campaign.urllib.request, "urlopen", side_effect=open_request):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(client.get, "https://jobs.example/" + str(i)) for i in range(2)]
                [future.result(timeout=2) for future in futures]
        self.assertGreaterEqual(max(starts) - min(starts), 0.055)

    def test_joined_request_observes_cancellation_without_waiting_for_owner(self):
        stop, entered, release = threading.Event(), threading.Event(), threading.Event()
        client = campaign.PublicClient(stop, spacing=0)
        url = "https://jobs.example/123"
        def open_request(request, **kwargs):
            entered.set()
            self.assertTrue(release.wait(3))
            return Response(request.full_url)
        with patch.object(campaign.urllib.request, "urlopen", side_effect=open_request) as request:
            with ThreadPoolExecutor(max_workers=2) as pool:
                owner = pool.submit(client.get, url)
                self.assertTrue(entered.wait(2))
                joined = pool.submit(client.get, url)
                try:
                    until(lambda: client.snapshot_stats()["shared_waits"] == 1)
                    stop.set()
                    with self.assertRaises(campaign.Cancelled):
                        joined.result(timeout=1)
                finally:
                    release.set()
                owner.result(timeout=2)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(client.snapshot_stats()["inflight_urls"], 0)

    def test_cancellation_during_host_queue_does_not_open_another_connection(self):
        stop = threading.Event()
        client = campaign.PublicClient(stop, spacing=20)
        with patch.object(campaign.urllib.request, "urlopen", side_effect=lambda req, **kw: Response(req.full_url)) as request:
            client.get("https://jobs.example/first")
            with ThreadPoolExecutor(max_workers=1) as pool:
                queued = pool.submit(client.get, "https://jobs.example/second")
                until(lambda: client.snapshot_stats()["queued_requests"] == 1)
                stop.set()
                with self.assertRaises(campaign.Cancelled):
                    queued.result(timeout=1)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(client.snapshot_stats()["queued_requests"], 0)

    def test_access_denial_skips_the_host_but_not_other_sources(self):
        client = campaign.PublicClient(spacing=0)
        error = HTTPError("https://blocked.example/first", 403, "denied", {}, io.BytesIO())
        def open_request(request, **kwargs):
            if "blocked.example" in request.full_url:
                raise error
            return Response(request.full_url)
        with patch.object(campaign.urllib.request, "urlopen", side_effect=open_request) as request:
            self.assertEqual(client.get(error.url)[1]["http_status"], 403)
            denied = client.get("https://blocked.example/second")
            self.assertEqual(client.get("https://employer.example/job")[0], "Pega developer")
        self.assertEqual(request.call_count, 2)
        self.assertIsNone(denied[0])
        self.assertEqual(denied[1]["http_status"], 403)
        self.assertTrue(denied[1]["request_skipped"])
        # Access denials stop this host for the current run.
        # Other hosts remain available without changing client identities.
        self.assertTrue(denied[1]['blocked_for_run'])
        self.assertEqual(client.snapshot_stats()['platforms']['Employer']['pages'],2)
        self.assertEqual(client.snapshot_stats()['platforms']['Employer']['skipped'],1)
        self.assertEqual(denied[1]["blocked_source_url"], error.url)
        self.assertTrue(error.closed)

    def test_rate_limit_honors_retry_after_before_allowing_next_attempt(self):
        client = campaign.PublicClient(spacing=0)
        tick = [100.0]
        error = HTTPError("https://jobs.example/first", 429, "limited", {"Retry-After": "120"}, io.BytesIO())
        with patch.object(campaign.time, "monotonic", side_effect=lambda: tick[0]):
            with patch.object(campaign.urllib.request, "urlopen", side_effect=[error, Response("https://jobs.example/third")]) as request:
                client.get(error.url)
                skipped = client.get("https://jobs.example/second")
                self.assertEqual(skipped[1]["http_status"], 429)
                self.assertEqual(skipped[1]["retry_after_seconds"], 120)
                self.assertEqual(request.call_count, 1)
                tick[0] = 221.0
                self.assertEqual(client.get("https://jobs.example/third")[0], "Pega developer")
                self.assertEqual(request.call_count, 2)

    def test_long_retry_after_does_not_get_shortened_to_backoff_cap(self):
        client = campaign.PublicClient(spacing=0)
        error = HTTPError("https://jobs.example/first", 429, "limited", {"Retry-After": "3600"}, io.BytesIO())
        with patch.object(campaign.urllib.request, "urlopen", side_effect=error) as request:
            client.get(error.url)
            skipped = client.get("https://jobs.example/second")
        self.assertEqual(request.call_count, 1)
        self.assertTrue(skipped[1]["blocked_for_run"])

    def test_http_date_retry_after_is_honored(self):
        client = campaign.PublicClient(spacing=0)
        future = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=180), usegmt=True)
        error = HTTPError("https://jobs.example/first", 429, "limited", {"Retry-After": future}, io.BytesIO())
        with patch.object(campaign.urllib.request, "urlopen", side_effect=error) as request:
            client.get(error.url)
            skipped = client.get("https://jobs.example/second")
        self.assertEqual(request.call_count, 1)
        self.assertGreaterEqual(skipped[1]["retry_after_seconds"], 178)

    def test_server_errors_and_temporary_network_errors_are_not_cached(self):
        for error in (HTTPError("https://jobs.example/one", 503, "busy", {}, io.BytesIO()), URLError("timeout")):
            client = campaign.PublicClient(spacing=0)
            with patch.object(campaign.urllib.request, "urlopen", side_effect=[error, Response("https://jobs.example/one")]) as request:
                self.assertIsNone(client.get("https://jobs.example/one")[0])
                self.assertEqual(client.get("https://jobs.example/one")[0], "Pega developer")
            self.assertEqual(request.call_count, 2)

    def test_response_limit_and_truncation_flag_survive_cache(self):
        client = campaign.PublicClient(spacing=0)
        response = Response("https://jobs.example/one", b"x" * 3_000_100)
        with patch.object(campaign.urllib.request, "urlopen", return_value=response) as request:
            first = client.get(response.url)
            second = client.get(response.url)
        self.assertEqual(len(first[0]), 3_000_000)
        self.assertTrue(first[1]["content_truncated"])
        self.assertTrue(second[1]["content_truncated"])
        self.assertEqual(response.read_limits, [3_000_001])
        self.assertTrue(response.closed)
        self.assertEqual(request.call_count, 1)

    def test_response_cache_has_both_count_and_memory_bounds(self):
        client = campaign.PublicClient(spacing=0)
        client.CACHE_ENTRIES = 2
        with patch.object(campaign.urllib.request, "urlopen", side_effect=lambda req, **kw: Response(req.full_url)) as request:
            for name in ("one", "two", "one", "three", "two"):
                client.get("https://jobs.example/" + name)
            self.assertEqual(request.call_count, 4)
        self.assertEqual(client.snapshot_stats()["cached_responses"], 2)
        bounded = campaign.PublicClient(spacing=0)
        bounded.CACHE_BYTES = 1100
        with patch.object(campaign.urllib.request, "urlopen", side_effect=lambda req, **kw: Response(req.full_url)):
            for index in range(10):
                bounded.get("https://jobs.example/" + str(index))
        self.assertLessEqual(bounded.snapshot_stats()["cache_bytes"], 1100)
        self.assertEqual(bounded.snapshot_stats()["cached_responses"], 1)

    def test_unexpected_error_wakes_duplicate_waiters_and_releases_slots(self):
        client = campaign.PublicClient(spacing=0)
        entered, release = threading.Event(), threading.Event()
        def open_request(request, **kwargs):
            entered.set()
            self.assertTrue(release.wait(3))
            raise ValueError("fixture unexpected error")
        with patch.object(campaign.urllib.request, "urlopen", side_effect=open_request):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(client.get, "https://jobs.example/one")
                self.assertTrue(entered.wait(2))
                second = pool.submit(client.get, "https://jobs.example/one")
                try:
                    until(lambda: client.snapshot_stats()["shared_waits"] == 1)
                finally:
                    release.set()
                for future in (first, second):
                    with self.assertRaisesRegex(ValueError, "fixture unexpected error"):
                        future.result(timeout=2)
        self.assertEqual(client.snapshot_stats()["active_requests"], 0)
        self.assertEqual(client.snapshot_stats()["inflight_urls"], 0)


if __name__ == "__main__":
    unittest.main()
