"""End-to-end tests for scripts/bst_ghcr_cache.py.

Needs grpcio and BuildStream's protos, so it runs inside the bst2 container:
`just test-cache-proxy`. A fake OCI registry (with a bearer-token challenge,
like ghcr) runs in-process; no network access is needed.
"""

from __future__ import annotations

import hashlib
import http.server
import json
import os
import re
import sys
import tempfile
import threading
import typing
import unittest
import uuid

import grpc

sys.path.insert(0, os.path.dirname(__file__))

import bst_ghcr_cache as cache
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
from buildstream._protos.google.bytestream import bytestream_pb2, bytestream_pb2_grpc
from buildstream._protos.google.rpc import code_pb2

TOKEN = "test-bearer"


class FakeRegistry(http.server.BaseHTTPRequestHandler):
    blobs: typing.ClassVar[dict[str, bytes]] = {}
    manifests: typing.ClassVar[dict[str, bytes]] = {}
    uploads: typing.ClassVar[dict[str, bool]] = {}

    def log_message(self, *args):
        pass

    def _send(self, code, body=b"", headers=None):
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _authorized(self):
        if self.path.startswith("/token"):
            return True
        if self.headers.get("Authorization") == f"Bearer {TOKEN}":
            return True
        host = self.headers["Host"]
        self._send(401, headers={"WWW-Authenticate": f'Bearer realm="http://{host}/token",service="fake"'})
        return False

    def _body(self):
        return self.rfile.read(int(self.headers.get("Content-Length") or 0))

    def do_GET(self):
        if not self._authorized():
            return
        if self.path.startswith("/token"):
            return self._send(200, json.dumps({"token": TOKEN}).encode())
        if m := re.match(r"/v2/[^?]+/tags/list", self.path):
            if not self.manifests:
                return self._send(404)
            return self._send(200, json.dumps({"tags": sorted(self.manifests)}).encode())
        if m := re.match(r"/v2/.+/manifests/(.+)$", self.path):
            body = self.manifests.get(m.group(1))
            return self._send(200, body) if body else self._send(404)
        if m := re.match(r"/v2/.+/blobs/(sha256:[0-9a-f]+)$", self.path):
            body = self.blobs.get(m.group(1))
            return self._send(200, body) if body is not None else self._send(404)
        self._send(404)

    def do_HEAD(self):
        if not self._authorized():
            return
        if m := re.match(r"/v2/.+/blobs/(sha256:[0-9a-f]+)$", self.path):
            return self._send(200 if m.group(1) in self.blobs else 404)
        self._send(404)

    def do_POST(self):
        if not self._authorized():
            return
        self._body()
        upload = uuid.uuid4().hex
        self.uploads[upload] = True
        self._send(202, headers={"Location": f"/v2/repo/blobs/uploads/{upload}"})

    def do_PUT(self):
        if not self._authorized():
            return
        body = self._body()
        if m := re.match(r"/v2/.+/blobs/uploads/(\w+)\?digest=(.+)$", self.path):
            digest = m.group(2).replace("%3A", ":")
            assert digest == "sha256:" + hashlib.sha256(body).hexdigest()
            self.blobs[digest] = body
            return self._send(201)
        if m := re.match(r"/v2/.+/manifests/(.+)$", self.path):
            self.manifests[m.group(1)] = body
            return self._send(201)
        self._send(400)


def put_blob(objects: str, data: bytes) -> re_pb2.Digest:
    h = hashlib.sha256(data).hexdigest()
    path = os.path.join(objects, h[:2], h[2:])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return re_pb2.Digest(hash=h, size_bytes=len(data))


class CacheProxyTest(unittest.TestCase):
    def setUp(self):
        FakeRegistry.blobs, FakeRegistry.manifests = {}, {}
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeRegistry)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.repo = f"127.0.0.1:{self.httpd.server_address[1]}/owner/cache"
        self.tmp = tempfile.TemporaryDirectory()
        self.servers = []

    def tearDown(self):
        for s in self.servers:
            s.stop(0)
        self.httpd.shutdown()
        self.httpd.server_close()
        self.tmp.cleanup()

    def proxy(self, name: str, push: bool):
        local = os.path.join(self.tmp.name, name, "cas")
        os.makedirs(os.path.join(local, "objects"))
        blobs = cache.Blobs(local, os.path.join(self.tmp.name, name, "store"))
        registry = cache.Registry(self.repo, "user", "secret", push)
        packs = cache.PackCache(registry, blobs, push, [], None)
        server, port = cache.build_server(packs, blobs, "127.0.0.1:0")
        server.start()
        self.servers.append(server)
        self.addCleanup(lambda: channel.close())
        channel = grpc.insecure_channel(f"127.0.0.1:{port}")
        return os.path.join(local, "objects"), channel

    def test_push_then_pull_in_a_fresh_cache(self):
        objects, channel = self.proxy("builder", push=True)
        big = os.urandom(3 * cache.CHUNK + 17)
        f1 = put_blob(objects, b"hello\n")
        f2 = put_blob(objects, big)
        sub = re_pb2.Directory(files=[re_pb2.FileNode(name="big", digest=f2)])
        sub_d = put_blob(objects, sub.SerializeToString())
        root = re_pb2.Directory(
            files=[re_pb2.FileNode(name="hello", digest=f1)],
            directories=[re_pb2.DirectoryNode(name="sub", digest=sub_d)],
        )
        root_d = put_blob(objects, root.SerializeToString())
        meta = put_blob(objects, b"metadata")
        art = put_blob(objects, b"artifact-proto")
        uris = [
            "urn:fdc:buildstream.build:2020:artifact:mercury/apps-thing/" + "a" * 64,
            "urn:fdc:buildstream.build:2020:artifact:mercury/apps-thing/" + "b" * 64,
        ]

        push = remote_asset_pb2_grpc.PushStub(channel)
        push.PushBlob(
            remote_asset_pb2.PushBlobRequest(
                uris=uris, blob_digest=art, references_blobs=[meta], references_directories=[root_d]
            )
        )
        self.assertEqual(set(FakeRegistry.manifests), {cache.tag_for(u) for u in uris})

        # Nothing is missing on the builder: blobs come from casd's store.
        cas = re_grpc.ContentAddressableStorageStub(channel)
        missing = cas.FindMissingBlobs(re_pb2.FindMissingBlobsRequest(blob_digests=[f1, f2, art]))
        self.assertEqual(list(missing.missing_blob_digests), [])

        _, fresh = self.proxy("consumer", push=False)
        fetch = remote_asset_pb2_grpc.FetchStub(fresh)
        resp = fetch.FetchBlob(remote_asset_pb2.FetchBlobRequest(uris=[uris[1]]))
        self.assertEqual(resp.status.code, code_pb2.OK)
        self.assertEqual(resp.blob_digest, art)

        cas = re_grpc.ContentAddressableStorageStub(fresh)
        read = cas.BatchReadBlobs(re_pb2.BatchReadBlobsRequest(digests=[f1, meta, art]))
        self.assertEqual([r.data for r in read.responses], [b"hello\n", b"metadata", b"artifact-proto"])
        tree = list(cas.GetTree(re_pb2.GetTreeRequest(root_digest=root_d)))
        self.assertEqual(sum(len(t.directories) for t in tree), 2)

        bs = bytestream_pb2_grpc.ByteStreamStub(fresh)
        data = b"".join(
            r.data for r in bs.Read(bytestream_pb2.ReadRequest(resource_name=f"blobs/{f2.hash}/{f2.size_bytes}"))
        )
        self.assertEqual(data, big)

        miss = fetch.FetchBlob(
            remote_asset_pb2.FetchBlobRequest(uris=["urn:fdc:buildstream.build:2020:artifact:x/y/" + "c" * 64])
        )
        self.assertEqual(miss.status.code, code_pb2.NOT_FOUND)

    def test_sources_are_never_pushed(self):
        objects, channel = self.proxy("builder", push=True)
        d = put_blob(objects, re_pb2.Directory().SerializeToString())
        push = remote_asset_pb2_grpc.PushStub(channel)
        for uri in (
            "urn:fdc:buildstream.build:2020:source:local/" + "d" * 64,
            "urn:fdc:buildstream.build:2020:source:" + "e" * 64,
        ):
            with self.assertRaises(grpc.RpcError) as ctx:
                push.PushDirectory(remote_asset_pb2.PushDirectoryRequest(uris=[uri], root_directory_digest=d))
            self.assertEqual(ctx.exception.code(), grpc.StatusCode.PERMISSION_DENIED)
        self.assertEqual(FakeRegistry.manifests, {})

    def test_read_only_proxy_refuses_pushes(self):
        objects, channel = self.proxy("reader", push=False)
        art = put_blob(objects, b"artifact")
        push = remote_asset_pb2_grpc.PushStub(channel)
        with self.assertRaises(grpc.RpcError) as ctx:
            push.PushBlob(
                remote_asset_pb2.PushBlobRequest(
                    uris=["urn:fdc:buildstream.build:2020:artifact:m/e/" + "f" * 64], blob_digest=art
                )
            )
        self.assertEqual(ctx.exception.code(), grpc.StatusCode.PERMISSION_DENIED)


if __name__ == "__main__":
    unittest.main()
