# Signing and notarization (optional)

Unsigned builds work end to end. Signing is optional and is enabled only by adding repository secrets;
when they are absent, the workflow logs that signing was skipped. No secret values are echoed.

## macOS Developer ID + notarization

Required secrets/variables (repository settings → Secrets and variables → Actions):

| Name | Purpose |
|---|---|
| `APPLE_CERT_P12_BASE64` | base64 of the Developer ID Application `.p12` |
| `APPLE_CERT_PASSWORD` | password for that `.p12` |
| `APPLE_TEAM_ID` | Apple Developer team ID |
| `APPLE_ID` | Apple ID used for notarization |
| `APPLE_APP_SPECIFIC_PASSWORD` | app-specific password for `notarytool` |

The release workflow should import the certificate into a temporary keychain, run
`codesign --force --options runtime --timestamp --sign "Developer ID Application: …"` on the `.app` and DMG,
then `xcrun notarytool submit --wait`, `xcrun stapler staple`, and `spctl --assess --type execute` on the
final artifacts. Without the secrets, the build uses ad-hoc signing (`codesign --sign -`) as required on
Apple Silicon.

## Windows SignPath

SignPath Foundation is free for qualifying open-source projects. Add:

- secret `SIGNPATH_API_TOKEN`
- variables `SIGNPATH_ORGANIZATION_ID`, `SIGNPATH_PROJECT_SLUG`, `SIGNPATH_SIGNING_POLICY_SLUG`

The workflow should submit the unsigned EXE/installer, wait for signing, download the signed artifact, and
then attach it to the draft release. Verify with `Get-AuthenticodeSignature`.

Code-signing policy text for SignPath:

> BackupLens is an open-source, local-only application distributed under GPL-3.0-or-later. Release
> artifacts are built by the public GitHub Actions workflow from the tagged source. Signing requests come
> only from that workflow, and the signed binaries are published only on the project's GitHub Releases.

## Linux

Linux artifacts are unsigned; publish `SHA256SUMS.txt`. Users can verify with `sha256sum`.

## Never commit

No certificate, private key, API token, Apple ID password or `p12` may be committed. Add them only as
encrypted repository secrets. A leaked secret must be rotated and the artifact/history treated as an
incident.
