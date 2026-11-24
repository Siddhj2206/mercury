#!/usr/bin/env python3
"""Update CI-managed source pins for x86_64, without committing or publishing."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CORE = "core-junctions"
# Overridden into gnome-build-meta, so it must provide every plugin GBM's
# project.conf loads: copy GBM's pin rather than tracking it independently.
PLUGINS_COMMUNITY = "elements/plugins/buildstream-plugins-community.bst"

# This is also CI's matrix. Keep review notes with the corresponding element.
TRACKED = [
    ("apps/brew.bst", "brew", ""),
    ("fonts/jetbrains-mono.bst", "jetbrains-mono", ""),
    ("boot/efibootmgr.bst", "efibootmgr", ""),
    ("virt/distrobox.bst", "distrobox", ""),
    ("system/xdg-terminal-exec.bst", "xdg-terminal-exec", ""),
    ("overrides/bootc.bst", "bootc", "review: core system component"),
    ("overrides/dnsmasq.bst", "dnsmasq", "review: core system component"),
    ("auth/sudo-rs.bst", "sudo-rs", "review: core system component"),
    ("system/uutils-coreutils.bst", "uutils-coreutils", "review: core system component"),
    # Despite its name this is a docker source, not a release tarball.
    ("apps/brew-tarball.bst", "brew-tarball", ""),
    # Same git source and track pattern as kernel/linux-fdsdk.bst, so both move
    # to the same stable tag on the same run.
    ("virt/hyperv-daemons.bst", "Hyper-V daemons",
     "review: tools/hv from the kernel/linux-fdsdk.bst tree"),
    ("hardware/brlaser.bst", "brlaser", ""),
    ("apps/fastfetch.bst", "fastfetch", ""),
    ("apps/kanata.bst", "kanata", ""),
    ("diagnostics/libtracefs.bst", "libtracefs", ""),
    ("virt/libvirt.bst", "libvirt", "review: libvirt and its git submodule"),
    ("hardware/lm-sensors.bst", "lm-sensors", ""),
    # The track pattern keeps the LV2 build on the 1.1 series.
    ("apps/lsp-plugins-lv2.bst", "lsp-plugins-lv2", ""),
    ("diagnostics/nethogs.bst", "nethogs", ""),
    ("virt/nspawn.bst", "nspawn",
     "review: CLI, D-Bus, and polkit changes across major versions"),
    ("diagnostics/sysstat.bst", "sysstat", ""),
    ("hardware/ddcutil.bst", "ddcutil",
     "review: libddcutil display-detection changes have crashed GPU drivers"),
    ("diagnostics/trace-cmd.bst", "trace-cmd", ""),
    ("virt/virtiofsd.bst", "virtiofsd", ""),
    ("apps/ydotool.bst", "ydotool", ""),
    # Branch heads: every update is unreleased code.
    ("hardware/usbmuxd.bst", "usbmuxd", "review: unreleased branch head"),
    # IBus Rime stack: each library follows its own release tags.
    ("input/glog.bst", "glog", ""),
    ("input/ibus-rime.bst", "ibus-rime", ""),
    ("input/leveldb.bst", "leveldb", ""),
    ("input/librime.bst", "librime",
     "review: the librime-lua plugin follows its unreleased branch head"),
    ("input/marisa-trie.bst", "marisa-trie", ""),
    ("input/opencc.bst", "OpenCC", ""),
    ("input/yaml-cpp.bst", "yaml-cpp", ""),
    ("diagnostics/tiptop.bst", "tiptop", "review: unreleased branch head"),
    # anitya sources: release-monitoring.org names the newest stable release.
    ("input/boost.bst", "boost", ""),
    ("system/nfs-utils.bst", "nfs-utils", ""),
    ("diagnostics/nicstat.bst", "nicstat", ""),
    ("system/rpcbind.bst", "rpcbind", ""),
    ("desktop/greetd.bst", "greetd", ""),
    # Private toolchain for Syncthing; any newer Go satisfies its go.mod.
    ("apps/syncthing-go.bst", "Go (Syncthing toolchain)", ""),
    ("plugins/buildstream-plugins.bst", "buildstream-plugins",
     "review: plugin junction bump"),
]


# The kernel ref is owned independently by testing and next. Respect each
# checkout's track pattern; never widen a stable series or force next to stable.
KERNELS = [
    ("kernel/linux-fdsdk.bst", "Linux kernel",
     "review: kernel patches and vendored FDSDK helpers"),
]


# Elements whose pin must equal another component's, so they move with it
# instead of on their own: the owner's updater rewrites them.
DERIVED = {
    # Lockstep with freedesktop-sdk's alsa-lib (matching libasound API).
    "hardware/alsa-utils.bst": "core-junctions",
    # Ghostty's minimum_zig_version; Zig breaks compatibility between minors.
    "apps/zig.bst": "apps/ghostty.bst",
}


# Elements with network sources that no updater moves, and why. The tests fail
# on any element with a network source that is neither updated nor listed here,
# so a new element cannot silently freeze at the version it was added with.
# A reason is a decision someone must make before the pin can move, not a
# missing updater.
PINNED = {
    "boot/fedora-shim.bst": "Secure Boot trust: a shim change alters what firmware will boot",
}


@dataclass(frozen=True)
class Release:
    # GitHub repository for the release lookup and changelog links; empty for
    # a feed outside GitHub.
    repo: str
    # Matches the version inside a source URL (group "version"); every match
    # in one URL must carry the same version and is replaced by `replacement`
    # (fields: tag, version, asset).
    pattern: str
    replacement: str
    x86_asset_suffix: str = ""
    query: str = ".tag_name"
    endpoint: str = "releases/latest"
    tag_pattern: str = r"v[0-9]+\.[0-9]+\.[0-9]+"
    # Pins the release together with sources derived from it, in place of a
    # URL rewrite; called with the version (tag without "v").
    generator: str = ""
    # Other elements the generator may rewrite in the same update.
    derived: tuple[str, ...] = ()
    # Releases outside GitHub: fetch this URL and take the newest version
    # matching feed_pattern (group "version"). {shell} expands to the GNOME
    # Shell major version that gnome-build-meta tracks.
    feed: str = ""
    feed_pattern: str = ""
    # Stay on the pinned series: the first `series` numeric components of the
    # version must match the pin (a driver branch, a distribution release).
    series: int = 0
    # How many source URLs carry the version. Multi-asset releases rewrite
    # them together; URLs matching `skip` belong to the paused architecture.
    urls: int = 1
    skip: str = ""
    # Other element keys that repeat the version, such as a remote filename.
    keys: tuple[str, ...] = ()
    # Asset names that embed more than the version (a build number or commit):
    # the one release asset fully matching this regex fills {asset}.
    asset: str = ""
    # Changelog link ({version}) for a feed outside GitHub.
    link: str = ""
    note: str = ""


RELEASES = {
    "apps/gum.bst": Release(
        "charmbracelet/gum", r"download/(?P<version>v[0-9.]+)/gum_[0-9.]+_",
        "download/{tag}/gum_{version}_", x86_asset_suffix="_Linux_x86_64.tar.gz"),
    "apps/gtk4-layer-shell.bst": Release(
        "wmww/gtk4-layer-shell", r"tags/(?P<version>v[0-9.]+)\.tar\.gz",
        "tags/{tag}.tar.gz"),
    "fonts/jetbrains-mono-nerd-font.bst": Release(
        "ryanoasis/nerd-fonts", r"download/(?P<version>v[^/]+)/", "download/{tag}/"),
    # No versioned GitHub releases (only a rolling "tip"), so read tags. Each
    # release changes the Zig dependency graph, which the generator re-pins.
    "apps/ghostty.bst": Release(
        "ghostty-org/ghostty", r"ghostty_releases:(?P<version>[0-9.]+)/", "",
        endpoint="tags?per_page=100",
        query='[.[].name | select(test("^v[0-9]+\\\\.[0-9]+\\\\.[0-9]+$"))]'
              ' | sort_by(ltrimstr("v") | split(".") | map(tonumber)) | last',
        generator="files/scripts/generate_ghostty_sources.py", derived=("apps/zig.bst",)),
    # The source archive vendors Go modules; apps/syncthing-go.bst may need to follow.
    "apps/syncthing.bst": Release(
        "syncthing/syncthing",
        r"download/(?P<version>v[0-9.]+)/syncthing-source-v[0-9.]+\.tar\.gz",
        "download/{tag}/syncthing-source-{tag}.tar.gz"),
    "hardware/ifuse.bst": Release(
        "libimobiledevice/ifuse", r"download/(?P<version>[0-9.]+)/ifuse-[0-9.]+\.tar",
        "download/{tag}/ifuse-{version}.tar", tag_pattern=r"[0-9]+\.[0-9]+\.[0-9]+"),
    "diagnostics/powertop.bst": Release(
        "fenrus75/powertop", r"tags/(?P<version>v[0-9.]+)\.tar\.gz", "tags/{tag}.tar.gz"),
    "system/nx.bst": Release(
        "Siddhj2206/nx", r"download/(?P<version>v[0-9.]+)/nx-v[0-9.]+-fc45-",
        "download/{tag}/nx-{tag}-fc45-", x86_asset_suffix="-x86_64.tar.gz"),
    "auth/pam-u2f.bst": Release(
        "", r"pam_u2f-(?P<version>[0-9.]+)\.tar\.gz", "pam_u2f-{version}.tar.gz",
        tag_pattern=r"[0-9]+\.[0-9]+\.[0-9]+",
        feed="https://developers.yubico.com/pam-u2f/Releases/atom.xml",
        feed_pattern=r"pam_u2f-(?P<version>[0-9.]+)\.tar\.gz",
        link="https://github.com/Yubico/pam-u2f/releases/tag/pam_u2f-{version}"),
    # The font archive and its fontconfig, license, and audit files.
    "fonts/nerd-fonts-symbols.bst": Release(
        "ryanoasis/nerd-fonts", r"(?<=/)(?P<version>v[0-9]+\.[0-9]+\.[0-9]+)(?=/)", "{tag}",
        urls=4),
    # The binary and its three shell completions; the ARM binary stays paused.
    "apps/tealdeer.bst": Release(
        "tealdeer-rs/tealdeer", r"download/(?P<version>v[0-9.]+)/", "download/{tag}/",
        urls=4, skip="aarch64"),
    "virt/open-vm-tools.bst": Release(
        "vmware/open-vm-tools",
        r"download/(?P<version>stable-[0-9.]+)/open-vm-tools-[0-9.]+-[0-9]+\.tar\.gz",
        "download/{tag}/{asset}", tag_pattern=r"stable-[0-9]+\.[0-9]+\.[0-9]+",
        asset=r"open-vm-tools-[0-9.]+-[0-9]+\.tar\.gz", note="review: local GCC patch still applies"),
}


def matrix() -> dict:
    return {"include": [dict(element=element, title=f"chore(deps): update {title}", note=note)
                        for element, title, note in TRACKED + KERNELS]}


def run(*args: str, capture: bool = False) -> str:
    result = subprocess.run(args, cwd=ROOT, check=True, text=True,
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else ""


def track(element: str) -> None:
    run("just", "bst", "--no-interactive", "-o", "arch", "x86_64",
        "source", "track", element)


PATCHED = re.compile(r"^\s*- kind:\s*(patch|patch_queue)\s*$", re.MULTILINE)


def check_patches(element: str) -> None:
    """Stage a patched element's sources so a local patch that stopped applying
    fails here, inside the rollback boundary, rather than in the bundle build."""
    if not PATCHED.search((ROOT / "elements" / element).read_text()):
        return
    # Relative to the checkout so `just bst`'s container sees the same path.
    scratch = Path(".source-check") / Path(element).stem
    print(f"Checking local patches still apply: {element}", flush=True)
    try:
        run("just", "bst", "--no-interactive", "-o", "arch", "x86_64",
            "source", "checkout", "--deps", "none", "--directory", str(scratch), element)
    finally:
        shutil.rmtree(ROOT / ".source-check", ignore_errors=True)


@contextmanager
def rollback_on_failure(paths: list[Path]):
    """Restore pre-invocation contents (including local edits), not Git HEAD."""
    with tempfile.TemporaryDirectory(prefix="mercury-source-update-") as tmp:
        backups = []
        for index, path in enumerate(paths):
            backup = Path(tmp) / str(index)
            if path.is_dir():
                shutil.copytree(path, backup)
            elif path.exists():
                shutil.copy2(path, backup)
            backups.append((path, backup))
        try:
            yield
        except BaseException:
            for path, backup in backups:
                if path.is_dir():
                    shutil.rmtree(path)
                elif path.exists():
                    path.unlink()
                if backup.is_dir():
                    shutil.copytree(backup, path)
                elif backup.exists():
                    shutil.copy2(backup, path)
            raise


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"[0-9]+", version))


def selected(release: Release, url: str) -> bool:
    # ARM is paused: preserve its URL as well as its checksum. Only the
    # selected x86_64 asset (or an architecture-independent URL) advances.
    if release.x86_asset_suffix and not url.endswith(release.x86_asset_suffix):
        return False
    return not (release.skip and re.search(release.skip, url))


def pinned_version(text: str, release: Release) -> str:
    for url in re.findall(r"^\s*url:\s+(\S+)", text, re.MULTILINE):
        if selected(release, url) and (match := re.search(release.pattern, url)):
            return match["version"]
    raise ValueError(f"No selected source URL matches {release.pattern!r}")


def rewrite_release(text: str, release: Release, tag: str, asset: str = "") -> tuple[str, str]:
    if not re.fullmatch(release.tag_pattern, tag):
        raise ValueError(f"Unexpected release tag for {release.repo or release.feed}: {tag!r}")
    if release.asset and not re.fullmatch(release.asset, asset):
        raise ValueError(f"Unexpected release asset for {release.repo}: {asset!r}")
    versions = []
    count = 0
    version = tag.removeprefix("v")
    replacement = release.replacement.format(tag=tag, version=version, asset=asset)

    def replace_value(match):
        nonlocal count
        key, value = match.group(2), match.group(3)
        if key == "url" and not selected(release, value):
            return match.group(0)
        found = {m.group("version") for m in re.finditer(release.pattern, value)}
        if len(found) != 1:
            raise ValueError(f"Expected one release version in {key}: {value}")
        if key == "url":
            versions.extend(found)
            count += 1
        return match.group(1) + re.sub(release.pattern, lambda _: replacement, value)

    # Change source URLs (and keys that repeat the version) only, never
    # comments, refs, or install commands.
    keys = "|".join(re.escape(key) for key in ("url", *release.keys))
    updated = re.sub(rf"^(\s*({keys}):\s+'?)([^'\s]+)", replace_value, text, flags=re.MULTILINE)
    if count != release.urls:
        raise ValueError(f"Expected {release.urls} selected source URL(s) for "
                         f"{release.repo or release.feed}, found {count}")
    return updated, ", ".join(dict.fromkeys(versions))


def gnome_shell_version() -> str:
    text = (ROOT / "elements/gnome-build-meta.bst").read_text()
    match = re.search(r"^\s*track:\s*gnome-([0-9]+)\s*$", text, re.MULTILINE)
    if not match:
        raise ValueError("Cannot read the GNOME version gnome-build-meta.bst tracks")
    return match[1]


def latest_release(element: str, release: Release, current: str) -> tuple[str, str]:
    """Return the newest release tag (and asset name, when the release names one)."""
    if release.feed:
        feed = release.feed.format(shell=gnome_shell_version()) if "{shell}" in release.feed else release.feed
        body = run("curl", "-fsSL", feed, capture=True)
        candidates = {m["version"] for m in re.finditer(release.feed_pattern, body)}
        candidates = [v for v in candidates if re.fullmatch(release.tag_pattern, v)
                      and version_key(v)[:release.series] == version_key(current)[:release.series]]
        if not candidates:
            raise ValueError(f"No release matching {release.tag_pattern!r} in {feed}")
        return max(candidates, key=version_key), ""
    if release.asset:
        lines = run("gh", "api", f"repos/{release.repo}/{release.endpoint}",
                    "--jq", "[.tag_name] + [.assets[].name] | .[]", capture=True).splitlines()
        assets = [name for name in lines[1:] if re.fullmatch(release.asset, name)]
        if not lines or len(assets) != 1:
            raise ValueError(f"Expected one asset matching {release.asset!r} in {release.repo}")
        return lines[0], assets[0]
    return run("gh", "api", f"repos/{release.repo}/{release.endpoint}",
               "--jq", release.query, capture=True), ""


def release_links(release: Release, old: str, tag: str) -> str:
    if not release.repo:
        return f"[release]({release.link.format(version=tag.removeprefix('v'))})" if release.link else ""
    if re.fullmatch(r"[0-9a-f]{40}", tag):
        return f"[compare](https://github.com/{release.repo}/compare/{old}...{tag})"
    links = f"[release](https://github.com/{release.repo}/releases/tag/{tag})"
    if ", " not in old:
        old_tag = ("v" if tag.startswith("v") else "") + old.removeprefix("v")
        links += f" · [compare](https://github.com/{release.repo}/compare/{old_tag}...{tag})"
    return links


def update_release(element: str, out: Path | None) -> None:
    release = RELEASES[element]
    path = ROOT / "elements" / element
    original = path.read_text()
    current = (re.search(release.pattern, original)["version"] if release.generator
               else pinned_version(original, release))
    tag, asset = latest_release(element, release, current)
    if not re.fullmatch(release.tag_pattern, tag):
        raise ValueError(f"Unexpected release tag for {release.repo or release.feed}: {tag!r}")
    # A feed can list an older build than the pin (a withdrawn release, an
    # extension dropping support); never move backwards.
    if (not re.fullmatch(r"[0-9a-f]{40}", tag)
            and version_key(tag) < version_key(current)):
        print(f"{element}: pinned {current} is newer than upstream's {tag}; keeping it")
        return
    derived = {extra: (ROOT / "elements" / extra).read_text() for extra in release.derived}
    if release.generator:
        old = current
        if old == tag.removeprefix("v"):
            print(f"{element}: already up to date")
            return
        run(sys.executable, release.generator, tag.removeprefix("v"))
    else:
        updated, old = rewrite_release(original, release, tag, asset)
        if updated == original:
            print(f"{element}: already up to date")
            return
        path.write_text(updated)
        track(element)
        check_patches(element)
    if out is not None:
        slug = Path(element).stem
        # Report versions in the element's own style (with or without "v").
        new = tag if old.startswith("v") else tag.removeprefix("v")
        files = [f"elements/{element}"] + [f"elements/{extra}" for extra, text in derived.items()
                                           if (ROOT / "elements" / extra).read_text() != text]
        run(sys.executable, ".github/scripts/track_bundle.py", "record",
            "--out", str(out), "--slug", slug,
            "--title", f"chore(deps): update {slug} {old} -> {new}",
            "--change", f"`{old}` → `{new}`", "--links", release_links(release, old, tag),
            "--note", release.note, *files)


def gbm_file(sha: str, path: str) -> str:
    quoted = path.replace("/", "%2F")
    url = ("https://gitlab.gnome.org/api/v4/projects/GNOME%2Fgnome-build-meta/"
           f"repository/files/{quoted}/raw?ref={sha}")
    return run("curl", "-fsSL", url, capture=True)


def sync_plugins_community(upstream: str) -> None:
    source = re.search(r"^- kind: tar\n  url: (pypi:[A-Za-z0-9/._-]+\.tar\.gz)\n"
                       r"  ref: ([0-9a-f]{64})$", upstream, re.MULTILINE)
    if not source:
        raise ValueError("Could not read buildstream-plugins-community pin from GNOME Build Meta")
    path = ROOT / PLUGINS_COMMUNITY
    text, count = re.subn(r"^(  url: )pypi:\S+\n(  ref: )\S+$",
                          lambda m: f"{m[1]}{source[1]}\n{m[2]}{source[2]}",
                          path.read_text(), count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError("Missing local buildstream-plugins-community tar source")
    path.write_text(text)


def fdsdk_file(ref: str, path: str) -> str:
    sha = re.search(r"-g([0-9a-f]{40})$", ref)
    if not sha:
        raise ValueError(f"Cannot read a commit from the freedesktop-sdk ref {ref!r}")
    quoted = path.replace("/", "%2F")
    url = ("https://gitlab.com/api/v4/projects/freedesktop-sdk%2Ffreedesktop-sdk/"
           f"repository/files/{quoted}/raw?ref={sha[1]}")
    return run("curl", "-fsSL", url, capture=True)


def sync_alsa_utils(upstream: str) -> None:
    """Build the alsa-utils release matching freedesktop-sdk's alsa-lib."""
    lib = re.search(r"^  ref: v([0-9]+(?:\.[0-9]+){2,3})-[0-9]+-g[0-9a-f]{40}$", upstream, re.MULTILINE)
    if not lib:
        raise ValueError("Could not read the alsa-lib release from freedesktop-sdk")
    release = ALSA_UTILS
    # alsa-lib hotfixes (1.2.16.1) pair with the alsa-utils release of their series.
    candidates = [v for v in {m["version"] for m in re.finditer(
                      release.feed_pattern, run("curl", "-fsSL", release.feed, capture=True))}
                  if version_key(v)[:3] == version_key(lib[1])[:3]
                  and version_key(v) <= version_key(lib[1])]
    if not candidates:
        raise ValueError(f"No alsa-utils release for alsa-lib {lib[1]}")
    path = ROOT / "elements/hardware/alsa-utils.bst"
    original = path.read_text()
    updated, _ = rewrite_release(original, release, max(candidates, key=version_key))
    if updated != original:
        path.write_text(updated)
        track("hardware/alsa-utils.bst")


ALSA_UTILS = Release(
    "", r"alsa-utils-(?P<version>[0-9.]+)\.tar", "alsa-utils-{version}.tar",
    tag_pattern=r"[0-9]+(?:\.[0-9]+){2,3}", feed="https://www.alsa-project.org/files/pub/utils/",
    feed_pattern=r"alsa-utils-(?P<version>[0-9]+(?:\.[0-9]+){2,3})\.tar\.bz2")
CORE_DERIVED = [f"elements/{element}" for element, owner in DERIVED.items() if owner == CORE]


def update_core() -> None:
    track("gnome-build-meta.bst")
    gbm = (ROOT / "elements/gnome-build-meta.bst").read_text()
    ref = re.search(r"^\s*ref: (\S+)", gbm, re.MULTILINE)
    sha = re.search(r"-g([0-9a-f]{40})$", ref[1]) if ref else None
    if not sha:
        raise ValueError("Could not extract GNOME Build Meta commit SHA")
    upstream = gbm_file(sha[1], "elements/freedesktop-sdk.bst")
    # Read the ref from the git source, not another source or config block.
    source = re.search(r"^  url: gitlab:freedesktop-sdk/[^\n]+\n"
                       r"(?:(?!^\S)[^\n]*\n)*?^  ref: (\S+)", upstream, re.MULTILINE)
    if not source or not re.fullmatch(r"[A-Za-z0-9._-]+", source[1]):
        raise ValueError("Could not read freedesktop-sdk pin from GNOME Build Meta")
    path = ROOT / "elements/freedesktop-sdk.bst"
    text, count = re.subn(r"^(\s*)ref:.*$", lambda m: f"{m[1]}ref: {source[1]}",
                          path.read_text(), count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError("Missing local freedesktop-sdk ref")
    if path.read_text() != text:
        print("REVIEW: FDSDK changed. Compare kernel/linux-fdsdk.bst, patches/linux, "
              "files/linux/config-utils.sh and files/linux/fdsdk-config.sh with the new SDK; "
              "preserve Mercury's local kernel configuration.")
    path.write_text(text)
    sync_plugins_community(gbm_file(sha[1], "elements/plugins/buildstream-plugins-community.bst"))
    sync_alsa_utils(fdsdk_file(source[1], "elements/components/alsa-lib.bst"))
    run("just", "patch-sync")
    run("just", "patch-drift-check")


def update(element: str, out: Path | None) -> None:
    paths = [ROOT / "elements" / element]
    if element == CORE:
        paths = [ROOT / p for p in ("elements/gnome-build-meta.bst",
                 "elements/freedesktop-sdk.bst", PLUGINS_COMMUNITY, "patches/freedesktop-sdk",
                 "patches/freedesktop-sdk.manifest.json", *CORE_DERIVED)]
    elif element in RELEASES:
        paths += [ROOT / "elements" / extra for extra in RELEASES[element].derived]
    with rollback_on_failure(paths):
        if element == CORE:
            update_core()
        elif element in RELEASES:
            update_release(element, out)
        else:
            track(element)
            # Tracking a git ref does not apply subsequent patch sources, and
            # neither does fetching: only staging runs them. Stage before
            # accepting the pin, inside the rollback boundary.
            check_patches(element)
            if element in {item[0] for item in KERNELS}:
                print(f"REVIEW: {element}: patches apply; build the kernel "
                      "before shipping.")
            if out is not None:
                item = next(item for item in matrix()["include"] if item["element"] == element)
                run(sys.executable, ".github/scripts/track_bundle.py", "record-element",
                    "--element", element, "--title", item["title"], "--note", item["note"],
                    "--out", str(out))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    select = parser.add_mutually_exclusive_group()
    select.add_argument("--group", choices=("all", "bundle", "tracked", "tarballs", "kernels", CORE),
                        default="all", help="update subset (default: all)")
    select.add_argument("--element", choices=[item[0] for item in TRACKED + KERNELS] + list(RELEASES),
                        metavar="ELEMENT", help="one CI-managed element; use --list to see the scope")
    parser.add_argument("--list", action="store_true", help="list selected updates without network or writes")
    parser.add_argument("--matrix", action="store_true", help="print the CI tracking matrix as JSON")
    parser.add_argument("--record-dir", type=Path, help="CI only: record successful bundle updates here")
    parser.add_argument("--failure-dir", type=Path,
                        help="CI only: record failed updates here (default: --record-dir)")
    parser.add_argument("--pinned", action="store_true",
                        help="print the deliberately pinned elements and reasons as JSON")
    args = parser.parse_args(argv)
    if args.matrix:
        print(json.dumps(matrix()))
        return 0
    if args.pinned:
        print(json.dumps(PINNED))
        return 0
    selected = []
    if args.element:
        selected = [args.element]
    else:
        if args.group in ("all", "bundle", "tracked"):
            selected.extend(item[0] for item in TRACKED + KERNELS)
        if args.group == "kernels":
            selected.extend(item[0] for item in KERNELS)
        if args.group in ("all", "bundle", "tarballs"):
            selected.extend(RELEASES)
        if args.group in ("all", CORE):
            selected.append(CORE)
    if args.list:
        print("\n".join(selected))
        return 0
    failed = []
    out = args.record_dir.resolve() if args.record_dir else None
    failures = args.failure_dir.resolve() if args.failure_dir else out
    for element in selected:
        print(f"Updating {element}", flush=True)
        try:
            update(element, out)
        except (OSError, ValueError, subprocess.CalledProcessError) as exc:
            print(f"FAILED {element}: {exc}", file=sys.stderr)
            failed.append(element)
            if failures is not None:
                # The bundle PR lists these, so a stuck element is not only
                # visible in this job's log.
                reason = (f"`{' '.join(exc.cmd[:2])}` exited {exc.returncode}; see the run log"
                          if isinstance(exc, subprocess.CalledProcessError) else str(exc))
                record = failures / "failed" / f"{Path(element).stem}.json"
                record.parent.mkdir(parents=True, exist_ok=True)
                record.write_text(json.dumps({"element": element, "error": reason[:300]}) + "\n")
    if failed:
        print("Failed updates (restored to their starting contents): " + ", ".join(failed),
              file=sys.stderr)
        return 1
    print("Source update pass complete. Review git diff, then run just validate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
