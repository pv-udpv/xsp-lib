# Security Policy

## Supported Versions

We release patches for security vulnerabilities. The following versions are currently being supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

**Note**: As we are currently in pre-release (0.x.x), we support only the latest release. Once we reach version 1.0.0, we will provide extended support for previous major versions.

## Reporting a Vulnerability

The xsp-lib team takes security bugs seriously. We appreciate your efforts to responsibly disclose your findings and will make every effort to acknowledge your contributions.

### How to Report a Security Vulnerability

**Please DO NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of the following methods:

1. **Preferred**: Use GitHub's Security Advisory feature
   - Navigate to the [Security tab](https://github.com/pv-udpv/xsp-lib/security/advisories)
   - Click "Report a vulnerability"
   - Fill in the details of the vulnerability

2. **Alternative**: Email the maintainers directly
   - Send an email with details to the repository maintainers
   - Include the word "SECURITY" in the subject line
   - You can find maintainer contact information in the [CONTRIBUTING.md](../CONTRIBUTING.md) file

### What to Include in Your Report

To help us better understand and resolve the issue, please include as much of the following information as possible:

- Type of vulnerability (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the vulnerability
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### Response Timeline

- **Initial Response**: We aim to acknowledge receipt of your vulnerability report within **48 hours** (2 business days)
- **Status Updates**: We will send you regular updates about our progress (at minimum, weekly)
- **Resolution**: We will notify you when the vulnerability has been fixed
- **Disclosure**: We follow coordinated disclosure and will work with you to determine an appropriate disclosure timeline

### What to Expect

1. **Acknowledgment**: We'll confirm receipt of your report
2. **Investigation**: Our team will investigate and validate the vulnerability
3. **Resolution**: We'll develop and test a fix
4. **Release**: We'll release a patched version
5. **Credit**: We'll publicly acknowledge your responsible disclosure (unless you prefer to remain anonymous)

## Security Best Practices for Contributors

### Dependency Security

- All dependencies are automatically scanned by **Dependabot**
- Weekly automated pull requests for dependency updates
- Security advisories are monitored continuously
- Review the [Dependabot configuration](.github/dependabot.yml) for details

### Code Security Scanning

- **CodeQL** analysis runs automatically on:
  - All pull requests to `main`
  - All pushes to `main`
  - Weekly scheduled scans
- Address any security findings before merging PRs
- View scan results in the [Security tab](https://github.com/pv-udpv/xsp-lib/security/code-scanning)

### Secret Scanning

GitHub secret scanning is enabled for this repository to prevent accidental exposure of credentials.

**If you accidentally commit a secret:**

1. **Immediately rotate the compromised credential** at its source (API provider, service, etc.)
2. Remove the secret from the repository history:
   ```bash
   # Use git-filter-repo or BFG Repo-Cleaner
   # See: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
   ```
3. Notify the maintainers through the vulnerability reporting process above
4. Document the incident (date, credential type, actions taken)

**Preventing secret commits:**

- Use environment variables for sensitive configuration
- Never hardcode API keys, tokens, passwords, or credentials
- Use `.gitignore` to exclude configuration files with secrets
- Enable push protection (recommended for all contributors):
  - Go to Settings → Code security and analysis → Push protection
  - Enable for your fork if you have admin access

### Secure Coding Guidelines

When contributing to xsp-lib, follow these security practices:

1. **Input Validation**: Always validate and sanitize external inputs (URLs, XML/JSON payloads, user data)
2. **Output Encoding**: Properly encode outputs to prevent injection attacks
3. **Error Handling**: Avoid exposing sensitive information in error messages
4. **Authentication & Authorization**: Follow the principle of least privilege
5. **Dependency Management**: Only add well-maintained, reputable dependencies
6. **Type Safety**: Leverage Python's type hints and our mypy configuration
7. **Async Security**: Be cautious with async/await and concurrent operations

### AdTech-Specific Security Considerations

Given xsp-lib's focus on AdTech protocols (VAST, OpenRTB, etc.), be particularly vigilant about:

- **XML External Entity (XXE) attacks** in VAST/VMAP/DAAST XML parsing
- **SSRF (Server-Side Request Forgery)** when fetching remote ad creative URLs
- **Macro injection** in VAST macro substitution
- **Bid request/response tampering** in OpenRTB implementations
- **Privacy compliance** (GDPR, CCPA) in user data handling
- **Ad fraud vectors** (click fraud, impression fraud, creative manipulation)

## Security Updates and Notifications

- Security advisories are published in the [GitHub Security Advisories](https://github.com/pv-udpv/xsp-lib/security/advisories) section
- Critical security updates will be released as patch versions (e.g., 0.1.1 → 0.1.2)
- Subscribe to repository releases to be notified of security patches
- Check the [CHANGELOG.md](../CHANGELOG.md) for security-related release notes

## Attribution

We believe in recognizing security researchers who help improve our project. With your permission, we will:

- Acknowledge your contribution in the security advisory
- Credit you in the release notes
- Add your name to a security researchers hall of fame (if we create one)

If you prefer to remain anonymous, please let us know and we will respect your wishes.

## Policy Updates

This security policy may be updated from time to time. Check the [commit history](.github/SECURITY.md) for changes. Material changes will be announced through repository discussions or release notes.

## Questions?

If you have questions about this security policy or xsp-lib's security practices, please open a discussion in the [Discussions](https://github.com/pv-udpv/xsp-lib/discussions) section or contact the maintainers.

---

**Last Updated**: December 2025  
**Version**: 1.0
