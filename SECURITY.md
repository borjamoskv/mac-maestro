# SECURITY.md — THREAT MEMBRANE

**Reality Level: C5-REAL**

## 01 · Operating Scope

MacMaestro interfaces with the macOS Accessibility API (AX), wielding system-level read/write clearance across all UI applications in the user session. This is a maximally privileged execution surface.

**In-Scope Vectors:**
- **Safety Policy bypass**: Mechanisms allowing execution of blocked elements (e.g., `Delete`) without explicit override.
- **Privilege escalation**: Exploitation of AX to leak or mutate data outside the caller's target bundle.
- **RCE via Input**: Execution of arbitrary code sourced from untrusted agent inputs via AX actions.
- **Trace Leakage**: Exposure of sensitive `AXValue` data (passwords, tokens) into `RunTrace` or NDJSON streams.

**Out-of-Scope Vectors:**
- UI cosmetic rendering bugs.
- Denial-of-Service via payload size (AX is not a hardened endpoint).
- Downstream vulnerabilities in automated target applications.

## 02 · AX Privilege Advisory

MacMaestro requires **Accessibility** clearance (`System Settings → Privacy & Security → Accessibility`).
A process with this clearance can inspect and mutate **ALL UI** — including secure inputs, password fields, and OS dialogs.

**[P0] Treat Accessibility clearance as root-level user-land access.**

Auditing the `SafetyPolicy` is mandatory before attaching MacMaestro to any sovereign agent or autonomous loop.

## 03 · Vulnerability Reporting

Do NOT file public issues for security vulnerabilities.

Use **GitHub Private Security Advisories**:
[https://github.com/borjamoskv/mac-maestro/security/advisories/new](https://github.com/borjamoskv/mac-maestro/security/advisories/new)

**Required Payload:**
- Vulnerability description.
- Reproduction topology.
- Blast radius / impact.
- Proposed patch or mitigation vector.

## 04 · Disclosure Protocol

- Receipt acknowledgement: **< 5 business days**.
- Assessment matrix: **< 15 business days**.
- Resolution window: **< 90 days** (technical feasibility permitting).
- Reporter credited in release notes (unless anonymity requested).

## 05 · Hall of Fame

*State: Empty. Become the first.*
