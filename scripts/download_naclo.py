#!/usr/bin/env python3
"""
Download all PDFs linked from https://naclo.org/past_competitions.php

Output layout (default under data/):
  OUTDIR/
    2016/
      naclo-2016-round1-problems.pdf
      naclo-2016-round1-solutions.pdf
      ...
    unknown_year/
      some-file.pdf

Also writes:
  OUTDIR/manifest.jsonl   (one JSON object per line)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urljoin, urldefrag, urlparse, unquote
from urllib.request import Request, urlopen

try:
    import certifi
except Exception:  # pragma: no cover - optional dependency
    certifi = None


DEFAULT_INDEX_URL = "https://naclo.org/past_competitions.php"
DEFAULT_UA = "naclo-pdf-downloader/1.0 (+https://naclo.org/; respectful research use)"


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        for k, v in attrs:
            if k.lower() == "href" and v:
                self.hrefs.append(v)


@dataclass(frozen=True)
class PdfItem:
    url: str
    year: Optional[int]
    kind: str       # problems | solutions | other
    lang: Optional[str]
    filename: str


def fetch_bytes(
    url: str,
    timeout: float,
    retries: int,
    backoff: float,
    user_agent: str,
    context: ssl.SSLContext,
) -> bytes:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": user_agent})
            with urlopen(req, timeout=timeout, context=context) as resp:
                return resp.read()
        except Exception as e:
            last_err = e
            if attempt == retries - 1:
                break
            time.sleep(backoff ** attempt)
    raise RuntimeError(f"Failed to fetch {url}: {last_err}") from last_err


def iter_pdf_urls(index_html: bytes, base_url: str) -> Iterable[str]:
    parser = LinkExtractor()
    parser.feed(index_html.decode("utf-8", errors="replace"))
    seen = set()
    for href in parser.hrefs:
        full = urljoin(base_url, href)
        full = urldefrag(full)[0]  # drop #fragments
        if full.lower().endswith(".pdf") and full not in seen:
            seen.add(full)
            yield full


def iter_page_links(index_html: bytes, base_url: str) -> Iterable[str]:
    parser = LinkExtractor()
    parser.feed(index_html.decode("utf-8", errors="replace"))
    seen = set()
    for href in parser.hrefs:
        full = urljoin(base_url, href)
        full = urldefrag(full)[0]
        if not full:
            continue
        parsed = urlparse(full)
        if parsed.scheme not in ("http", "https"):
            continue
        if full in seen:
            continue
        seen.add(full)
        yield full


def parse_year(url: str) -> Optional[int]:
    m = re.search(r"(19|20)\d{2}", url)
    if m:
        return int(m.group(0))
    return None


def parse_lang(url: str) -> Optional[str]:
    m = re.search(r"\.([A-Za-z0-9-]+)\.pdf$", url)
    return m.group(1).lower() if m else None


def parse_kind(url: str) -> str:
    u = url.lower()
    if "solution" in u or "answer" in u:
        return "solutions"
    if "problem" in u or "question" in u:
        return "problems"
    return "other"


def build_item(url: str) -> PdfItem:
    path = urlparse(url).path
    filename = unquote(Path(path).name)
    return PdfItem(
        url=url,
        year=parse_year(url),
        kind=parse_kind(url),
        lang=parse_lang(url),
        filename=filename,
    )


def parse_years_arg(s: str) -> Optional[set[int]]:
    s = s.strip().lower()
    if s in ("all", ""):
        return None
    years: set[int] = set()
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            a_i, b_i = int(a), int(b)
            lo, hi = (a_i, b_i) if a_i <= b_i else (b_i, a_i)
            years.update(range(lo, hi + 1))
        else:
            years.add(int(part))
    return years


def parse_langs_arg(s: str) -> Optional[set[str]]:
    s = s.strip().lower()
    if s in ("all", ""):
        return None
    return {x.strip().lower() for x in s.split(",") if x.strip()}


def parse_kinds_arg(s: str) -> Optional[set[str]]:
    s = s.strip().lower()
    if s in ("all", ""):
        return None
    return {x.strip().lower() for x in s.split(",") if x.strip()}


def should_keep(item: PdfItem, years: Optional[set[int]], langs: Optional[set[str]], kinds: Optional[set[str]]) -> bool:
    if years is not None:
        if item.year is None or item.year not in years:
            return False
    if langs is not None:
        if item.lang is None or item.lang not in langs:
            return False
    if kinds is not None:
        if item.kind not in kinds:
            return False
    return True


def download_stream(
    url: str,
    dest: Path,
    timeout: float,
    retries: int,
    backoff: float,
    user_agent: str,
    context: ssl.SSLContext,
) -> str:
    tmp = dest.with_suffix(dest.suffix + ".part")
    last_err: Exception | None = None

    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": user_agent})
            with urlopen(req, timeout=timeout, context=context) as resp, open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
            os.replace(tmp, dest)
            return "ok"
        except Exception as e:
            last_err = e
            try:
                if tmp.exists():
                    tmp.unlink()
            except Exception:
                pass
            if attempt == retries - 1:
                break
            time.sleep(backoff ** attempt)

    return f"fail: {last_err}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index-url", default=DEFAULT_INDEX_URL, help="Index page to scrape for PDFs")
    ap.add_argument("--out", default="data/naclo_pdfs", help="Output directory")
    ap.add_argument("--years", default="all", help="e.g. all | 2007-2024 | 2012,2019")
    ap.add_argument("--langs", default="all", help="e.g. all | en,fr | ...")
    ap.add_argument("--kinds", default="all", help="all | problems,solutions,other")
    ap.add_argument("--crawl-depth", type=int, default=1, help="Depth to crawl from the index page for PDFs")
    ap.add_argument("--max-pages", type=int, default=200, help="Maximum number of HTML pages to fetch")
    ap.add_argument("--workers", type=int, default=4, help="Parallel downloads")
    ap.add_argument("--sleep", type=float, default=0.2, help="Sleep (seconds) before each download task")
    ap.add_argument("--timeout", type=float, default=45.0, help="HTTP timeout per request (seconds)")
    ap.add_argument("--retries", type=int, default=4, help="Retries per request")
    ap.add_argument("--backoff", type=float, default=1.6, help="Backoff base for retries")
    ap.add_argument("--ssl-ca-file", default="", help="Path to CA bundle (PEM). Overrides system trust store.")
    ap.add_argument("--insecure", action="store_true", help="Disable TLS certificate verification (NOT recommended)")
    ap.add_argument("--overwrite", action="store_true", help="Re-download even if file exists")
    ap.add_argument("--dry-run", action="store_true", help="Print what would be downloaded, don’t download")
    ap.add_argument("--user-agent", default=DEFAULT_UA, help="Custom User-Agent header")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    years = parse_years_arg(args.years)
    langs = parse_langs_arg(args.langs)
    kinds = parse_kinds_arg(args.kinds)

    if args.insecure:
        context = ssl._create_unverified_context()
    elif args.ssl_ca_file:
        context = ssl.create_default_context(cafile=args.ssl_ca_file)
    elif certifi is not None:
        context = ssl.create_default_context(cafile=certifi.where())
    else:
        context = ssl.create_default_context()

    base_parsed = urlparse(args.index_url)
    pdf_urls: set[str] = set()
    to_crawl = [args.index_url]
    seen_pages: set[str] = set()

    for depth in range(max(0, args.crawl_depth) + 1):
        if not to_crawl or len(seen_pages) >= args.max_pages:
            break
        next_pages: list[str] = []
        for page_url in to_crawl:
            if page_url in seen_pages or len(seen_pages) >= args.max_pages:
                continue
            seen_pages.add(page_url)
            html = fetch_bytes(
                page_url,
                timeout=args.timeout,
                retries=args.retries,
                backoff=args.backoff,
                user_agent=args.user_agent,
                context=context,
            )
            pdf_urls.update(iter_pdf_urls(html, page_url))
            if depth < args.crawl_depth:
                for link in iter_page_links(html, page_url):
                    if link in seen_pages:
                        continue
                    parsed = urlparse(link)
                    if parsed.netloc != base_parsed.netloc:
                        continue
                    if not parsed.path.startswith("/"):
                        continue
                    if link.lower().endswith(".pdf"):
                        continue
                    next_pages.append(link)
        to_crawl = next_pages

    pdf_urls = list(pdf_urls)
    items = [build_item(u) for u in pdf_urls]
    items = [it for it in items if should_keep(it, years, langs, kinds)]
    items.sort(key=lambda x: (x.year or 0, x.kind, x.lang or "", x.filename))

    manifest_path = out_dir / "manifest.jsonl"
    with open(manifest_path, "w", encoding="utf-8") as mf:
        for it in items:
            mf.write(json.dumps(it.__dict__, ensure_ascii=False) + "\n")

    print(f"Found {len(items)} PDFs to download. Manifest: {manifest_path}")

    if args.dry_run:
        for it in items[:200]:
            print(it.url)
        if len(items) > 200:
            print(f"... (showing first 200 of {len(items)})")
        return 0

    def task(it: PdfItem):
        time.sleep(args.sleep)
        year_dir = out_dir / (str(it.year) if it.year else "unknown_year")
        year_dir.mkdir(parents=True, exist_ok=True)
        dest = year_dir / it.filename

        if dest.exists() and not args.overwrite:
            return it, dest, "skip"

        status = download_stream(
            it.url,
            dest,
            timeout=args.timeout,
            retries=args.retries,
            backoff=args.backoff,
            user_agent=args.user_agent,
            context=context,
        )
        return it, dest, status

    ok = skip = fail = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futures = [ex.submit(task, it) for it in items]
        for i, fut in enumerate(as_completed(futures), 1):
            it, dest, status = fut.result()
            if status == "ok":
                ok += 1
            elif status == "skip":
                skip += 1
            else:
                fail += 1
            print(f"[{i}/{len(items)}] {status:10s} -> {dest}")

    print(f"Done. ok={ok}, skip={skip}, fail={fail}. Manifest: {manifest_path}")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
