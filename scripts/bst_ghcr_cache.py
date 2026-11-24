#!/usr/bin/env python3
"""BuildStream remote cache backed by an OCI registry (ghcr).

BuildStream talks to remote caches with the Remote Asset, CAS and ByteStream
gRPC APIs. This server speaks those APIs on localhost and stores each pushed
artifact or source as one zstd-compressed pack in an OCI repository, tagged
by the SHA-256 of its Remote Asset URI. Nothing is restored up front: a pack
is downloaded only when BuildStream asks for that artifact, and a push uploads
only the artifact just built.

Run it inside the bst2 container, which provides grpcio and BuildStream's
generated protos, with the BuildStream cache directory mounted read-only:
blobs BuildStream pushes are read straight from casd's object store, so a
push copies nothing over gRPC.

Only artifacts are accepted; source pushes are refused, because sources can
carry files staged from the checkout (including the Secure Boot private key
in signing builds). Artifacts an upstream cache (gbm.gnome.org, cache.freedesktop-sdk.io) already
serves are never uploaded, so the repository holds only what Mercury builds.

Environment:
  CACHE_REPO      registry/repository, e.g. ghcr.io/siddhj2206/mercury-bst-cache
  REGISTRY_USER   registry user (optional; anonymous pulls work for public repos)
  REGISTRY_TOKEN  registry token or password (required with CACHE_PUSH=1)
  CACHE_PUSH      1 to accept pushes; anything else serves reads only
  UPSTREAMS       comma-separated grpcs:// or https:// Remote Asset endpoints
  LOCAL_CAS       casd object root (default /bstcache/cas)
  STORE           scratch directory for downloaded packs (default /store)
  LISTEN          host:port (default 127.0.0.1:50051)
  USED_LOG        optional file that receives one tag per line for every pack
                  served or pushed, for retention
"""

from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import json
import logging
import os
import re
import signal
import sys
import tarfile
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable

import grpc
from buildstream._protos.build.bazel.remote.asset.v1 import (
    remote_asset_pb2,
    remote_asset_pb2_grpc,
)
from buildstream._protos.build.bazel.remote.execution.v2 import (
    remote_execution_pb2 as re_pb2,
)
from buildstream._protos.build.bazel.remote.execution.v2 import (
    remote_execution_pb2_grpc as re_grpc,
)
from buildstream._protos.build.bazel.semver import semver_pb2
from buildstream._protos.google.bytestream import bytestream_pb2, bytestream_pb2_grpc
from buildstream._protos.google.rpc import code_pb2, status_pb2

LOG = logging.getLogger("bst-ghcr-cache")

PACK_MEDIA_TYPE = "application/vnd.mercury.bst-pack.v1.tar+zstd"
ARTIFACT_TYPE = "application/vnd.mercury.bst-pack.v1"
EMPTY_CONFIG = b"{}"
EMPTY_CONFIG_DIGEST = "sha256:" + hashlib.sha256(EMPTY_CONFIG).hexdigest()
MANIFEST_MEDIA_TYPE = "application/vnd.oci.image.manifest.v1+json"
CHUNK = 1024 * 1024
MAX_BATCH = 4 * 1024 * 1024
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ARTIFACT_URI = re.compile(r"^urn:fdc:buildstream\.build:2020:artifact:")


def tag_for(uri: str) -> str:
    return hashlib.sha256(uri.encode()).hexdigest()


def digest_str(d: re_pb2.Digest) -> str:
    return f"{d.hash}/{d.size_bytes}"


def parse_digest(s: str) -> re_pb2.Digest:
    h, size = s.split("/")
    return re_pb2.Digest(hash=h, size_bytes=int(size))


# ── OCI registry client ─────────────────────────────────────────────────────


class Registry:
    """Minimal OCI distribution client with bearer-token auth (ghcr, registry:2)."""

    def __init__(self, repo: str, user: str | None, token: str | None, push: bool):
        host, _, name = repo.partition("/")
        self.scheme = "http" if host.startswith(("localhost", "127.0.0.1")) else "https"
        self.host = host
        self.name = name
        self.user = user
        self.secret = token
        self.scope = f"repository:{name}:pull,push" if push else f"repository:{name}:pull"
        self._bearer: str | None = None
        self._lock = threading.Lock()

    def _url(self, path: str) -> str:
        return f"{self.scheme}://{self.host}/v2/{self.name}/{path}"

    def _authenticate(self, challenge: str) -> None:
        params = dict(re.findall(r'(\w+)="([^"]*)"', challenge))
        realm = params.get("realm")
        if not realm:
            raise RuntimeError(f"unsupported auth challenge: {challenge}")
        query = {"scope": self.scope}
        if "service" in params:
            query["service"] = params["service"]
        req = urllib.request.Request(f"{realm}?{urllib.parse.urlencode(query)}")
        if self.secret:
            basic = base64.b64encode(f"{self.user or 'token'}:{self.secret}".encode()).decode()
            req.add_header("Authorization", f"Basic {basic}")
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.load(resp)
        self._bearer = body.get("token") or body.get("access_token")

    def request(self, method: str, url: str, *, data=None, headers=None, length=None, ok=(200,), stream=False):
        """Issue a request, authenticating on 401. Retries transient failures."""
        for attempt in range(5):
            if hasattr(data, "seek"):
                data.seek(0)
            req = urllib.request.Request(url, data=data, method=method)
            for k, v in (headers or {}).items():
                req.add_header(k, v)
            if length is not None:
                req.add_header("Content-Length", str(length))
            if self._bearer:
                # Never forward the token to the blob CDN a redirect points at.
                req.add_unredirected_header("Authorization", f"Bearer {self._bearer}")
            try:
                resp = urllib.request.urlopen(req, timeout=600)
            except urllib.error.HTTPError as e:
                if e.code == 401 and attempt < 2:
                    e.close()
                    with self._lock:
                        self._authenticate(e.headers.get("WWW-Authenticate", ""))
                    continue
                if e.code in ok:
                    return e
                if e.code in (429, 500, 502, 503, 504) and attempt < 4:
                    e.close()
                    time.sleep(2**attempt)
                    continue
                raise
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if attempt < 4:
                    time.sleep(2**attempt)
                    continue
                raise
            if resp.status not in ok:
                raise RuntimeError(f"{method} {url}: unexpected status {resp.status}")
            if stream:
                return resp
            with resp:
                resp.body = resp.read()
            return resp
        raise RuntimeError(f"{method} {url}: retries exhausted")

    def list_tags(self) -> set[str]:
        tags: set[str] = set()
        url = self._url("tags/list?n=10000")
        while url:
            try:
                resp = self.request("GET", url)
            except urllib.error.HTTPError as e:
                if e.code == 404:  # repository does not exist yet
                    e.close()
                    return tags
                raise
            tags.update(t for t in (json.loads(resp.body).get("tags") or []) if HEX64.match(t))
            link = resp.headers.get("Link", "")
            m = re.search(r"<([^>]+)>;\s*rel=\"next\"", link)
            url = urllib.parse.urljoin(f"{self.scheme}://{self.host}", m.group(1)) if m else None
        return tags

    def get_manifest(self, tag: str) -> dict:
        resp = self.request("GET", self._url(f"manifests/{tag}"), headers={"Accept": MANIFEST_MEDIA_TYPE})
        return json.loads(resp.body)

    def download_blob(self, digest: str, dest: str) -> None:
        resp = self.request("GET", self._url(f"blobs/{digest}"), stream=True)
        h = hashlib.sha256()
        with resp, open(dest, "wb") as f:
            while chunk := resp.read(CHUNK):
                h.update(chunk)
                f.write(chunk)
        if "sha256:" + h.hexdigest() != digest:
            raise RuntimeError(f"blob {digest} failed verification")

    def blob_exists(self, digest: str) -> bool:
        try:
            self.request("HEAD", self._url(f"blobs/{digest}"))
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                e.close()
                return False
            raise

    def upload_blob(self, digest: str, path: str | None = None, data: bytes | None = None) -> None:
        if self.blob_exists(digest):
            return
        resp = self.request("POST", self._url("blobs/uploads/"), ok=(202,), length=0, data=b"")
        location = urllib.parse.urljoin(self._url(""), resp.headers["Location"])
        sep = "&" if "?" in location else "?"
        target = f"{location}{sep}digest={urllib.parse.quote(digest)}"
        headers = {"Content-Type": "application/octet-stream"}
        if path is not None:
            with open(path, "rb") as f:
                self.request("PUT", target, data=f, headers=headers, length=os.path.getsize(path), ok=(201,))
        else:
            self.request("PUT", target, data=data, headers=headers, length=len(data), ok=(201,))

    def put_manifest(self, tag: str, manifest: bytes) -> None:
        self.request(
            "PUT",
            self._url(f"manifests/{tag}"),
            data=manifest,
            headers={"Content-Type": MANIFEST_MEDIA_TYPE},
            length=len(manifest),
            ok=(201,),
        )


# ── Blob storage: casd's object store (read-only) plus our pack store ──────


class Blobs:
    def __init__(self, local_cas: str, store: str):
        self.local = os.path.join(local_cas, "objects")
        self.store = os.path.join(store, "objects")
        self.tmp = os.path.join(store, "tmp")
        os.makedirs(self.store, exist_ok=True)
        os.makedirs(self.tmp, exist_ok=True)

    @staticmethod
    def _rel(h: str) -> str:
        return os.path.join(h[:2], h[2:])

    def path(self, h: str) -> str | None:
        for root in (self.store, self.local):
            p = os.path.join(root, self._rel(h))
            if os.path.exists(p):
                return p
        return None

    def has(self, d: re_pb2.Digest) -> bool:
        return d.size_bytes == 0 or self.path(d.hash) is not None

    def read(self, d: re_pb2.Digest) -> bytes:
        if d.size_bytes == 0:
            return b""
        p = self.path(d.hash)
        if p is None:
            raise FileNotFoundError(d.hash)
        with open(p, "rb") as f:
            return f.read()

    def write(self, h: str, data: bytes) -> None:
        if hashlib.sha256(data).hexdigest() != h:
            raise ValueError(f"digest mismatch for {h}")
        dest = os.path.join(self.store, self._rel(h))
        if os.path.exists(dest):
            return
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.tmp)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, dest)

    def adopt(self, h: str, src: str) -> None:
        dest = os.path.join(self.store, self._rel(h))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        os.replace(src, dest)

    def closure(self, roots: Iterable[re_pb2.Digest], dirs: Iterable[re_pb2.Digest]) -> dict[str, int]:
        """All blobs reachable from the given blobs and Directory roots."""
        out: dict[str, int] = {}
        for d in roots:
            if d.size_bytes:
                out[d.hash] = d.size_bytes
        stack = [d for d in dirs]
        while stack:
            d = stack.pop()
            if d.hash in out:
                continue
            out[d.hash] = d.size_bytes
            directory = re_pb2.Directory.FromString(self.read(d))
            for f in directory.files:
                if f.digest.size_bytes:
                    out[f.digest.hash] = f.digest.size_bytes
            stack.extend(sub.digest for sub in directory.directories)
        return out


# ── Pack cache: ghcr tags ↔ local blobs ─────────────────────────────────────


class PackCache:
    def __init__(self, registry: Registry, blobs: Blobs, push: bool, upstreams: list[str], used_log: str | None):
        self.registry = registry
        self.blobs = blobs
        self.push_enabled = push
        try:
            self.tags = registry.list_tags()
        except Exception:
            # Serve anyway: BuildStream falls back to the public caches and
            # builds what is missing. Pushes will report their own errors.
            LOG.exception("could not list %s/%s; starting with an empty index", registry.host, registry.name)
            self.tags = set()
        self.roots: dict[str, tuple[str, str]] = {}  # tag -> (kind, digest)
        self.locks: dict[str, threading.Lock] = {}
        self.locks_lock = threading.Lock()
        self.upstreams = [self._upstream(u) for u in upstreams]
        self.used_log = used_log
        self.used_lock = threading.Lock()
        LOG.info("index: %d packs in %s/%s", len(self.tags), registry.host, registry.name)

    @staticmethod
    def _upstream(url: str):
        parsed = urllib.parse.urlparse(url)
        target = parsed.netloc
        if parsed.scheme in ("https", "grpcs"):
            channel = grpc.secure_channel(target, grpc.ssl_channel_credentials())
        else:
            channel = grpc.insecure_channel(target)
        return url, remote_asset_pb2_grpc.FetchStub(channel)

    def _lock(self, tag: str) -> threading.Lock:
        with self.locks_lock:
            return self.locks.setdefault(tag, threading.Lock())

    def _record(self, tag: str) -> None:
        if self.used_log:
            with self.used_lock, open(self.used_log, "a") as f:
                f.write(tag + "\n")

    def upstream_has(self, uris: list[str], kind: str) -> bool:
        for url, stub in self.upstreams:
            try:
                if kind == "blob":
                    resp = stub.FetchBlob(remote_asset_pb2.FetchBlobRequest(uris=uris), timeout=60)
                else:
                    resp = stub.FetchDirectory(remote_asset_pb2.FetchDirectoryRequest(uris=uris), timeout=60)
            except grpc.RpcError as e:
                if e.code() != grpc.StatusCode.NOT_FOUND:
                    LOG.warning("upstream %s: %s", url, e.code().name)
                continue
            if resp.status.code == code_pb2.OK:
                return True
        return False

    def fetch(self, uris: list[str], kind: str) -> tuple[str, re_pb2.Digest] | None:
        for uri in uris:
            tag = tag_for(uri)
            if tag not in self.tags:
                continue
            with self._lock(tag):
                if tag not in self.roots:
                    try:
                        self.roots[tag] = self._download(tag)
                    except Exception:
                        LOG.exception("pack %s for %s unavailable", tag[:12], uri)
                        continue
            pack_kind, root = self.roots[tag]
            if pack_kind != kind:
                continue
            self._record(tag)
            return uri, parse_digest(root)
        return None

    def _download(self, tag: str) -> tuple[str, str]:
        start = time.monotonic()
        manifest = self.registry.get_manifest(tag)
        ann = manifest.get("annotations", {})
        layer = manifest["layers"][0]
        fd, pack = tempfile.mkstemp(dir=self.blobs.tmp, suffix=".tar.zst")
        os.close(fd)
        try:
            self.registry.download_blob(layer["digest"], pack)
            with tarfile.open(pack, "r:zst") as tar:
                for member in tar:
                    h = member.name
                    if not member.isfile() or not HEX64.match(h):
                        raise RuntimeError(f"unexpected pack member {member.name!r}")
                    if self.blobs.has(re_pb2.Digest(hash=h, size_bytes=member.size)):
                        continue
                    src = tar.extractfile(member)
                    fd, tmp = tempfile.mkstemp(dir=self.blobs.tmp)
                    hasher = hashlib.sha256()
                    with os.fdopen(fd, "wb") as out:
                        while chunk := src.read(CHUNK):
                            hasher.update(chunk)
                            out.write(chunk)
                    if hasher.hexdigest() != h:
                        os.unlink(tmp)
                        raise RuntimeError(f"pack blob {h} failed verification")
                    self.blobs.adopt(h, tmp)
        finally:
            os.unlink(pack)
        LOG.info(
            "pulled %s (%.1f MB) in %.1fs",
            ann.get("org.mercury.bst.uri", tag)[:120],
            layer["size"] / 1e6,
            time.monotonic() - start,
        )
        return ann["org.mercury.bst.kind"], ann["org.mercury.bst.root"]

    def push(self, uris: list[str], kind: str, root: re_pb2.Digest, blobs: list, dirs: list) -> None:
        if not self.push_enabled:
            raise PermissionError("push disabled")
        if not all(ARTIFACT_URI.match(u) for u in uris):
            # Artifacts only. Source pushes (including the combined
            # element-sources entry) carry files staged from the checkout,
            # and the signing build stages the Secure Boot private key: never
            # let sources leave the runner.
            raise PermissionError("only artifacts are cached")
        tags = [tag_for(u) for u in uris]
        if all(t in self.tags for t in tags):
            return
        if self.upstream_has(uris, kind):
            LOG.info("skip %s: upstream has it", uris[0][:120])
            return
        start = time.monotonic()
        if kind == "blob":
            members = self.blobs.closure([root, *blobs], dirs)
        else:
            members = self.blobs.closure(blobs, [root, *dirs])
        fd, pack = tempfile.mkstemp(dir=self.blobs.tmp, suffix=".tar.zst")
        os.close(fd)
        try:
            with tarfile.open(pack, "w:zst") as tar:
                for h, size in sorted(members.items()):
                    p = self.blobs.path(h)
                    if p is None:
                        raise FileNotFoundError(f"blob {h} missing from local CAS")
                    info = tarfile.TarInfo(h)
                    info.size = size
                    info.mode = 0o644
                    with open(p, "rb") as f:
                        tar.addfile(info, f)
            h = hashlib.sha256()
            with open(pack, "rb") as f:
                while chunk := f.read(CHUNK):
                    h.update(chunk)
            layer_digest = "sha256:" + h.hexdigest()
            layer_size = os.path.getsize(pack)
            self.registry.upload_blob(EMPTY_CONFIG_DIGEST, data=EMPTY_CONFIG)
            self.registry.upload_blob(layer_digest, path=pack)
        finally:
            os.unlink(pack)
        manifest = json.dumps(
            {
                "schemaVersion": 2,
                "mediaType": MANIFEST_MEDIA_TYPE,
                "artifactType": ARTIFACT_TYPE,
                "config": {
                    "mediaType": "application/vnd.oci.empty.v1+json",
                    "digest": EMPTY_CONFIG_DIGEST,
                    "size": len(EMPTY_CONFIG),
                },
                "layers": [{"mediaType": PACK_MEDIA_TYPE, "digest": layer_digest, "size": layer_size}],
                "annotations": {
                    "org.mercury.bst.kind": kind,
                    "org.mercury.bst.root": digest_str(root),
                    "org.mercury.bst.uri": uris[0],
                    "org.opencontainers.image.source": os.environ.get("CACHE_SOURCE", ""),
                },
            },
            sort_keys=True,
        ).encode()
        for tag in tags:
            self.registry.put_manifest(tag, manifest)
            self.tags.add(tag)
            self.roots[tag] = (kind, digest_str(root))
            self._record(tag)
        LOG.info(
            "pushed %s (%d blobs, %.1f MB) in %.1fs",
            uris[0][:120],
            len(members),
            layer_size / 1e6,
            time.monotonic() - start,
        )


# ── gRPC services ───────────────────────────────────────────────────────────


def _status(code: int, message: str = "") -> status_pb2.Status:
    return status_pb2.Status(code=code, message=message)


class Fetch(remote_asset_pb2_grpc.FetchServicer):
    def __init__(self, packs: PackCache):
        self.packs = packs

    def FetchBlob(self, request, context):
        if not request.uris:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "no uris")
        hit = self.packs.fetch(list(request.uris), "blob")
        if hit is None:
            return remote_asset_pb2.FetchBlobResponse(status=_status(code_pb2.NOT_FOUND))
        uri, digest = hit
        return remote_asset_pb2.FetchBlobResponse(status=_status(code_pb2.OK), uri=uri, blob_digest=digest)

    def FetchDirectory(self, request, context):
        if not request.uris:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "no uris")
        hit = self.packs.fetch(list(request.uris), "directory")
        if hit is None:
            return remote_asset_pb2.FetchDirectoryResponse(status=_status(code_pb2.NOT_FOUND))
        uri, digest = hit
        return remote_asset_pb2.FetchDirectoryResponse(
            status=_status(code_pb2.OK), uri=uri, root_directory_digest=digest
        )


class Push(remote_asset_pb2_grpc.PushServicer):
    def __init__(self, packs: PackCache):
        self.packs = packs

    def _push(self, request, context, kind, root):
        if not request.uris:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "no uris")
        if not self.packs.push_enabled:
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "this cache is read-only")
        try:
            self.packs.push(
                list(request.uris), kind, root, list(request.references_blobs), list(request.references_directories)
            )
        except PermissionError as e:
            context.abort(grpc.StatusCode.PERMISSION_DENIED, str(e))
        except FileNotFoundError as e:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
        except Exception as e:
            LOG.exception("push failed for %s", request.uris[0])
            context.abort(grpc.StatusCode.UNAVAILABLE, f"push failed: {e}")

    def PushBlob(self, request, context):
        self._push(request, context, "blob", request.blob_digest)
        return remote_asset_pb2.PushBlobResponse()

    def PushDirectory(self, request, context):
        self._push(request, context, "directory", request.root_directory_digest)
        return remote_asset_pb2.PushDirectoryResponse()


class CAS(re_grpc.ContentAddressableStorageServicer):
    def __init__(self, blobs: Blobs):
        self.blobs = blobs

    def FindMissingBlobs(self, request, context):
        missing = [d for d in request.blob_digests if not self.blobs.has(d)]
        return re_pb2.FindMissingBlobsResponse(missing_blob_digests=missing)

    def BatchUpdateBlobs(self, request, context):
        resp = re_pb2.BatchUpdateBlobsResponse()
        for r in request.requests:
            try:
                self.blobs.write(r.digest.hash, r.data)
                code = code_pb2.OK
            except ValueError:
                code = code_pb2.INVALID_ARGUMENT
            resp.responses.add(digest=r.digest, status=_status(code))
        return resp

    def BatchReadBlobs(self, request, context):
        resp = re_pb2.BatchReadBlobsResponse()
        for d in request.digests:
            try:
                resp.responses.add(digest=d, data=self.blobs.read(d), status=_status(code_pb2.OK))
            except FileNotFoundError:
                resp.responses.add(digest=d, status=_status(code_pb2.NOT_FOUND))
        return resp

    def GetTree(self, request, context):
        stack = [request.root_digest]
        seen: set[str] = set()
        page: list = []
        size = 0
        while stack:
            d = stack.pop()
            if d.hash in seen:
                continue
            seen.add(d.hash)
            try:
                directory = re_pb2.Directory.FromString(self.blobs.read(d))
            except FileNotFoundError:
                context.abort(grpc.StatusCode.NOT_FOUND, f"directory {d.hash} not found")
            page.append(directory)
            size += d.size_bytes
            stack.extend(sub.digest for sub in directory.directories)
            if size > MAX_BATCH // 2:
                yield re_pb2.GetTreeResponse(directories=page)
                page, size = [], 0
        yield re_pb2.GetTreeResponse(directories=page)


class ByteStream(bytestream_pb2_grpc.ByteStreamServicer):
    BLOB = re.compile(r"(?:^|/)blobs/([0-9a-f]{64})/(\d+)")

    def __init__(self, blobs: Blobs):
        self.blobs = blobs

    def Read(self, request, context):
        m = self.BLOB.search(request.resource_name)
        if not m:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "bad resource name")
        path = self.blobs.path(m.group(1))
        if int(m.group(2)) == 0:
            yield bytestream_pb2.ReadResponse(data=b"")
            return
        if path is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "blob not found")
        with open(path, "rb") as f:
            f.seek(request.read_offset)
            remaining = request.read_limit or -1
            while remaining:
                chunk = f.read(CHUNK if remaining < 0 else min(CHUNK, remaining))
                if not chunk:
                    break
                if remaining > 0:
                    remaining -= len(chunk)
                yield bytestream_pb2.ReadResponse(data=chunk)

    def Write(self, request_iterator, context):
        fd, tmp = tempfile.mkstemp(dir=self.blobs.tmp)
        h = hashlib.sha256()
        size = 0
        name = None
        with os.fdopen(fd, "wb") as f:
            for req in request_iterator:
                name = name or req.resource_name
                f.write(req.data)
                h.update(req.data)
                size += len(req.data)
        m = self.BLOB.search(name or "")
        if not m or m.group(1) != h.hexdigest():
            os.unlink(tmp)
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "digest mismatch")
        if self.blobs.path(m.group(1)) is None:
            self.blobs.adopt(m.group(1), tmp)
        else:
            os.unlink(tmp)
        return bytestream_pb2.WriteResponse(committed_size=size)

    def QueryWriteStatus(self, request, context):
        m = self.BLOB.search(request.resource_name)
        done = bool(m and self.blobs.path(m.group(1)))
        return bytestream_pb2.QueryWriteStatusResponse(
            committed_size=int(m.group(2)) if done else 0, complete=done
        )


class Capabilities(re_grpc.CapabilitiesServicer):
    def GetCapabilities(self, request, context):
        return re_pb2.ServerCapabilities(
            cache_capabilities=re_pb2.CacheCapabilities(
                digest_functions=[re_pb2.DigestFunction.SHA256],
                max_batch_total_size_bytes=MAX_BATCH,
                symlink_absolute_path_strategy=re_pb2.SymlinkAbsolutePathStrategy.ALLOWED,
            ),
            low_api_version=semver_pb2.SemVer(major=2, minor=0),
            high_api_version=semver_pb2.SemVer(major=2, minor=2),
        )


def build_server(packs: PackCache, blobs: Blobs, listen: str) -> tuple[grpc.Server, int]:
    server = grpc.server(
        concurrent.futures.ThreadPoolExecutor(max_workers=32),
        options=[
            ("grpc.max_receive_message_length", 64 * 1024 * 1024),
            ("grpc.max_send_message_length", 64 * 1024 * 1024),
        ],
    )
    remote_asset_pb2_grpc.add_FetchServicer_to_server(Fetch(packs), server)
    remote_asset_pb2_grpc.add_PushServicer_to_server(Push(packs), server)
    re_grpc.add_ContentAddressableStorageServicer_to_server(CAS(blobs), server)
    re_grpc.add_CapabilitiesServicer_to_server(Capabilities(), server)
    bytestream_pb2_grpc.add_ByteStreamServicer_to_server(ByteStream(blobs), server)
    port = server.add_insecure_port(listen)
    return server, port


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    repo = os.environ["CACHE_REPO"]
    push = os.environ.get("CACHE_PUSH") == "1"
    token = os.environ.get("REGISTRY_TOKEN") or None
    if push and not token:
        LOG.error("CACHE_PUSH=1 needs REGISTRY_TOKEN")
        return 2
    registry = Registry(repo, os.environ.get("REGISTRY_USER"), token, push)
    blobs = Blobs(os.environ.get("LOCAL_CAS", "/bstcache/cas"), os.environ.get("STORE", "/store"))
    upstreams = [u for u in os.environ.get("UPSTREAMS", "").split(",") if u]
    packs = PackCache(registry, blobs, push, upstreams, os.environ.get("USED_LOG"))
    listen = os.environ.get("LISTEN", "127.0.0.1:50051")
    server, _ = build_server(packs, blobs, listen)
    server.start()
    signal.signal(signal.SIGTERM, lambda *_: server.stop(30))
    LOG.info("serving on %s (push=%s)", listen, push)
    server.wait_for_termination()
    return 0


if __name__ == "__main__":
    sys.exit(main())
