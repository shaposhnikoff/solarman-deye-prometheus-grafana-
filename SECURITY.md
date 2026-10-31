# Security policy

## Supported versions

Only the latest commit on the default branch is supported. Older tags and
forks receive no fixes.

## Reporting a vulnerability

Do not open a public issue for a security problem.

1. Use **Report a vulnerability** on the repository's *Security* tab
   (private vulnerability reporting).
2. If that button is unavailable, email the maintainer address listed in the
   repository profile.
3. Include: affected file or endpoint, version or commit, reproduction steps,
   impact, and any suggested fix.

Never include real credentials, tokens or personal data from a live system.
Replace them with obviously fake values.

## What to expect

| Stage | Target |
| --- | --- |
| Acknowledgement | 3 business days |
| Initial assessment | 10 business days |
| Fix or mitigation for critical/high | 30 days |
| Public disclosure | after a fix is released, by agreement |

## Scope

In scope: code and configuration in this repository.

Out of scope: vulnerabilities in third-party dependencies that are already
published upstream (report them upstream), missing hardening headers on
unrelated services, and findings that require physical access to the host.

## Safe harbour

Good-faith research that respects this policy will not lead to legal action.
Do not access data that is not yours, do not degrade service, and stop as soon
as you have confirmed the issue.
