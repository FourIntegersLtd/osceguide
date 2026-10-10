"""Base FAQ: settings, billing, pricing, voice help, troubleshooting, account."""

from __future__ import annotations

from ..models import FaqEntry

BILLING = "Settings, subscription, and billing"
PRICING = "Pricing and access"
REFERRAL = "Referral and discount codes"
VOICE = "Voice help and Athena"
TROUBLESHOOTING = "Technical troubleshooting"
ACCOUNT = "Achievements and account"
OTHER = "Questions not in the FAQ"

_SETTINGS_NAV = ("settings",)

ENTRIES: tuple[FaqEntry, ...] = (
    FaqEntry(
        "manage-subscription",
        BILLING,
        "Where do I manage my subscription?",
        "Open {nav.settings}, then the Payments tab. Profile is separate for name, email, and password.",
        _SETTINGS_NAV,
    ),
    FaqEntry(
        "subscribe",
        BILLING,
        "How do I subscribe or pay?",
        "Open {nav.settings}, then the Payments tab, choose a plan, and complete checkout. You may also see an upgrade prompt when Create Session needs a paid plan. After paying, refresh or log out and log in again, then go to {nav.mocks} to create a session.",
        _SETTINGS_NAV,
    ),
    FaqEntry(
        "upgrade-plan",
        BILLING,
        "How do I upgrade my plan?",
        "If the API returns an upgrade prompt, a modal may open from the practice flow. Otherwise open {nav.settings} and use the Payments tab.",
        _SETTINGS_NAV,
    ),
    FaqEntry(
        "paid-no-access",
        BILLING,
        "I paid but I still cannot access sessions or cases",
        "Log out, log back in, then open {nav.settings}, Payments to confirm the plan shows as active. Next go to {nav.mocks}, Setup, and Create Session. If Payments still looks unpaid or Create Session is blocked, use {nav.messages} and include the email you paid with and the approximate payment time.",
        _SETTINGS_NAV,
    ),
    FaqEntry(
        "payment-activation",
        BILLING,
        "How long does payment take to activate?",
        "Access is usually immediate after a successful checkout. If nothing changes within a few minutes, refresh, log out and in again, then check {nav.settings} Payments. If it still fails, use {nav.messages}.",
        _SETTINGS_NAV,
    ),
    FaqEntry(
        "wrong-email",
        BILLING,
        "I paid with the wrong email",
        "Subscriptions are tied to the account email used at checkout. Use {nav.messages} from the account you should have, and include both email addresses so support can link the payment.",
    ),
    FaqEntry(
        "cancel-subscription",
        BILLING,
        "How do I cancel my subscription?",
        "You cannot cancel mid plan after payment. Access continues until the end of the subscription period you bought, then it ends. There is a strict no refund policy after you access any station. Read the refund policy before purchasing, or email hello at fourintegers dot com if you are unsure.",
    ),
    FaqEntry(
        "subscription-end",
        BILLING,
        "When does my subscription end?",
        "Open {nav.settings}, Payments. Your current plan and timing details appear there. Use Download receipt for a payment confirmation (also emailed when you subscribed).",
        _SETTINGS_NAV,
    ),
    FaqEntry(
        "invoice",
        BILLING,
        "Can I get an invoice for tax?",
        "Open {nav.settings}, Payments and tap Download receipt for your payment confirmation (emailed at purchase). For a full VAT tax invoice, contact hello@fourintegers.com with the email on your account.",
        _SETTINGS_NAV,
    ),
    FaqEntry(
        "promo-code",
        BILLING,
        "Where do I enter a promo or referral code?",
        "The referral programme is paused for now. There are no active promo or referral codes at the moment. We will announce when codes return. Do not pay twice hoping a code will apply.",
    ),
    FaqEntry(
        "billing-email",
        BILLING,
        "Who do I email for billing questions?",
        "Email hello at fourintegers dot com before purchasing if you need clarification. For questions not covered here, use {nav.messages} in the app.",
    ),
    FaqEntry(
        "need-to-pay",
        PRICING,
        "Do I need to pay for OSCE Guide?",
        "Yes, OSCE Guide requires a subscription. Typical plans include 1 month, 3 months, and 6 months. Exact prices and station counts depend on your exam. Check the public pricing section on the website for current numbers.",
    ),
    FaqEntry(
        "station-count",
        PRICING,
        "How many stations or cases do I get?",
        "Station counts depend on the plan you bought and your exam. Check the pricing page before purchase, and after payment open {nav.mocks} to create sessions under that access. The help assistant cannot quote a live inventory number.",
    ),
    FaqEntry(
        "refund-policy",
        PRICING,
        "What is your refund policy?",
        "There is a strict no refund policy after you access any station. By paying you agree that each subscription is its own purchase and that access to any station makes the payment non refundable. Email hello at fourintegers dot com before buying if unsure.",
    ),
    FaqEntry(
        "extra-time",
        PRICING,
        "Can I get extra time for reading or the consultation?",
        "Station timers follow the standard exam style shown in the app. There is no self serve control to set longer reading or consultation times. Use {nav.messages} if you need support about accommodations.",
    ),
    FaqEntry(
        "referral-codes",
        REFERRAL,
        "Do you offer referral codes or discount codes?",
        "Referrals and discount codes are paused. There are no active promo codes right now. We will announce when they return.",
    ),
    FaqEntry(
        "discount",
        REFERRAL,
        "How can I get a discount?",
        "Discount codes are not available at the moment. The referral programme is paused.",
    ),
    FaqEntry(
        "share-referral",
        REFERRAL,
        "Can I share a referral code?",
        "Not while the programme is paused. We will notify users when sharing codes is possible again.",
    ),
    FaqEntry(
        "voice-help",
        VOICE,
        "How does voice help work?",
        "You can speak to Help from the help panel. Ask how to use the app. Help answers from the FAQ and can highlight controls on screen when UI guidance is enabled.",
    ),
    FaqEntry(
        "clinical-questions",
        VOICE,
        "Can Athena answer clinical exam content questions?",
        "Use Help for navigation and how to use the product. For medical decisions always follow your own clinical judgement and official exam guidance.",
    ),
    FaqEntry(
        "mic-not-working",
        TROUBLESHOOTING,
        "Microphone or audio is not working",
        "Allow microphone permission in the browser, use Chrome or Edge if possible, check system input volume, and disconnect Bluetooth headsets that conflict. Use a laptop with a stable connection for the best results.",
    ),
    FaqEntry(
        "mic-mobile",
        TROUBLESHOOTING,
        "Microphone permission fails on my tablet or phone",
        "Open the site in Chrome on Android or Safari on iOS, check site permissions for microphone, and avoid in-app browsers. For the most reliable AI practice audio, use a laptop with Chrome or Edge.",
    ),
    FaqEntry(
        "consultation-crash",
        TROUBLESHOOTING,
        "The consultation crashes or cuts off mid station",
        "Use a stable connection on a laptop browser, avoid switching apps mid station, and refresh if the voice link drops. If the timer kept running without a real consultation, use {nav.messages} with session and station names so attempts can be reviewed.",
    ),
    FaqEntry(
        "blank-page",
        TROUBLESHOOTING,
        "The page is blank or stuck loading",
        "Hard refresh the page, try another browser, disable aggressive ad blockers for this site, and check your internet connection. If it persists, use {nav.messages} with what you were doing.",
    ),
    FaqEntry(
        "best-browser",
        TROUBLESHOOTING,
        "Which browser works best?",
        "Use an up to date Chrome or Edge on desktop for the most reliable audio, video, and practice features.",
    ),
    FaqEntry(
        "mobile-app",
        TROUBLESHOOTING,
        "Is there a mobile app?",
        "OSCE Guide runs in the browser as a progressive web app. You can add it to your home screen from Chrome or Safari. There is no separate store app.",
    ),
    FaqEntry(
        "missing-images",
        TROUBLESHOOTING,
        "Images are missing on a station or flagged scenario",
        "Refresh and reopen the station from Review Last Attempt or Flagged Stations. If images still do not show, use {nav.messages} with the station name.",
    ),
    FaqEntry(
        "achievements",
        ACCOUNT,
        "What are Achievements?",
        "{nav.achievements} tracks milestones as you use the platform, such as completing sessions or hitting learning goals. Open {nav.achievements} in the left navigation to see your progress.",
        ("achievements",),
    ),
    FaqEntry(
        "logout",
        ACCOUNT,
        "How do I log out?",
        "Use the Logout control at the bottom of the left navigation sidebar.",
    ),
    FaqEntry(
        "change-profile",
        ACCOUNT,
        "How do I change my profile or email?",
        "Open {nav.settings}, Profile tab. You can update your username and save. The email field is read only in the app; to change email, use {nav.messages} so support can help. Password updates use the change password control on the same Profile screen.",
        _SETTINGS_NAV,
    ),
    FaqEntry(
        "not-listed",
        OTHER,
        "What if my question is not listed here?",
        "Open {nav.messages} in the left navigation and send a message to the team. Include session and station names for practice problems, and the payment email for billing. For pre purchase questions you can also email hello at fourintegers dot com.",
    ),
    FaqEntry(
        "reset-exam",
        OTHER,
        "Can you reset my exam for me?",
        "The help assistant cannot change your account or exam data. Use {nav.messages} and the team will assist.",
    ),
    FaqEntry(
        "upload-cases",
        OTHER,
        "Can I upload my own case scenarios?",
        "You cannot add custom patient cases into {nav.mocks} yourself. Use {nav.messages} for feature requests.",
    ),
)
