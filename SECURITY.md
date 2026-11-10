# Security policy

## Supported versions

Security fixes are applied to the latest release on the `main` branch.

## Reporting a vulnerability or privacy issue

Please **do not open a public issue** for a vulnerability, a leaked secret, a way to read data outside the
chosen backup, or any accidental personal-data exposure.

Use GitHub's private vulnerability reporting on this repository:

https://github.com/tkrishnakanth/backuplens/security/advisories/new

Include:

- affected version and OS;
- a minimal description and reproduction steps;
- impact (confidentiality/integrity/availability);
- whether a backup, password or personal data is involved.

You should receive an acknowledgement within a few days. Please allow time for a fix and coordinated
disclosure.

## Scope and threat model

BackupLens is a **local-only** application:

- It binds to `127.0.0.1` on a random free port and requires a per-launch token. Host/Origin checks block
  DNS-rebinding and cross-site requests. The frontend makes no outbound requests.
- It opens an iOS backup **read-only**. It must never write, delete or modify anything in the backup folder.
- The backup password is used only in memory to unlock the backup. It is never logged, written to disk,
  sent over a network or stored in the configuration file.
- Decrypted temporary data and the media cache are removed on exit unless cache persistence is explicitly
  enabled. "Clear cache" is always available.
- Exports are written only to a user-chosen destination outside the backup, with path-containment checks.

Reports that require an attacker to already have local access to the user's account, or that rely on
modifying the application binary, are generally out of scope. Reports about a secret/device identifier in
the repository or a released artifact are in scope and treated as incidents.

## If you find personal data in a release

Do not copy it into an issue. Report the category and file path only through private vulnerability
reporting; the maintainers will remove the artifact/commit history and rotate anything exposed.
