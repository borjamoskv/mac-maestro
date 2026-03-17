# Security Policy

## Scope

MacMaestro interacts with the macOS Accessibility API, which has system-level
read/write access to every UI application running in the user's session.
This is an inherently privileged surface.

Security issues in scope include:

- **Safety Policy bypass**: Any mechanism that allows a caller to click or
  trigger destructive elements (e.g., Delete, Format) that would be blocked
  by the default `SafetyPolicy`.
- **Privilege escalation via AX**: Exploitation of AX permissions to interact
  with applications or data outside the caller's intended scope.
- **Remote Code Execution via untrusted input**: Any path where external or
  agent-provided content becomes executable via AX actions.
- **Sensitive data exposure**: Leakage of `AXValue` contents (passwords, tokens,
  etc.) into the `RunTrace` or logs without the user's knowledge.

Issues **not** in scope:

- UI visual glitches or cosmetic rendering bugs.
- Denial-of-service via crafted element trees (AX itself is not a hardened API).
- Issues in downstream applications being automated (report to those vendors).

## Accessibility & Automation Permissions Advisory

MacMaestro requires **Accessibility** permissions (`System Settings → Privacy & Security → Accessibility`).
Any program with this permission can read and potentially mutate **all UI** in the user's session,  
including password fields, secure inputs, and system dialogs.

**Treat Accessibility permission as equivalent to full user-land access.**

Only grant this permission to programs you trust. Review `SafetyPolicy` 
configuration before connecting MacMaestro to any autonomous agent.

## Reporting Vulnerabilities

Please **do not** file public GitHub Issues for security vulnerabilities.

Use **GitHub Private Security Advisories** (preferred):
[https://github.com/borjamoskv/mac-maestro/security/advisories/new](https://github.com/borjamoskv/mac-maestro/security/advisories/new)

Include:
- A description of the vulnerability.
- Reproduction steps.
- Potential impact.
- Any proposed fix or mitigation.

## Disclosure Policy

We commit to:
- Acknowledging receipt within **5 business days**.
- Providing an initial assessment within **15 business days**.
- Resolving confirmed issues within **90 days** where technically feasible.
- Coordinating a public disclosure timeline with the reporter.

We will credit reporters in the relevant release notes unless they request
anonymity.

## Hall of Fame

*Empty — be the first.*
