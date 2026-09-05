"""Small concept vocabulary mapped to existing canonical signals, not scores."""
from schemas.signals import SignalCode

MULTILINGUAL_ACTIONS = (
    "साझा करें", "भेजें", "बताएं", "सत्यापित करें", "क्लिक करें",
    "பகிரவும்", "அனுப்பவும்", "சரிபார்க்கவும்", "நிறுவவும்",
    "share karo", "verify karo", "bhejo", "batao", "share pannunga",
    "verify pannunga", "anuppunga", "install pannunga",
)
MULTILINGUAL_SAFETY = (
    "साझा न करें", "शेयर न करें", "मत भेजें", "कभी न बताएं", "क्लिक न करें",
    "பகிர வேண்டாம்", "பகிராதீர்கள்", "அனுப்ப வேண்டாம்", "நிறுவ வேண்டாம்",
    "share mat karo", "mat bhejo", "share panna vendam", "anuppa vendam",
)
MULTILINGUAL_SIGNALS = {
    SignalCode.OTP_REQUEST: ("ओटीपी", "ஓடிபி"),
    SignalCode.CREDENTIAL_REQUEST: ("पासवर्ड", "பாஸ்வேர்டு", "கடவுச்சொல்"),
    SignalCode.IDENTITY_VERIFICATION: ("सत्यापित करें", "சரிபார்க்கவும்"),
    SignalCode.ACCOUNT_THREAT: (
        "खाता बंद हो जाएगा", "खाता ब्लॉक हो जाएगा", "account block ho jayega",
        "கணக்கு முடக்கப்படும்", "account block aagum",
    ),
    SignalCode.PAYMENT_REQUEST: ("पैसे भेजें", "பணம் அனுப்பவும்", "paise bhejo", "panam anuppunga"),
    SignalCode.REMOTE_ACCESS: ("स्क्रीन साझा करें", "திரையை பகிரவும்"),
    SignalCode.URGENCY: ("जल्दी", "तुरंत", "अभी", "உடனே", "உடனடியாக", "abhi", "udaney"),
}
