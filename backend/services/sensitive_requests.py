"""Local request concepts, not a separate score or conversational inference model."""
import re
from schemas.signals import SignalCode

SENSITIVE_SAFETY = (
    'never give', 'never send', 'do not send', "don't send", 'do not tell',
    'do not need to share', "don't need to share", 'nobody needs your',
    'no one needs your',
)
PRESSURE = re.compile(r'\b(?:jaldi|jldi|expire|expires|really\s+quick|quickly|quick|right now|immediately|before\s+(?:it|the code)\s+expires?|only\s+(?:\d+|one|two|three|five)\s+minutes?\s+left|(?:otherwise|or)\s+.{0,35}\bwait\b.{0,20}\bdays?|not be able\b.{0,35}\bdays?)\b')
INTENT = re.compile(r"\b(?:(?:i|we)(?:'ll| will)?\s+(?:need|require)|(?:need|require)\s+(?:the|your|that|this|a)|(?:can|could|may)\s+i\s+(?:get|have)|tell|provide|give|send|share)\b")
QUESTION = re.compile(r"\b(?:what is|what's)\s+(?:your|the|that)\b")
OTP_OBJECT = re.compile(r'\b(?:otp|one[- ]time password|(?:verification|security|login|authentication)[- ](?:code|number)|(?:six|6)[- ]digit code|code\s+(?:(?:that|which)\s+)?(?:came|sent)\s+to\s+your\s+phone|code\s+(?:that\s+)?you\s+(?:received|receive))\b')
CREDENTIAL_OBJECT = re.compile(r'\b(?:password|pin|cvv|passcode)\b')


# Concepts are deliberately separate: object references do not imply requests.
TRANSFER = re.compile(r"(?<!\w)(?:bhej(?:o|na)?(?:\s+do)?|send\s+krdo|bata(?:o|na)?(?:\s+do)?|bta\s+do|bol\s+do|chahiye|anuppunga|pannunga|sollunga|வேண்டும்|அனுப்பவும்|பகிரவும்|சொல்லுங்கள்|भेज(?:ें|ो|ना|\s+दो)|बता(?:एं|ओ|ना)|चाहिए)(?!\w)")
CODE = re.compile(r"(?<!\w)(?:code|number|no|digits?|कोड|अंकों|சரிபார்ப்பு|எண்(?:ணை)?)(?!\w)")
AUTH = re.compile(r"(?<!\w)(?:verification|verifiction|security|authentication|login|otp|सत्यापन|சரிபார்ப்பு)(?!\w)")
SIX_DIGITS = re.compile(r"(?<!\w)(?:(?:6|six)[- ]+digits?|छह\s+अंकों|ஆறு\s+இலக்க)(?!\w)")
PHONE = re.compile(r"(?<!\w)(?:phone|mobile|handset|message|sms|फोन|मोबाइल|போனில்)(?!\w)")
ARRIVAL = re.compile(r"(?<!\w)(?:aya|aaya|aaye|aayi|received|arrived|came|sent|आया|आए|vandha|வந்த)(?!\w)")
RECIPIENT = re.compile(r"\b(?:mujhe|hume|bas|me|us)\b")
NEGATION = re.compile(
    r"(?<!\w)(?:mat\s+(?:bhej\w*|dena|do|bata\w*|share|send|karo)|"
    r"(?:share|send|bhej\w*|bata\w*)\s+(?:mat|nahi|nahin)|"
    r"(?:nahi|nahin)\s+(?:karna|maangte|mangte)|"
    r"(?:anuppa|panna)\s+vendam|मत\s+(?:भेजना|भेजो|देना|बताओ)|"
    r"(?:பகிர|அனுப்ப)\s+வேண்டாம்|பகிராதீர்கள்)(?!\w)")



def clauses(text: str) -> list[str]:
    return re.split(r"[,.!?।;\n]|\b(?:but|instead|lekin)\b", text)


def implicit_otp_object(text: str) -> bool:
    return bool(OTP_OBJECT.search(text) or SIX_DIGITS.search(text)
        or (CODE.search(text) and (AUTH.search(text) or (PHONE.search(text) and ARRIVAL.search(text))
            or re.search(r"\bexpires?\b", text))))


def transfer_intent(text: str) -> bool:
    return bool(INTENT.search(text) or QUESTION.search(text) or TRANSFER.search(text))


def recipient_exception(text: str) -> bool:
    """An omitted object may refer back; a new named object must stand alone."""
    if not RECIPIENT.search(text) or not transfer_intent(text):
        return False
    remainder = TRANSFER.sub(' ', text)
    for concept in (INTENT, RECIPIENT, AUTH):
        remainder = concept.sub(' ', remainder)
    remainder = re.sub(r"\b(?:ke|liye|woh|wahi|it|that|please|to|only|do|karo)\b", ' ', remainder)
    return not remainder.strip()


def safe_clause(text: str) -> bool:
    if re.search(r"\b(?:except|apart from|unless)\b.{0,45}\b(?:me|us|agent|caller)\b", text):
        return False
    return bool(NEGATION.search(text)) or any(phrase in text for phrase in SENSITIVE_SAFETY) or bool(re.search(
        r"\b(?:never|do not|don't)\b.{0,45}\b(?:share|give|send|tell|provide|ask)\b", text))


def benign_code_context(text: str) -> bool:
    return bool(re.search(r'\b(?:postal|postcode|zip|pincode)\b', text) or (
        re.search(r'\b(?:project|source|test|testing|sandbox)\b', text)
        and re.search(r'\b(?:code|environment|repository)\b', text)))


def request_signals(text: str) -> set[SignalCode]:
    codes = set()
    previous_warning = ''
    previous_end = 0
    for match in re.finditer(r'[^,.!?;।\n]+', text):
        clause = match.group()
        separator = text[previous_end:match.start()]
        previous_end = match.end()
        if safe_clause(clause):
            previous_warning = clause
            continue
        # Only a recipient-directed exception may inherit a negated object's
        # reference, and only across a comma, never an unrelated sentence.
        inherited = (previous_warning and recipient_exception(clause)
            and separator == ',' and (implicit_otp_object(previous_warning) or re.search(r"\bcode\b", previous_warning))
            and not benign_code_context(previous_warning))
        previous_warning = ''
        # Development/postal qualifiers disambiguate generic codes, but must not
        # erase an explicitly named OTP/password request in the same clause.
        explicit_secret = re.search(r'\b(?:otp|one[- ]time password|password|cvv|passcode)\b', clause)
        if benign_code_context(clause) and not explicit_secret:
            continue
        intent = transfer_intent(clause)
        if not intent:
            continue
        otp = implicit_otp_object(clause) or inherited
        expiring_code = re.search(r'\b(?:that|the|your) code\b', clause) and re.search(r'\bexpires?\b', clause)
        if otp or expiring_code:
            codes.add(SignalCode.OTP_REQUEST)
        # "one-time password" is an OTP, not two independent objects.
        credential_text = re.sub(r'one[- ]time password', '', clause)
        if CREDENTIAL_OBJECT.search(credential_text):
            codes.add(SignalCode.CREDENTIAL_REQUEST)
    return codes


def ambiguous_pressure(text: str) -> bool:
    """Anaphoric pressure can reinforce earlier evidence, never identify its object."""
    return any(not safe_clause(clause) and not benign_code_context(clause)
        and re.search(r'\b(?:need|require)\s+(?:it|that)\b', clause)
        and PRESSURE.search(clause)
        for clause in re.split(r'[.!?;।]', text))
