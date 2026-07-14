# Config Schema

Workspace-first path:

```text
./config.yaml
```

If `./config.yaml` is missing, the skill auto-creates it in the current working directory.

Legacy template source:

```text
/Users/apple/Documents/Listing优化建议/amazon_chrome_listing_monitor/config.yaml
```

Required:

- `excel_path`: absolute path to the ASIN Excel file.
- `output.report_dir`: Markdown and Excel report directory.
- `output.snapshot_dir`: run packages and JSON snapshot directory.
- `output.screenshot_dir`: screenshot directory for abnormal pages.

Runtime defaults:

- `browser`: must be `chrome`.
- `max_parallel_pages`: keep `1` unless the user accepts higher Amazon access-block risk.
- `min_delay_ms` / `max_delay_ms`: delay between Amazon pages.
- `retry_on_abnormal`: retry count for abnormal first reads.
- `screenshot_on_abnormal`: save screenshots for abnormal pages.
- `screenshot_on_success`: default false.

Delivery:

- `delivery.email.enabled`: send email only when true.
- `delivery.email.password`: direct SMTP password, allowed but not preferred.
- `delivery.email.password_env`: preferred SMTP password environment variable name. For backward compatibility, a non-env-name literal value is also accepted.
- `delivery.feishu.enabled`: send Feishu only when true.
- `delivery.feishu.webhook_url`: direct Feishu webhook URL, allowed but not preferred.
- `delivery.feishu.webhook_url_env`: preferred webhook environment variable name. For backward compatibility, a literal `https://...` value is also accepted.
- `delivery.feishu.secret`: direct signing secret, allowed but not preferred.
- `delivery.feishu.secret_env`: optional signing secret environment variable name. For backward compatibility, a non-env-name literal value is also accepted.

Send behavior:

- Assembly sends notifications automatically when email or Feishu is enabled in the active config.
- Use `--no-send` only for manual validation.
- Message bodies must include a Markdown-style table with remark, score, optimization flag, priority, issue summary, core suggestion, ASIN, country, page status, and URL.
- Email must attach the generated Excel report file.

Never print secret values in user-facing responses or logs.
