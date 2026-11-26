# About this fork

`ntserver2003/AWG-Router` is a fork of [r-slashslash/AWG-Router](https://github.com/r-slashslash/AWG-Router). It follows upstream every day. Panels installed from it update from this fork, not from upstream.

## What differs from upstream

| File | Change |
|---|---|
| `install.sh`, `app/updates.py` | The default `AWGR_REPO` is `ntserver2003/AWG-Router`. Installs, `awg-router update`, the panel's Update button and its new-version check all use this fork. |
| `app/static/js/system.js` | The "What's new" link opens this fork's release. |
| `Dockerfile`, `awg-server/Dockerfile` | `org.opencontainers.image.source` points to this fork, so the images in `ghcr.io/ntserver2003/awg-router` are linked to this repository. |
| `app/awgserver.py`, `tests/test_fork_peer_comments.py` | `#` comments inside a `[Peer]` block survive the panel's rewrites of the server config. They're written back right after `[Peer]`, where amneziawg-installer keeps `#_Name = <name>`. Without this, the installer and bots built on it, such as awgram, lose all their clients on the panel's first write. In a client disabled in the panel, they're commented out (`# #_Name = …`), so the installer doesn't see it. Comment lines with control characters are dropped when a backup is restored. |
| `.github/workflows/sync-upstream.yml` | Daily sync with upstream, plus publishing releases (see below). |
| `FORK.md` | This file. |

Keep fork-only changes small and in as few lines as possible. Every line upstream also edits becomes a merge conflict.

## How releases flow

1. Every day at 02:41 UTC, `sync-upstream.yml` merges upstream `main` into `main`. It uses the GitHub "Sync fork" API, which creates a merge commit when this fork has its own commits.
2. That push runs upstream's own `release.yml` here. It runs the tests, builds the panel and server images into `ghcr.io/ntserver2003/awg-router`, and creates or refreshes the draft `v<VERSION>`.
3. After upstream publishes `vX`, the next `Release` run here, or the next daily run, publishes this fork's draft `vX` as Latest. It does this only if the archive carries `IMAGES`, the prebuilt images.
4. Installed panels see `vX` within 6 hours (`app/updates.py`) and install it from this fork's release archive.

A fork release `vX` contains upstream `main` at the time of publishing, plus this fork's changes. That can include upstream commits made after its own `vX` release that kept the same version. Fork changes made after `vX` is published reach panels with the next upstream version.

## One-time setup

1. **Actions:** open the **Actions** tab and enable workflows. GitHub turns them off in new forks.
   - Disable `E2E` and `OpenSSF Scorecard` there. They test upstream's release path and score upstream's repository.
2. **Secret `SYNC_TOKEN`:** go to Settings → Secrets and variables → Actions.
   - Use a fine-grained token for this repository only, with **Contents: read and write** and **Workflows: read and write**.
   - `GITHUB_TOKEN` cannot merge upstream changes to `.github/workflows`, and its pushes don't start `release.yml`.
3. **Package:** after the first `Release` run, make `ghcr.io/ntserver2003/awg-router` public.
   - Go to github.com/users/ntserver2003/packages/container/awg-router/settings → Change visibility → Public.
   - While it is private, panels build the images themselves, and `release.yml` warns about it.
4. **Optional:** enable Issues, so a failed sync opens an issue. Without Issues, the failed run and GitHub's e-mail about it are the report.

## Switching an installed panel to this fork

This needs root on the server, and you only do it once:

```sh
AWGR_REPO=ntserver2003/AWG-Router bash /opt/awg-router/install.sh --update
```

After that, the installed `install.sh` and the panel already default to this fork.

## When the sync fails

```sh
git fetch upstream
git merge upstream/main     # resolve conflicts, keeping the fork's lines from the table above
git push origin main
```
