"""Client HTTP poli : débit limité, cache disque avec ETag/Last-Modified,
respect du robots.txt, reprise sur erreurs réseau."""
from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.error
import urllib.request
import urllib.robotparser
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

log = logging.getLogger(__name__)
USER_AGENT = "GTA6CompanionPersonal/0.1 (usage personnel, non diffusé)"


@dataclass
class Response:
    url: str
    status: int
    text: str
    from_cache: bool
    changed: bool


class PoliteClient:
    def __init__(self, cache_dir: str | Path, min_interval: float = 3.0, retries: int = 3):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.min_interval = min_interval
        self.retries = retries
        self._last: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}

    def _paths(self, url: str) -> tuple[Path, Path]:
        h = hashlib.sha256(url.encode()).hexdigest()[:32]
        return self.cache_dir / f"{h}.body", self.cache_dir / f"{h}.meta.json"

    def allowed(self, url: str) -> bool:
        host = urlsplit(url).netloc
        rp = self._robots.get(host)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            try:
                rp.parse(self._raw_get(f"https://{host}/robots.txt").splitlines())
            except Exception:  # robots illisible : on reste prudent
                log.warning("robots.txt illisible pour %s, accès refusé", host)
                rp.parse(["User-agent: *", "Disallow: /"])
            self._robots[host] = rp
        return rp.can_fetch(USER_AGENT, url)

    def _throttle(self, host: str) -> None:
        wait = self._last.get(host, 0) + self.min_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last[host] = time.monotonic()

    def _raw_get(self, url: str, headers: dict | None = None) -> str:
        self._throttle(urlsplit(url).netloc)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace")

    def get(self, url: str, *, max_age: float = 0) -> Response:
        """max_age (s) : réutilise le cache sans requête s'il est assez récent."""
        if not self.allowed(url):
            raise PermissionError(f"Interdit par robots.txt : {url}")
        body_p, meta_p = self._paths(url)
        meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
        if meta and max_age and time.time() - meta.get("fetched", 0) < max_age:
            return Response(url, 200, body_p.read_text(encoding="utf-8"), True, False)

        headers = {}
        if meta.get("etag"):
            headers["If-None-Match"] = meta["etag"]
        if meta.get("last_modified"):
            headers["If-Modified-Since"] = meta["last_modified"]

        last_err: Exception | None = None
        for attempt in range(self.retries):
            self._throttle(urlsplit(url).netloc)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **headers})
                with urllib.request.urlopen(req, timeout=30) as r:
                    text = r.read().decode("utf-8", "replace")
                    old_hash = meta.get("sha256")
                    new_hash = hashlib.sha256(text.encode()).hexdigest()
                    body_p.write_text(text, encoding="utf-8")
                    meta_p.write_text(json.dumps({
                        "url": url, "fetched": time.time(), "sha256": new_hash,
                        "etag": r.headers.get("ETag"), "last_modified": r.headers.get("Last-Modified")}))
                    return Response(url, r.status, text, False, new_hash != old_hash)
            except urllib.error.HTTPError as e:
                if e.code == 304 and body_p.exists():
                    meta["fetched"] = time.time()
                    meta_p.write_text(json.dumps(meta))
                    return Response(url, 304, body_p.read_text(encoding="utf-8"), True, False)
                if e.code in (429, 500, 502, 503, 504):
                    last_err = e
                    time.sleep(self.min_interval * (2 ** attempt) * 5)
                    continue
                raise
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last_err = e
                time.sleep(self.min_interval * (2 ** attempt))
        raise ConnectionError(f"Échec après {self.retries} tentatives : {url}") from last_err
