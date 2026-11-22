# Security Policy

## Supported Versions

The `latest` tag on `ghcr.io/siddhj2206/mercury` always reflects the
current supported release. Older builds identified by their commit SHA or
`VERSION.DATE` tag are not actively maintained for security updates.

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Report security vulnerabilities privately via GitHub's Security Advisory
feature (Siddhj2206/mercury → Security → Advisories → New draft advisory).

## Disclosure Policy

We follow coordinated vulnerability disclosure:

1. You report the vulnerability privately using the channel above.
2. We acknowledge receipt within **5 business days**.
3. We investigate and work on a fix, keeping you informed of progress.
4. We aim to release a fix within **30 days** of confirmation.
5. For complex issues requiring upstream coordination, the timeline may
   extend to **90 days**. We will notify you if this is the case.
6. We publicly disclose the vulnerability after a fix is available, or
   after the agreed-upon disclosure deadline has passed.

## Supply Chain Security

Mercury images are signed with keyless OIDC signatures via Sigstore/cosign,
produced by `.github/workflows/build.yml` on pushes to `main`.

Verify the image signature:
```bash
cosign verify \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  --certificate-identity-regexp '^https://github.com/Siddhj2206/mercury/.github/workflows/build.yml' \
  ghcr.io/siddhj2206/mercury:latest
```
