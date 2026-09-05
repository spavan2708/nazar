"""Reproduce fixed, manually authored synthetic records; no random paraphrasing.
Blocks are authored independently by split. Never move eval rows into training.
Format: category|text. No external/private messages are used.
"""
import json
from pathlib import Path

TRAIN = {
('English', 'scam'): '''otp|The approval window is closing; read the digits from your bank's SMS to this caller.
implicit_sensitive|I'll need the security number before the session expires to release your balance.
euphemistic|Pass along the little number that popped up on the handset while we are talking.
credential|To stop a disputed transaction, reply with your card's CVV and online password.
remote_access|Run the desktop helper and grant our operator full control of your laptop.
bank_impersonation|Bank audit desk here: disclose your customer login so we can cancel the freeze.
government_impersonation|Cyber police require a security deposit to clear the warrant attached to your identity.
payment|Your refund is queued; approve the collect-money request to receive it.
account_threat|We will deactivate your wallet tonight unless you submit your secret recovery phrase.
investment|Our insider commodity pool pays a fixed profit every hour with no possibility of loss.
link|Activate your salary account at http://salary-unlock.example/login using your banking password.
otp|Forward the bank text to my personal number; I will finish the loan approval for you.
credential|Upload a photo of both sides of your debit card, including the security digits.
remote_access|Let me see your banking screen through the remote-control utility while you sign in.
bank_impersonation|I represent branch security; move your savings into this temporary protected account.
government_impersonation|The revenue office will seize your property unless you settle through gift-card vouchers.
payment|Pay the interview clearance fee to my wallet before I send your appointment letter.
account_threat|Your number will be disconnected unless you reveal the SIM replacement verification token.
investment|Put your pension into our private crypto pool; losses are impossible under our guarantee.
link|Use this shortened verification address to enter your card details before your parcel is returned.
otp|Do not hang up; dictate the new sign-in code even if the SMS says not to disclose it.
implicit_sensitive|May I have the login code from your messages? I need it to unlock your payout.
remote_access|Download the support tool, accept the connection request, and leave your phone unlocked.
credential|Send your email recovery codes to this chat so the help desk can reset your account.
payment|Congratulations on the grant; transfer the release charge before we disburse your award.
account_threat|This final notice cancels your benefits unless you submit your banking credentials here.
investment|A celebrity broker guarantees triple your deposit; send funds now to reserve a place.
link|Your toll account is restricted; scan this payment QR and type your card PIN on the page.
ocr|KYC l0ck pending: sh4re the bank 0TP with our officer to restore withdrawals.
transcription|uh yes just tell me those login digits and I'll take care of the rest on my side.
implicit_sensitive|I require the authentication code from your mobile to authorize your compensation.
euphemistic|Read out the six figures beneath the sign-in notification, one at a time.
remote_access|Start screen sharing with our refund executive and approve the device access prompt.
payment|To retrieve money lost to scammers, first pay our recovery team an investigation bond.
government_impersonation|Customs officers found illegal goods in your parcel; buy vouchers to close the case.
credential|We need your UPI PIN in this conversation to reverse an accidental debit.
bank_impersonation|This is the bank migration team; provide your passcode to avoid a service interruption.
investment|Join our secret trading channel and borrow money today for a guaranteed weekly payout.
link|The scholarship expires this evening; verify through http://student-funds.example/card-check.
otp|Share the one-time password with the agent, not the website, to complete the chargeback.''',
('English', 'safe'): '''safety|Keep verification codes private even when the caller claims to work at your branch.
educational|An authentication token is a temporary proof used by a login system.
hard_negative|The test OTP is stored in our mock fixture, never in the production database.
hard_negative|Send me the project verification code from the integration-test repository.
ordinary|I need lunch before the afternoon workshop starts.
hard_negative|My coupon expires today; I will use it at the supermarket.
ordinary|We need to finish quickly because the library closes at six.
safety|Never install screen-control software at the request of a caller you cannot verify.
educational|A six-digit postal identifier is not the same as a secret banking PIN.
ordinary|Please forward the agenda and reserve two chairs for the meeting.
safety|Nobody needs your sign-in code to issue a refund.
hard_negative|Our local emulator generates fake security numbers for automated tests.
educational|Banks may send warnings about phishing; these warnings do not request your password.
ordinary|The school fee receipt is available in the usual parent portal.
safety|Do not accept a payment collection request when you expect to receive money.
hard_negative|What is the postal PIN code for the address on the parcel label?
ordinary|The dentist moved my appointment to Thursday morning.
educational|Remote support tools can be useful, but access should be approved through trusted support channels.
safety|Anyone promising risk-free daily trading profits may be trying to deceive you.
hard_negative|The login-code example in the textbook uses invented digits, not an actual account.
safety|If an officer asks for gift cards to settle a case, contact the agency independently.
ordinary|Could you share the recipe for the soup we had yesterday?
educational|Two-factor authentication adds a second check beyond a password.
hard_negative|We require the source code of the verification module for peer review.
safety|Your bank will not require your CVV or password over a phone call.
ordinary|The community chess tournament begins after the lunch break.
hard_negative|The printed discount code stops working at midnight; there is no account involved.
educational|An SMS can be spoofed, so the displayed sender name is not sufficient proof.
safety|Disconnect if a stranger tells you to move savings into a so-called safe account.
ordinary|Would you collect the repaired bicycle on your way home?
ocr|S4fety notice: d0 not give callers your banking c0des.
transcription|um no don't read those numbers to me, just enter them yourself in your usual bank app.
hard_negative|The password field in this design mockup is placeholder text.
educational|Fraud researchers study demands for advance fees and remote device access.
safety|Decline requests to show your banking screen to strangers.
ordinary|The train tickets are booked; please bring your own water bottle.
hard_negative|I need that project code quickly so I can build the test application.
safety|Never send an image of your debit card to an unsolicited chat contact.
ordinary|Our neighborhood clean-up is postponed because of heavy rain.
educational|A government impersonation scam falsely uses an official title to demand payment.''',
('Hindi', 'scam'): '''otp|लोन जारी करने के लिए मोबाइल पर आया ओटीपी मुझे पढ़कर बताइए।
credential|आपके कार्ड का सीवीवी और पासवर्ड चाहिए, तभी गलत कटौती रोक पाएंगे।
remote_access|यह सहायता ऐप चलाइए और हमारे कर्मचारी को फोन का नियंत्रण दीजिए।
bank_impersonation|मैं बैंक निरीक्षण विभाग से हूँ, अपनी रकम हमारे सुरक्षित खाते में डालिए।
government_impersonation|आपके नाम गिरफ्तारी आदेश है, जुर्माना इस निजी वॉलेट में भरिए।
payment|नौकरी पक्की है लेकिन नियुक्ति पत्र से पहले प्रशिक्षण शुल्क भेजना होगा।
account_threat|आज पहचान नहीं बताई तो खाता बंद होगा, लॉगिन जानकारी यहाँ भेजें।
investment|इस योजना में पैसा कभी नहीं डूबता, हर दिन तय मुनाफा मिलेगा।
link|पेंशन रोक दी गई है, इस छोटे लिंक पर कार्ड विवरण भरकर चालू करें।
implicit_sensitive|मुझे आपके फोन का सत्यापन नंबर चाहिए ताकि भुगतान जारी कर सकूँ।''',
('Hindi', 'safe'): '''safety|बैंक का नाम लेने वाले किसी अनजान व्यक्ति को ओटीपी न बताएं।
educational|ओटीपी एक सीमित समय के लिए मान्य रहने वाला पासवर्ड होता है।
hard_negative|परीक्षण वातावरण में इस्तेमाल किया गया कोड नकली है।
ordinary|कल पुस्तकालय से मेरी किताब लेते आना।
safety|रिफंड पाने के लिए किसी को अपना पिन बताने की जरूरत नहीं है।
hard_negative|कूरियर के पते में डाक पिन कोड ठीक लिखना है।
educational|स्क्रीन साझा करने से दूसरा व्यक्ति निजी जानकारी देख सकता है।
ordinary|कक्षा का समय बदल गया है, अब सुबह दस बजे आएं।
safety|गारंटीड मुनाफे का वादा सुनकर पैसे मत भेजिए।
ordinary|आज सब्जी बाजार से आलू और टमाटर ले आओ।''',
('Tamil', 'scam'): '''otp|கடன் தொகையை விடுவிக்க உங்கள் கைபேசிக்கு வந்த ஒருமுறை கடவுச்சொல்லை என்னிடம் கூறுங்கள்.
credential|தவறான பணப் பிடித்தலை நிறுத்த உங்கள் அட்டை ரகசிய எண்ணை இந்த உரையாடலில் அனுப்புங்கள்.
remote_access|இந்த உதவி செயலியை நிறுவி எங்கள் பணியாளருக்கு உங்கள் கைபேசியைக் கட்டுப்படுத்த அனுமதி கொடுங்கள்.
bank_impersonation|வங்கி பாதுகாப்புப் பிரிவிலிருந்து பேசுகிறேன், சேமிப்பை இந்த பாதுகாப்பு கணக்குக்கு மாற்றுங்கள்.
government_impersonation|உங்கள் மீது வழக்கு உள்ளது, கைது தவிர்க்க இந்த தனிப்பட்ட கணக்கில் அபராதம் செலுத்துங்கள்.
payment|வேலை உறுதி செய்ய முதலில் பதிவு கட்டணத்தை என் வாலட்டுக்கு அனுப்ப வேண்டும்.
account_threat|இன்றே உள்நுழைவு விவரங்களை தராவிட்டால் உங்கள் கணக்கு நிரந்தரமாக நிறுத்தப்படும்.
investment|இந்த முதலீட்டில் நஷ்டமே இல்லை, தினமும் உறுதியான லாபம் கிடைக்கும்.
link|ஓய்வூதியம் பெற இந்த இணைப்பில் வங்கி அட்டை விவரங்களை நிரப்புங்கள்.
implicit_sensitive|பணத்தை அனுப்ப உங்கள் தொலைபேசியில் வந்த சரிபார்ப்பு எண் எனக்குத் தேவை.''',
('Tamil', 'safe'): '''safety|வங்கி ஊழியர் என்று சொன்னாலும் அறிமுகமற்றவரிடம் ரகசிய எண்ணைக் கூறாதீர்கள்.
educational|ஒருமுறை கடவுச்சொல் சிறிது நேரம் மட்டுமே பயன்படும் பாதுகாப்பு முறை.
hard_negative|சோதனை நிரலில் உள்ள சரிபார்ப்பு எண் உண்மையான வாடிக்கையாளருடையது அல்ல.
ordinary|நாளை பள்ளியில் பெற்றோர் கூட்டம் நடைபெறுகிறது.
safety|பணம் திரும்பப் பெற உங்கள் பின் எண்ணை யாருக்கும் சொல்ல வேண்டியதில்லை.
hard_negative|அஞ்சல் முகவரியின் பின் குறியீட்டை தெளிவாக எழுதுங்கள்.
educational|திரையைப் பகிரும்போது தனிப்பட்ட தகவல்கள் பிறருக்கு தெரியலாம்.
ordinary|மாலை மழை வரும் என்பதால் குடை எடுத்துச் செல்லுங்கள்.
safety|உறுதியான லாபம் என்று சொல்லும் அந்நியருக்கு பணம் அனுப்ப வேண்டாம்.
ordinary|நூலகத்தில் எடுத்த புத்தகத்தை அடுத்த வாரம் திருப்பித் தரலாம்.''',
('Hinglish', 'scam'): '''otp|Loan clear karne ke liye mobile wala OTP mujhe bol do.
remote_access|Support software chalao aur technician ko poora phone access de do.
payment|Interview pass ho gaya, offer letter ke liye pehle security fee bhejo.
credential|Refund process karne ko tumhara banking password is chat mein chahiye.
investment|Hamare trading pool mein nuksan nahi hota, salary ka paisa abhi lagao.''',
('Hinglish', 'safe'): '''safety|Kisi caller ko login wala number mat batana, chahe bank ka naam le.
hard_negative|Test fixture ka verification code dummy hai, customer ka nahi.
ordinary|Kal office se aate hue doodh le aana.
educational|OTP ek temporary login secret hota hai, address ka PIN nahi.
safety|Screen control ki request aaye toh pehle apne IT desk se confirm karo.''',
('Tanglish', 'scam'): '''otp|Loan release panna phone la vandha OTP enakku sollunga.
remote_access|Support app open pannitu technician ku device control kudunga.
payment|Job confirm aachu, appointment letter venumna registration kaasu anuppunga.
credential|Refund poda unga bank password inga type pannunga.
investment|Enga trading scheme la loss varadhu, salary motham invest pannunga.''',
('Tanglish', 'safe'): '''safety|Unknown caller kitta bank code solla vendam.
hard_negative|Indha verification number test data mattum, real account illa.
ordinary|Naalaikku bus late varum, konjam seekiram kelambunga.
educational|OTP temporary secret, postal code oda confuse panna koodadhu.
safety|Screen share panna sollra aalai official help desk moolama verify pannunga.''',
('Mixed', 'scam'): '''otp|Verification pending है, phone का login token इस chat में भेजो.
remote_access|உங்கள் refund ready, allow remote control so our officer can finish it.
government_impersonation|Police enquiry चल रही है, settle now by paying the private UPI account.
account_threat|Account முடக்கப்படும், send the secret number before the deadline.
link|KYC புதுப்பிக்க http://kyc-desk.example/secret पर password डालो.''',
('Mixed', 'safe'): '''safety|OTP யாருக்கும் சொல்லாதீர்கள், even if they claim to be from the bank.
hard_negative|यह verification code sandbox का है, not a live customer credential.
ordinary|Meeting முடிந்ததும் வீட்டுக்கு போகலாம், no need to rush.
educational|Remote access का मतलब device control है; use it only with trusted support.
safety|Refund பெற PIN வேண்டாம், stop if a caller demands one.''',
}

# Independently authored evaluation situations, not expansions of training rows.
EVAL = {
('English', 'scam'): '''implicit_sensitive|Could I have the authentication digits from the notification to complete your insurance payout?
euphemistic|What are the numbers below the padlock symbol in the message you just got?
otp|The fraud reversal cannot proceed until you dictate your current one-time login secret.
credential|For identity matching, reply with the passphrase you normally use to enter your mailbox.
remote_access|Accept my connection invite in the assistance program so I can operate your tablet during verification.
bank_impersonation|Branch compliance requires a transfer of your entire balance to the auditor's holding wallet.
government_impersonation|A court investigator instructs you to purchase prepaid vouchers to suspend prosecution.
payment|The buyer overpaid; pay a release deposit through this collect request before the sale proceeds arrive.
account_threat|Your insurance profile will be deleted unless you reveal the recovery keys to this chat operator.
investment|A private arbitrage robot promises a fixed twenty percent every month and guarantees your principal.
link|A delivery surcharge must be paid at http://parcel-clearance.example/secure-card to prevent disposal.
ocr|Acc0unt h0ld: tell the caller y0ur l0gin c0de to resume service.
transcription|yeah so the thing is I need those digits from the bank message, say them slowly please.
implicit_sensitive|We require your security code here in the conversation before extending the login session.
euphemistic|Read the fresh six numerals displayed under the sign-in alert to the person on this call.
remote_access|Turn on remote management and approve our assistant's permission to control the computer.
payment|A missing relative's emergency release requires an immediate transfer to my personal account.
credential|Send the complete list of backup authentication keys so we can migrate your email securely.
government_impersonation|The municipal tax squad will seal your shop unless you remit the penalty to this private QR.
link|Your reward points vanish tonight; enter your banking secrets at http://points-claim.example/signin.''',
('English', 'safe'): '''safety|A caller asking you to read a banking notification is a reason to end the conversation.
educational|A passphrase can contain several words instead of a short sequence of letters.
hard_negative|Please send the mock verification snippet used in the staging server unit tests.
ordinary|The picnic has moved indoors because the park is flooded.
safety|You can receive a refund without approving anyone's request to take control of your tablet.
hard_negative|The postal sorting code printed on this envelope needs to be corrected.
educational|A login notification may contain a one-use secret which should stay with its recipient.
ordinary|Could you water the balcony plants while I am visiting my family?
safety|Do not pay a supposed investigator using prepaid shopping vouchers.
hard_negative|My museum discount voucher becomes invalid tomorrow, so I booked a visit today.
ocr|D0n't read bank digits to strangers, keep y0ur login private.
transcription|no no I don't want your password, contact the branch yourself and ask them.
hard_negative|We need the verification number in the fake data generator documented before release.
educational|Investment losses remain possible even when an advertisement claims otherwise.
ordinary|The orchestra rehearsal will run thirty minutes longer this evening.
safety|An online buyer should not need your backup login keys to pay you.
hard_negative|The example card security code in the tutorial is invented for demonstration.
educational|A help desk can explain device permissions without receiving your personal login token.
ordinary|Please send me the photograph of the handwritten recipe after dinner.
safety|Verify court notices through public office contact details instead of paying a caller.''',
('Hindi', 'scam'): '''implicit_sensitive|बीमा का पैसा भेजने से पहले मुझे संदेश में आया सुरक्षा अंक बताना जरूरी है।
remote_access|सत्यापन के दौरान हमारा सहायक आपका टैबलेट चलाएगा, कनेक्शन की अनुमति दें।
government_impersonation|नगर कर अधिकारी बोल रहा हूँ, दुकान सील होने से बचाने को निजी खाते में रकम डालें।
investment|हमारा रोबोट हर महीने निश्चित लाभ देता है, पूरी जमा पूंजी भेज दीजिए।
link|इनाम लेने के लिए इस वेबसाइट पर ईमेल का गुप्त पासवर्ड भर दें।''',
('Hindi', 'safe'): '''safety|किसी फोन करने वाले को संदेश के सुरक्षा अंक पढ़कर सुनाना ठीक नहीं है।
hard_negative|डेमो सर्वर का सत्यापन नंबर केवल प्रशिक्षण सामग्री के लिए है।
ordinary|इस रविवार परिवार के साथ संग्रहालय देखने जाएंगे।
educational|विज्ञापन में भरोसा दिलाने पर भी निवेश में नुकसान हो सकता है।
safety|पुलिस बताकर निजी खाते में पैसे मांगने वाले की पहचान स्वतंत्र रूप से जांचें।''',
('Tamil', 'scam'): '''implicit_sensitive|காப்பீட்டு பணம் வருவதற்கு முன் குறுஞ்செய்தியில் உள்ள பாதுகாப்பு இலக்கங்களை எனக்குப் படியுங்கள்.
remote_access|சரிபார்க்க எங்கள் உதவியாளர் உங்கள் கணினியை இயக்க வேண்டும், இணைப்பை ஏற்றுக்கொள்ளுங்கள்.
government_impersonation|நகராட்சி அதிகாரி பேசுகிறேன், கடையை மூடாமல் இருக்க இந்த தனி கணக்கில் பணம் செலுத்துங்கள்.
investment|எங்கள் தானியங்கி வர்த்தகம் மாதந்தோறும் உறுதியான வருமானம் தரும், முழு சேமிப்பையும் அனுப்புங்கள்.
link|பரிசுத் தொகையைப் பெற இந்த இணையதளத்தில் மின்னஞ்சல் ரகசிய கடவுச்சொல்லை இடுங்கள்.''',
('Tamil', 'safe'): '''safety|தொலைபேசியில் பேசும் அந்நியருக்கு குறுஞ்செய்தியின் பாதுகாப்பு இலக்கங்களைப் படிக்காதீர்கள்.
hard_negative|பயிற்சி சேவையகத்தில் உள்ள குறியீடு உண்மையான உள்நுழைவுக்கானது இல்லை.
ordinary|இந்த ஞாயிறு குடும்பத்துடன் அருங்காட்சியகத்திற்குச் செல்கிறோம்.
educational|விளம்பரம் உறுதி அளித்தாலும் முதலீட்டில் இழப்பு ஏற்படலாம்.
safety|அதிகாரி என்று கூறி தனிப்பட்ட கணக்கில் பணம் கேட்பவரை தனியாக சரிபாருங்கள்.''',
('Hinglish', 'scam'): '''implicit_sensitive|Insurance payout ruk gaya, notification ke security digits mujhe padh kar suna do.
remote_access|Tablet verify karna hai, meri assistance connection request accept kar lo.
account_threat|Tumhara email aaj delete hoga, backup keys operator ko bhej do.
payment|Buyer ka payment atka hai, collect request se release deposit pay karo.
investment|Private robot har mahine fixed profit dega, savings idhar transfer karo.''',
('Hinglish', 'safe'): '''safety|Bank notification ke digits caller ko padhne ki zaroorat nahi hoti.
hard_negative|Staging server ke fake login tokens ki documentation bhej dena.
ordinary|Sunday ko family ke saath museum chalna hai.
educational|Guaranteed bolne se investment ka risk khatam nahi hota.
safety|Court ka naam lekar voucher maange toh public office se khud jaanch karo.''',
('Tanglish', 'scam'): '''implicit_sensitive|Insurance amount vara notification security digits enakku padichu kaattunga.
remote_access|Tablet check panna assistance connection invite accept pannunga, naan operate panren.
account_threat|Unga email delete aagapogudhu, backup keys operator ku anuppunga.
payment|Buyer payment release aaga collect request la deposit pay pannunga.
investment|Private robot monthly fixed profit tharum, savings inga transfer pannunga.''',
('Tanglish', 'safe'): '''safety|Bank notification digits caller ku padichu kaatta thevai illai.
hard_negative|Staging server fake login tokens documentation mattum anuppunga.
ordinary|Sunday family oda museum pogalaam.
educational|Guarantee sonnaalum investment risk pogadhu.
safety|Court peru solli voucher ketta public office la neengale verify pannunga.''',
}

EVAL[('Mixed', 'scam')] = """implicit_sensitive|Insurance பணம் பெற SMS में आए digits मुझे बताओ.
remote_access|Verification के लिए tablet control வேண்டும், accept my remote session.
payment|Buyer refund கிடைக்க पहले release deposit मेरे wallet में भेजो.
credential|Email பாதுகாக்க backup secrets इस conversation में डालो.
investment|Monthly லாபம் guaranteed है, transfer all savings into our robot fund."""
EVAL[('Mixed', 'safe')] = """safety|Notification digits யாருக்கும் படிக்காதீர்கள், caller को बताना जरूरी नहीं.
hard_negative|यह staging token போலியானது, only for developer demonstrations.
ordinary|Museum போகலாம் Sunday को, bring the children too.
educational|Guaranteed returns என்றாலும் नुकसान का risk रहता है.
safety|Court अधिकारी என்று कहने वाले को independently verify before paying."""



def build():
    folder = Path(__file__).resolve().parent
    for split, blocks in [('train', TRAIN), ('eval', EVAL)]:
        rows = []
        for (language, label), block in blocks.items():
            for line in block.splitlines():
                category, text = line.split('|', 1)
                # Translations share a scenario group so CV never splits them.
                multilingual_group = f'{label}-{category}-{sum(r["language"] == language and r["category"] == category and r["label"] == label for r in rows)}'
                rows.append(dict(id=f'{split}-{len(rows)+1:03d}', text=text, label=label,
                    language=language, category=category, difficulty='hard' if category in ('implicit_sensitive','euphemistic','hard_negative','ocr','transcription') else 'standard',
                    source_type='synthetic_manual', notes='Authored prototype scenario; not an observed fraud label.',
                    group=f'{split}-{multilingual_group}' if language != 'English' else f'{split}-english-{len(rows)+1}'))
        (folder / f'{split}_v2.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
        print(split, len(rows))


if __name__ == '__main__':
    build()
