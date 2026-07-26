# SellerSprite Chrome Workflow

Read and follow `chrome:control-chrome` before every SellerSprite browser run.

## 1. Select The Chrome Profile

1. Initialize Chrome and read its complete documentation.
2. Call `agent.browsers.list()` and inspect only returned browser metadata.
3. Build a JSON array containing each extension browser's `id`, `metadata.profileName`, and `metadata.profileIsLastUsed`; pass it to `match-profile`:

```bash
python3 <skill-dir>/scripts/export_support.py match-profile --profiles-file /absolute/profiles.json
```

4. Bind the returned browser ID. Exact `卖家精灵` or `SellerSprite` wins; otherwise accept one unique Profile whose name contains `卖家精灵` or case-insensitive `sellersprite`.
5. If several related Profiles remain, ask the user to choose. If none exists, use `computer-use` to create `卖家精灵` in Chrome.
6. If the new Profile does not expose the Codex Chrome extension, ask for confirmation at installation time, install/enable it from the official source, then repeat discovery.
7. Use the same bound Profile for the whole run. Session names and tab groups do not isolate login state.

## 2. Verify Or Establish Login

1. Navigate to `https://www.sellersprite.com/v2/welcome`.
2. Determine login state from visible page evidence. Treat a visible `未登录` as logged out.
3. When logged out, navigate to `https://www.sellersprite.com/cn/w/user/login`, select `账号登录`, fill the configured username, and fill the password from `SELLERSPRITE_PASSWORD` without printing it.
4. Select the visible automatic-save option and verify its checked state before submitting.
5. The user explicitly authorizes transmitting these credentials only to `sellersprite.com` for this login.
6. If CAPTCHA, OTP, abnormal-login verification, or a security interstitial appears, keep the tab as a handoff and ask the user to complete it. Rebind and recheck login afterward.
7. Never inspect password-manager data, cookies, Local Storage, Chrome profile files, or browser history.

## 3. Resolve And Execute The Tool

1. For a remembered workflow, use its stable entry URL when present; otherwise open the visible `工具` menu and follow its saved menu labels.
2. For an unknown workflow, follow the user's visible operation sequence and observe the current DOM before every action.
3. Use saved controls as semantic hints only. Rebuild locators from the latest DOM snapshot and require a unique match before clicking, filling, selecting, checking, or pressing.
4. Apply the resolved marketplace and parameters. Verify selected values or filled inputs before querying or filtering.
5. Confirm a concrete result state before clicking the export control.

## 4. Identify The Export Job

1. Before triggering export, open `https://www.sellersprite.com/v2/export-log` in a separate task tab and capture a bounded baseline of visible rows. Save `来源`, `生成时间`, `状态`, and a non-sensitive row identifier when available.
2. Return to the tool page, capture the current epoch time, and trigger export.
3. Open the export log directly or use the visible `前往查看` action.
4. Identify a row that was absent from the baseline and whose `来源` matches the tool and whose `生成时间` is at or after the run start.
5. When more than one row satisfies the evidence and no unique row identifier exists, stop and ask the user to choose.
6. If status is not `已完成`, wait 10 seconds, reload, and re-evaluate the same row. Stop after 300 seconds.
7. Continue only when the same row shows `已完成` and a visible download icon.

## 5. Download And Preserve The Result

1. Capture epoch time immediately before clicking the unique download icon.
2. Start the Chrome download wait when supported, click, and verify a download event or visible download response.
3. If Chrome shows `ERR_BLOCKED_BY_CLIENT` for the uniquely matched row's visible download link and no file appears, use `fetch-download --url <visible-url>`. This fallback accepts only configured SellerSprite HTTPS download hosts and supported data-file extensions.
4. Run `collect-download --since <epoch>`; add a filename pattern when visible evidence supports one.
5. Verify the copied file exists under `<workspace>/seller_sprite_exports/runs/<run>/output/`, is non-empty, and has a recorded SHA-256.
6. Never move, rename, or delete the original file in `~/Downloads`.

## 6. Learn The Workflow

After the first successful download, record:

- Stable tool ID, display name, and user-facing aliases.
- Entry URL and menu labels.
- Marketplace parameter and default.
- Parameter keys, labels, control hints, required flags, and successful defaults.
- Ordered semantic steps and expected export source.

Do not save DOM node IDs, full snapshots, credentials, cookies, tokens, or user data unrelated to the workflow. When page drift requires a repair, keep the old memory until the repaired workflow also downloads successfully.

Finalize tabs after browser work. Keep a tab only for a user handoff or when the user explicitly needs the live result page.
