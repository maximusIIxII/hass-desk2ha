# Security Policy

## Supported Versions

| Version | Status |
|---------|--------|
| Latest  | Security fixes |
| < 0.3.0 | No support |

## Reporting a Vulnerability

**Do not** open a public issue for security vulnerabilities.

Use GitHub's private vulnerability reporting:
1. Go to the **Security** tab
2. Click **"Report a vulnerability"**
3. Include: affected version(s), description, impact, steps to reproduce

We triage within 7 days and provide status updates every 14 days.

## Scope

- Config Flow credential handling (SSH/WinRM passwords)
- Authentication bypass
- Unauthorized agent control via services
- Token exposure in diagnostics
