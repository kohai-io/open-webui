# Cookie Compliance Audit (Playwright)

A comprehensive cookie compliance auditing pipe for Open WebUI that uses Playwright for real browser rendering. Captures HTTP and JavaScript cookies, detects trackers, analyzes third-party requests, and generates ICO PECR compliance reports.

## Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **Real Browser Rendering** | Uses Playwright to execute JavaScript and capture dynamically-set cookies |
| **HTTP + JS Cookies** | Captures cookies set via HTTP headers AND `document.cookie` |
| **HAR Recording** | Records full network traffic for comprehensive analysis |
| **Tracker Detection** | Identifies tracking scripts using EasyPrivacy-style patterns |
| **Third-Party Analysis** | Lists all external domains contacted by the page |
| **Consent Detection** | Detects cookie consent banners and mechanisms |
| **Cookie Policy Detection** | Finds links to cookie/privacy policy pages |
| **Web Storage Analysis** | Reports localStorage and sessionStorage usage |
| **ICO PECR Compliance** | Scores compliance against UK ICO guidelines |

### Cookie Classification

Cookies are automatically classified into categories:

| Category | Examples | Requires Consent |
|----------|----------|------------------|
| **Essential** | Session IDs, CSRF tokens, auth cookies, CDN cookies | No |
| **Analytics** | Google Analytics (`_ga`, `_gid`), Hotjar, Mixpanel | Yes |
| **Marketing** | Facebook Pixel (`_fbp`), Google Ads (`IDE`), LinkedIn | Yes |
| **Functional** | Language preferences, theme settings | Yes |
| **Unknown** | Unclassified cookies | Yes (assumed) |

### Tracker Detection

Detects common tracking services:
- Google Analytics / Tag Manager / Ads
- Facebook/Meta Pixel
- Microsoft Clarity / Bing Ads
- Hotjar
- LinkedIn Insight
- Twitter/X Analytics
- Generic tracking pixels and beacons

## Requirements

### Playwright Browser Server

The pipe requires a Playwright browser server accessible via WebSocket. 

**Option 1: Docker (Recommended)**

```bash
docker run -d --name playwright-ws \
  -p 3000:3000 \
  mcr.microsoft.com/playwright:v1.58.0-noble \
  npx -y playwright@1.58.0 run-server --port 3000 --host 0.0.0.0
```

**Option 2: Use docker-compose.playwright.yaml**

```bash
docker-compose -f docker-compose.playwright.yaml up -d
```

### Python Dependencies

```
playwright==1.58.0
pydantic
```

> **Important:** The Playwright Python version must match the server version exactly.

## Configuration (Valves)

| Valve | Default | Description |
|-------|---------|-------------|
| `TIMEOUT_SECONDS` | 120 | Maximum time for entire audit |
| `PAGE_TIMEOUT_MS` | 30000 | Timeout for page load |
| `WAIT_AFTER_LOAD_MS` | 3000 | Wait time for JS cookies to be set |
| `PLAYWRIGHT_WS_URL` | `ws://10.100.1.144:3000` | WebSocket URL for Playwright server |
| `HEADLESS` | true | Run browser headless (local only) |
| `USER_AGENT` | Chrome 120 | Browser user agent string |
| `ENABLE_TRACKER_DETECTION` | true | Enable tracker pattern matching |
| `ENABLE_LLM_ANALYSIS` | false | Use LLM for policy analysis |
| `DEBUG_MODE` | false | Enable verbose logging |

## Usage

### Basic Usage

Send a message to the pipe with a URL:

```
Audit https://www.example.com for cookie compliance
```

Or simply:

```
https://www.bbc.co.uk
```

### Example Output

```markdown
# 🍪 Cookie Compliance Audit (Playwright)

**Target:** https://www.bbc.co.uk
**Standard:** ICO PECR Guidelines
**Engine:** Playwright (Real Browser)

---

## 📊 Summary

**Overall Compliance:** 🟠 Needs Improvement (50/100)

| Metric | Value |
|--------|-------|
| Total Cookies | 12 |
| Essential | 3 |
| Analytics | 5 |
| Marketing | 2 |
| Trackers Detected | 8 |
| Third-Party Hosts | 24 |
| Consent Mechanism | ✅ Yes |
| Cookie Policy | ✅ Found |

## ⚠️ Issues Found

- 🔴 **HIGH:** Found 9 non-essential cookies but no consent mechanism detected
- 🟠 **MEDIUM:** Found 8 tracking requests (Google Analytics, Facebook Pixel)

## 💡 Recommendations

- Implement a cookie consent mechanism before setting non-essential cookies
- Ensure all tracking scripts only load after user consent
```

## Architecture

### Based on EDPB Website Auditing Tool

Analysis patterns adapted from the [EDPB Website Auditing Tool](https://code.europa.eu/edpb/website-auditing-tool) (EUPL-1.2):

- **Cookie classification** from `cookie-card.ts`
- **HAR analysis** from `har-collector.ts`
- **Tracker detection** from `beacon-card.ts`
- **Traffic analysis** from `traffic-card.ts`

### How It Works

1. **Connect** to Playwright browser server via WebSocket
2. **Navigate** to target URL with HAR recording enabled
3. **Wait** for JavaScript execution (configurable delay)
4. **Collect** cookies from browser context
5. **Analyze** network requests for trackers
6. **Detect** consent mechanisms via DOM inspection
7. **Classify** cookies using pattern matching
8. **Score** ICO PECR compliance
9. **Generate** detailed markdown report

## Compliance Framework

### ICO PECR Requirements

The audit checks against UK ICO PECR (Privacy and Electronic Communications Regulations):

| Requirement | Description | ICO Reference |
|-------------|-------------|---------------|
| **Consent** | Users must consent before non-essential cookies | PECR Regulation 6 |
| **Information** | Clear explanation of cookies and purposes | PECR Regulation 6(2)(a) |
| **Control** | Users must be able to refuse non-essential cookies | PECR Regulation 6 |

### Scoring

| Score | Status | Criteria |
|-------|--------|----------|
| 100 | ✅ Compliant | No issues found |
| 70-99 | 🟡 Mostly Compliant | Low severity issues only |
| 40-69 | 🟠 Needs Improvement | Medium severity issues |
| 0-39 | 🔴 Non-Compliant | High severity issues |

## Troubleshooting

### Connection Errors

```
Error: WebSocket error: ws://host:3000/ 428 Precondition Required
Playwright version mismatch
```

**Solution:** Ensure Playwright Python version matches server version exactly.

### Timeout Errors

```
Audit timed out after 120 seconds
```

**Solution:** Increase `TIMEOUT_SECONDS` or `PAGE_TIMEOUT_MS` valves.

### Network Unreachable

```
Failed to navigate to URL
```

**Solution:** Verify the Playwright server can access the target URL (check firewall, DNS).

## Security

- **SSRF Protection:** Blocks auditing of localhost, private IPs, and internal hostnames
- **Deduplication:** Prevents multiple concurrent audits of the same URL
- **No Credentials:** Does not store or transmit any collected cookie values

## Related Files

- `functions_tools/functions/cookie-audit-playwright.py` - Main pipe implementation
- `functions_tools/functions/cookie-audit.py` - Simpler HTTP-only version (no Playwright)
- `backend/requirements.txt` - Python dependencies
- `docker-compose.playwright.yaml` - Playwright server configuration

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-04 | Initial release with Playwright integration |

## License

MIT License

Analysis patterns based on EDPB Website Auditing Tool (EUPL-1.2).

## References

- [ICO PECR Guidance](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guide-to-pecr/cookies-and-similar-technologies/)
- [EDPB Website Auditing Tool](https://code.europa.eu/edpb/website-auditing-tool)
- [Playwright Documentation](https://playwright.dev/)
