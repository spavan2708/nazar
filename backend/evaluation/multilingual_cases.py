"""Small hand-authored smoke/evaluation set, not a training or accuracy benchmark."""
CASES = [
    ("English scam", "scam", "Send me your OTP immediately."),
    ("Hindi scam", "scam", "आपका बैंक खाता बंद हो जाएगा। ओटीपी साझा करें।"),
    ("Tamil scam", "scam", "உங்கள் வங்கி கணக்கு முடக்கப்படும். OTP-ஐ பகிரவும்."),
    ("Hinglish KYC", "scam", "Your KYC expire ho gaya hai, abhi verify karo."),
    ("Hinglish OTP", "scam", "Aapka bank account block ho jayega. OTP share karo."),
    ("Tanglish scam", "scam", "Unga bank account block aagum, OTP share pannunga."),
    ("Mixed scam", "scam", "आपका खाता बंद हो जाएगा. Please share your OTP. உடனே அனுப்பவும்."),
    ("Hindi warning", "safety", "अपना ओटीपी किसी के साथ साझा न करें।"),
    ("Tamil warning", "safety", "உங்கள் OTP யாரிடமும் பகிர வேண்டாம்."),
    ("Hinglish warning", "safety", "Apna OTP share mat karo."),
    ("Tanglish warning", "safety", "Unga OTP yaarukkum share panna vendam."),
    ("Hindi benign", "benign", "नमस्ते, कल हम चाय पर मिलते हैं।"),
    ("Tamil benign", "benign", "வணக்கம், நாளை நாம் சந்திப்போம்."),
    ("English warning", "safety", "Never share your OTP with anyone."),
]
