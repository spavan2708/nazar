"""Offline URL inspection only: no DNS, HTTP clients, browser or subprocesses."""
import ipaddress
import re
import unicodedata
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import idna

from schemas.url import URLAnalysis, URLIndicator
from services.risk_levels import risk_level_for_score

MAX_URL_LENGTH = 4096
MAX_URLS = 20
SHORTENERS = {"bit.ly", "t.co", "tinyurl.com", "goo.gl", "ow.ly", "is.gd", "rb.gy", "cutt.ly", "shorturl.at"}
CREDENTIAL_WORDS = {"login", "signin", "password", "credential", "credentials", "verify", "verification", "secure", "account", "bank", "kyc", "otp"}
CONFUSABLES = str.maketrans({"а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "і": "i", "ј": "j", "ӏ": "l", "ο": "o", "ρ": "p", "ι": "i"})
# Known explicit schemes are captured as a whole so rejected values cannot be
# reinterpreted as a safe-looking embedded domain. Bare domains are heuristic.
URL_PATTERN = re.compile(
    r"(?<![\w@.-])(?:[a-zA-Z][a-zA-Z0-9+.-]*://[^\s<>\"“”]+|"
    r"(?:javascript|data|file|ftp):[^\s<>\"“”]+|"
    r"//[^\s<>\"“”]+|"
    r"(?:(?:[0-9]{1,3}\.){3}[0-9]{1,3}|(?:[^\W_][\w-]*\.)+(?:xn--[a-zA-Z0-9-]+|[^\W\d_]{2,63}))(?::[0-9]+)?(?:[/\?#][^\s<>\"“”]*)?)(?![\w-]|\.[\w])",
    re.IGNORECASE,
)


class InvalidURL(ValueError):
    pass


def _invalid(message: str) -> InvalidURL:
    # Fixed messages never echo input, userinfo, query values or parser errors.
    return InvalidURL(message)


def _scripts(label: str) -> set[str]:
    scripts = set()
    for char in label:
        if not char.isalpha():
            continue
        script = next((name for name in ("LATIN", "CYRILLIC", "GREEK", "DEVANAGARI", "TAMIL", "ARABIC", "HEBREW", "HIRAGANA", "KATAKANA", "CJK") if name in unicodedata.name(char, "")), None)
        if script:
            scripts.add(script)
    return scripts


def analyze_url(value: str) -> URLAnalysis:
    raw = value.strip()
    if not raw or len(raw) > MAX_URL_LENGTH:
        raise _invalid("Enter a URL of at most 4096 characters.")
    if any(char.isspace() or unicodedata.category(char).startswith("C") for char in raw) or "\\" in raw:
        raise _invalid("The URL contains invalid whitespace or control characters.")
    explicit_scheme = re.match(r"^([a-zA-Z][a-zA-Z0-9+.-]*):", raw)
    # A host:port entry is not a scheme, but unsupported schemes stay rejected.
    host_port = re.match(r"^[^/:]+\.[^/:]+:[0-9]+(?:[/?#]|$)", raw)
    if explicit_scheme and not host_port and explicit_scheme[1].lower() not in {"http", "https"}:
        raise _invalid("Only HTTP and HTTPS URLs are supported.")
    assumed = not explicit_scheme or bool(host_port)
    candidate = ("https:" + raw if raw.startswith("//") else "https://" + raw) if assumed else raw
    try:
        parsed = urlsplit(candidate)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc or not parsed.hostname:
            raise _invalid("Enter a valid HTTP or HTTPS URL with a hostname.")
        host = parsed.hostname.rstrip(".")
        port = parsed.port
        if port is not None and not 1 <= port <= 65535:
            raise _invalid("The URL port is invalid.")
        if re.search(r"%(?![0-9a-fA-F]{2})", parsed.path + parsed.query + parsed.fragment):
            raise _invalid("The URL contains invalid percent encoding.")
        ip = None
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            if re.fullmatch(r"[0-9.]+", host) or ":" in host:
                raise _invalid("Use a standard IPv4 or bracketed IPv6 address.")
        if ip:
            ascii_host = unicode_host = ip.compressed
        else:
            ascii_host = idna.encode(host, uts46=True, std3_rules=True).decode("ascii").lower()
            unicode_host = idna.decode(ascii_host)
            if "." not in ascii_host or len(ascii_host) > 253:
                raise _invalid("Enter a fully qualified domain name or IP address.")
        scheme = parsed.scheme.lower()
    except (ValueError, UnicodeError, idna.IDNAError) as error:
        if isinstance(error, InvalidURL):
            raise
        raise _invalid("The URL is malformed. Check its hostname and port.") from None

    indicators = []
    groups: dict[str, int] = {}

    def add(code: str, description: str, family: str, weight: int):
        indicators.append(URLIndicator(code=code, description=description))
        # Correlated IDN or wording indicators count only once per family.
        groups[family] = max(groups.get(family, 0), weight)

    if scheme == "http":
        add("NON_HTTPS", "Uses HTTP rather than encrypted HTTPS. This alone does not establish fraud.", "transport", 10)
    if ip:
        add("IP_ADDRESS_HOST", "Uses an IP address instead of a named domain; verify who operates it.", "host_address", 20)
    if parsed.username is not None or parsed.password is not None:
        add("EMBEDDED_USERINFO", "Contains text or credentials before the actual host, which can disguise the destination. These were removed from the displayed normalized URL.", "userinfo", 25)
    if port is not None and port != (443 if scheme == "https" else 80):
        add("UNUSUAL_PORT", "Uses a port other than the usual one for this scheme; legitimate services can do this too.", "port", 10)
    if not ip and any(label.startswith("xn--") for label in ascii_host.split(".")):
        add("IDN_HOST", "Uses an internationalized domain name. IDNs are legitimate, but similar-looking letters deserve a closer check.", "idn", 10)
    if not ip and any(len(_scripts(label)) > 1 for label in unicode_host.split(".")):
        add("MIXED_SCRIPT_HOST", "Combines writing systems within a hostname label, which can create lookalikes.", "idn", 25)
    if any(ord(char) in CONFUSABLES for char in unicode_host) and unicode_host.translate(CONFUSABLES) != unicode_host:
        add("LOOKALIKE_CHARACTERS", "Contains some non-Latin letters resembling Latin letters. This is a limited heuristic, not proof of impersonation.", "idn", 25)
    if not ip and len(ascii_host.split(".")) >= 5:
        add("DEEP_HOSTNAME", "Has many hostname labels, which may obscure the destination. Ownership was not checked.", "host_depth", 15)
    words = set(re.findall(r"[a-z]+", unquote(unicode_host + "/" + parsed.path).lower()))
    if words & CREDENTIAL_WORDS:
        add("LOGIN_WORDING", "Uses account, login or verification wording in the host or path; this is also common on legitimate sites.", "wording", 10)
    if len(words & CREDENTIAL_WORDS) >= 3:
        add("CREDENTIAL_HEAVY_URL", "Combines several account or credential-related terms in the host/path. Check the real organization independently.", "wording", 25)
    if ascii_host in SHORTENERS or any(ascii_host.endswith("." + domain) for domain in SHORTENERS):
        add("URL_SHORTENER", "Uses a known shortening domain. The final destination is hidden and was not expanded.", "shortener", 15)
    if len(parsed.path) > 200:
        add("LONG_PATH", "Has a long path that is harder to inspect; long paths can be legitimate.", "complexity", 5)
    query_count = sum(bool(part) for part in parsed.query.split("&"))
    if query_count > 8 or len(parsed.query) > 512:
        add("COMPLEX_QUERY", "Contains many or lengthy query parameters. Parameter values were not interpreted or logged.", "complexity", 5)
    score = min(sum(groups.values()), 100)
    authority = f"[{ascii_host}]" if ip and ip.version == 6 else ascii_host
    if port is not None and port != (443 if scheme == "https" else 80):
        authority += f":{port}"
    normalized = urlunsplit((scheme, authority,
        quote(parsed.path or "/", safe="/%:@!$&'()*+,;=-._~"),
        quote(parsed.query, safe="%:@!$&'()*+,;=/?-._~"),
        quote(parsed.fragment, safe="%:@!$&'()*+,;=/?-._~")))
    explanation = (
        "Several structural indicators deserve verification; they do not prove phishing."
        if len(groups) >= 2 else
        "One structural indicator was found; it is not enough to conclude this link is malicious."
        if groups else
        "No listed structural concerns were found. This does not establish that the destination is safe."
    )
    explanation += " No page, redirect, DNS record or reputation service was consulted."
    if assumed:
        explanation += " HTTPS was assumed because no scheme was supplied; support for HTTPS was not verified."
    return URLAnalysis(normalized_url=normalized, hostname=ascii_host, unicode_hostname=unicode_host,
        domain=ascii_host, scheme=scheme, scheme_assumed=assumed, port=port,
        path_length=len(parsed.path), query_parameter_count=query_count, query_length=len(parsed.query),
        indicators=indicators, structural_risk_score=score, risk_level=risk_level_for_score(score),
        explanation=explanation, evidence_groups=len(groups))


def extract_url_analysis(text: str) -> tuple[list[URLAnalysis], bool]:
    results = []
    seen = set()
    for match in URL_PATTERN.finditer(text):
        candidate = match[0].rstrip(".,;!。।，；！")
        # Remove wrapping punctuation, while retaining balanced URL parentheses.
        for closing, opening in ((")", "("), ("]", "["), ("}", "{")):
            while candidate.endswith(closing) and candidate.count(closing) > candidate.count(opening):
                candidate = candidate[:-1]
        if match.start() > 0 and text[match.start() - 1] == "'":
            candidate = candidate.rstrip("'")
        if candidate in seen:
            continue
        seen.add(candidate)
        if len(results) >= MAX_URLS:
            return results, True
        try:
            result = analyze_url(candidate)
        except InvalidURL as error:
            result = URLAnalysis(valid=False, explanation=str(error))
        results.append(result)
    return results, False
