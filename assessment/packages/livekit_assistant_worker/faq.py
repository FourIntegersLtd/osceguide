"""
FAQ knowledge base for the search_help_faqs tool.

Keep wording aligned with the live app:
- Left nav: Dashboard, AI Practice, Contact Us, Settings, Achievements, Community,
  Marketplace (SCA), A to Z (SCA), Slides (SCA), etc. See NAV_LINKS in the frontend.
- AI Practice page uses tabs: Setup, Consultation Tips (SCA only), Combine Stations,
  Flagged Stations. Primary action button text is Create Session.
"""

COMMON_QUERIES = [
    {
        "section": "Getting started",
        "questions": [
            {
                "question": "What is OSCE Guide?",
                "answer": "OSCE Guide, pronounced osski Guide, is a platform for clinical communication practice. The app supports several exam tracks such as SCA, PLAB, CASC, and orthodontics. You run AI practice stations, get structured feedback, and track progress on your dashboard. Live Practice and Marketplace are available on the SCA track; other tracks may not show those options.",
            },
            {
                "question": "How do I get started after I log in?",
                "answer": "Open Dashboard for your overview. On SCA you will also see recommendations and important observations there. To practise cases, click AI Practice, stay on the Setup tab, set your session name and station count, then click Create Session. Open your session from View All Sessions when it appears, then start a station when you are ready.",
            },
            {
                "question": "Where is the main menu?",
                "answer": "The main menu is the left navigation bar. Everyone with a normal account sees items such as Dashboard, AI Practice, Contact Us, Community, Settings, and Achievements. Admin only items such as Admin or Exam tutor appear only for admins. A to Z, Slides, and Marketplace are marked SCA only in the app configuration, so they show when your account is on the SCA track.",
            },
            {
                "question": "What is the difference between Dashboard and AI Practice?",
                "answer": "Dashboard shows performance summaries and charts for your track. On SCA, it also includes sections such as Important Observations and skill recommendations. AI Practice is where you create sessions, run stations, use Combine Stations, and open Flagged Stations.",
            },
            {
                "question": "I am lost. What should I click first?",
                "answer": "If you want to practise a case, click AI Practice, stay on the Setup tab, fill in your session details, and click Create Session. If you want to see how you are improving, click Dashboard first.",
            },
        ],
    },
    {
        "section": "Navigation and sidebar labels",
        "questions": [
            {
                "question": "Where is AI Practice?",
                "answer": "Click AI Practice in the left navigation bar. It opens the Practice area where you set up sessions and manage stations.",
            },
            {
                "question": "Where is Practise or Practice in the menu?",
                "answer": "In the app the sidebar item is called AI Practice. Click that to create sessions and run stations.",
            },
            {
                "question": "Where is Contact Us?",
                "answer": "Click Contact Us in the left navigation bar. It opens the messages page where you can reach the team.",
            },
            {
                "question": "Where are Settings?",
                "answer": "Click Settings in the left navigation bar to manage your account, subscription, and related options.",
            },
            {
                "question": "Where is the Marketplace?",
                "answer": "Marketplace is in the left navigation for SCA accounts only (it is configured as SCA only in the app). It is used to post or book scheduled practice with colleagues. If you are on PLAB, CASC, or orthodontics, that link is not shown.",
            },
            {
                "question": "Where is A to Z?",
                "answer": "A to Z is in the left navigation when your account uses the SCA track. It is hidden for tracks where the nav item is marked SCA only, such as PLAB or orthodontics.",
            },
            {
                "question": "Can I add my own notes in A to Z?",
                "answer": "A to Z is reference content. There is no built in personal notes editor on those pages. Use your own notes app alongside it, or use Contact Us for feature requests.",
            },
          
            {
                "question": "Where are Slides?",
                "answer": "Slides is in the left navigation for SCA accounts only, same as A to Z and Marketplace.",
            },
            {
                "question": "Where is Community?",
                "answer": "Click Community in the left navigation bar to read posts and interact with other learners.",
            },
            {
                "question": "Where are Achievements?",
                "answer": "Click Achievements in the left navigation bar to view your milestones and badges.",
            },
        ],
    },
    {
        "section": "AI Practice — Setup and sessions",
        "questions": [
            {
                "question": "How do I start a new session?",
                "answer": "Click AI Practice in the left navigation. Make sure you are on the Setup tab. Enter a session name, choose how many stations you want, then click Create Session at the bottom.",
            },
            {
                "question": "How do I create a practice session?",
                "answer": "Go to AI Practice, Setup tab, choose the number of stations and confirm your session name, then click Create Session.",
            },
            {
                "question": "Where can I find my previous sessions?",
                "answer": "Go to AI Practice, Setup tab. At the bottom click View All Sessions to open your full list of mocks and sessions.",
            },
            {
                "question": "How do I see all my mocks?",
                "answer": "Click AI Practice, then on the Setup tab click View All Sessions. That page lists your sessions.",
            },
            {
                "question": "What are the tabs on the AI Practice page?",
                "answer": "Setup is where you create sessions and open View All Sessions. Combine Stations builds a session from stations you already attempted. Flagged Stations lists cases you marked with a flag. If you are on SCA, you also have Consultation Tips with guidance content.",
            },
            {
                "question": "What is the Setup tab?",
                "answer": "Setup is the first tab under AI Practice. You use it to name your session, pick how many stations to include, and click Create Session. You can also open View All Sessions from there.",
            },
            {
                "question": "What is Consultation Tips?",
                "answer": "On SCA, Consultation Tips is a tab under AI Practice with extra guidance material. It does not replace doing a live station.",
            },
            {
                "question": "How do I start a free trial?",
                "answer": "After you sign up and log in, go to AI Practice, Setup tab, choose how many stations you want, and click Create Session. Trial access is limited compared with a paid plan. If Create Session asks you to upgrade, or you cannot see any stations, follow the upgrade prompt or open Contact Us.",
            },
           
            {
                "question": "Can I run twelve stations back to back?",
                "answer": "Yes. On AI Practice, Setup tab, set the station count to twelve, then click Create Session. Open that session from View All Sessions and work through the stations in order.",
            },
            {
                "question": "Can I choose a specific topic or specialty for AI cases?",
                "answer": "You currently cannot pick one specialty or named topic up front. Stations are assigned randomly when the session is created. To revisit cases you already did, use Combine Stations or open them from View All Sessions. ",
            },
          
            {
                "question": "What does Include previously attempted stations mean?",
                "answer": "When this option appears on the setup form, turning it on lets the session pull in stations from an earlier subscription period. Leaving it off limits you to stations from your current access. Turn it on after you resubscribe if you want to review or retry stations from a previous plan.",
            },
            {
                "question": "I resubscribed. How do I get my old stations back?",
                "answer": "Go to AI Practice, Setup tab, turn on Include previously attempted stations if shown, then create a new session, or use Combine Stations to rebuild from stations you already attempted. If old attempts are still locked, use Contact Us and name the sessions.",
            },
            {
                "question": "Why is my session locked?",
                "answer": "Sessions can show as locked when they belong to an older subscription that is no longer active. Start a new session under your current subscription from the Setup tab, or upgrade in Settings if you need access.",
            },
            {
                "question": "How do I delete a session?",
                "answer": "Open View All Sessions from AI Practice Setup. Use the delete or trash control on the session you want to remove, and confirm if asked.",
            },
            {
                "question": "Where is Consultation Tips or the hypothesis content?",
                "answer": "On SCA, open AI Practice and select the Consultation Tips tab. That is where consultation skill guidance lives. It is separate from running a live station on Simulation.",
            },
        ],
    },
    {
        "section": "Combine sessions and flagged stations",
        "questions": [
            {
                "question": "How do I combine stations?",
                "answer": "Click AI Practice, then open the Combine Stations tab. Enter a name for the new session, select stations you have already attempted, then click Create Session.",
            },
            {
                "question": "How do I merge stations into one mock?",
                "answer": "Use AI Practice, Combine Stations tab. Pick the stations you want from your previous attempts and create a named session.",
            },
            {
                "question": "How do I get to flagged stations?",
                "answer": "Click AI Practice, then open the Flagged Stations tab at the top.",
            },
            {
                "question": "What are flagged stations?",
                "answer": "Flagged stations are cases you marked during a mock so you can find them again for review or extra practice.",
            },
            {
                "question": "How do I flag a station?",
                "answer": "During your session, use the flag icon near the station indicator at the top of the page to mark that station.",
            },
            {
                "question": "How do I review a flagged station?",
                "answer": "Go to AI Practice, Flagged Stations tab, then use View Details on the station you want.",
            },
            {
                "question": "How long do stations stay flagged?",
                "answer": "They stay flagged until you remove the flag yourself.",
            },
        ],
    },
    {
        "section": "Session list and station actions",
        "questions": [
            {
                "question": "How do I start a new attempt for a station I did before?",
                "answer": "Click AI Practice, Setup tab, View All Sessions, open your session, then click Start New Attempt on the station you want.",
            },
            {
                "question": "How do I retry a station?",
                "answer": "Open the session from View All Sessions, find the station, and click Start New Attempt.",
            },
            {
                "question": "How do I review my last attempt?",
                "answer": "Click AI Practice, View All Sessions, open your session, then click Review Last Attempt for that station.",
            },
            {
                "question": "How do I open a station I already completed?",
                "answer": "From View All Sessions, select your session, then use Review Last Attempt to see feedback and transcript, or Start New Attempt for another go.",
            },
            {
                "question": "How many attempts do I get per station?",
                "answer": "Each station allows a maximum of three attempts. After three, Start New Attempt is blocked for that station. If a glitch used an attempt without a real consultation, open Contact Us and include the session and station names so support can reset it.",
            },
            {
                "question": "How do I reattempt a station after three attempts?",
                "answer": "You cannot reset attempts yourself. After three attempts the station is finished for that access period. Use Contact Us only if technical failures burned attempts you could not complete.",
            },
            {
                "question": "How do I reset all stations and start again?",
                "answer": "There is no self serve full reset button. Create a new session from AI Practice Setup for fresh practice. For attempts due to technical issues, use Contact Us with session and station names.",
            },
        ],
    },
    {
        "section": "Station page — Simulation, Management, Feedback",
        "questions": [
            {
                "question": "Where can I find my management plan for a station?",
                "answer": "Click AI Practice, View All Sessions, open your session, click Review Last Attempt, then open the Management tab at the top.",
            },
            {
                "question": "Where is the management plan?",
                "answer": "After Review Last Attempt, use the Management tab on the station page.",
            },
            {
                "question": "How do I see my feedback?",
                "answer": "Click AI Practice, View All Sessions, open your session, click Review Last Attempt, then open the Feedback tab at the top.",
            },
            {
                "question": "Where is my Athena feedback?",
                "answer": "Open Review Last Attempt for the station, then go to the Feedback tab.",
            },
            {
                "question": "Where is the consultation transcript?",
                "answer": "Click AI Practice, View All Sessions, open your session, click Review Last Attempt, then open the Simulation tab. The Simulation screen shows the consultation area and a Transcription panel: on large screens the transcription is beside the consultation; on small screens it stacks below.",
            },
            {
                "question": "Where can I read what I said to the patient?",
                "answer": "Go to Review Last Attempt, then the Simulation tab. The transcription list is in the Transcription panel on that screen.",
            },
            {
                "question": "How do I see the chat from my simulation?",
                "answer": "Use Review Last Attempt, then the Simulation tab. Your messages appear in the Transcription panel.",
            },
            {
                "question": "Which tab has the transcript?",
                "answer": "The Simulation tab. Feedback and Management tabs do not replace it.",
            },
            {
                "question": "How do I start the consultation?",
                "answer": "In attempt mode, open the Simulation tab. The top tab label may read Start Simulation until you are in the simulation view. Press the Start Consultation button in the consultation panel to begin the timed case.",
            },
            {
                "question": "Does the AI patient answer my questions?",
                "answer": "Yes. After Start Consultation, speak as you would to a real patient. The AI patient responds by voice. Ask normal consultation questions. If you get no reply, check microphone permission and remember to use Chrome on a laptop for the best audio experience.",
            },
            {
                "question": "What is the Simulation tab?",
                "answer": "Simulation is where you run or review the live consultation and see the Transcription panel for that attempt.",
            },
            {
                "question": "The patient or AI is not responding but the timer is running",
                "answer": "Stop and refresh the page rather than letting the timer burn an attempt. Allow microphone access, use Chrome or Edge on a laptop, check that the correct mic is selected, and start the consultation again. If voice still fails, leave the station and use Contact Us with the session and station names so attempts can be reviewed.",
            },
            {
                "question": "I cannot hear the AI when I start consultation",
                "answer": "Check speaker volume and that the browser is not muted, then refresh and try Start Consultation again on Chrome or Edge. Headphones sometimes help. If it keeps failing, use Contact Us.",
            },
            {
                "question": "How do I debrief with Athena?",
                "answer": "Click AI Practice, View All Sessions, open your session, Review Last Attempt, Feedback tab, then click Start Debrief to talk with Athena about your performance.",
            },
            {
                "question": "Athena debrief stays on connecting and never speaks",
                "answer": "Refresh the page, confirm microphone permission, and try Start Debrief again from the Feedback tab. Use a laptop browser when possible. If it still sticks on connecting, use Contact Us with the session name.",
            },
            {
                "question": "Can I practice role reversals?",
                "answer": "After feedback is available, click Start Debrief in the Feedback tab. In the modal, choose Practice as Patient so Athena acts as the doctor and you as the patient. On orthodontics, only Debrief Session is offered; Practice as Patient is hidden.",
            },
            {
                "question": "What is Practice as Patient?",
                "answer": "It is the second option in the debrief modal on non ortho tracks: Athena runs the consultation as the doctor while you experience it as the patient. The UI labels this mode Doctor Mode while it is active.",
            },
            {
                "question": "Athena Doctor mode or Practice as Patient is not available",
                "answer": "Complete a station attempt first and wait until feedback is ready. Open Review Last Attempt, Feedback tab, then Start Debrief and choose Practice as Patient.",
            },
            {
                "question": "What happens in a debrief session?",
                "answer": "Start Debrief opens a modal where you pick Debrief Session to talk through your performance with Athena, or Practice as Patient on supported tracks to hear Athena model the doctor side.",
            },
            {
                "question": "Feedback is still generating. What do I do?",
                "answer": "Stay on the station page. When feedback is ready, you will get a notification and can open the Feedback tab. If it takes unusually long, try refreshing after a few minutes or use Contact Us.",
            },
            {
                "question": "I finished a station but there is no feedback or transcript",
                "answer": "Open AI Practice, View All Sessions, open the session, then Review Last Attempt. Check Feedback for scores and Simulation for the transcript. Wait a few minutes if generation is still running. If Review Last Attempt is missing or says page not found, use Contact Us with the session and station names.",
            },
            {
                "question": "The attempt did not save or Review Last Attempt is missing",
                "answer": "Refresh and reopen the session from View All Sessions. If the station still shows no usable attempt or feedback after a completed consultation, use Contact Us and include session name, station name, and roughly when you practised.",
            },
        ],
    },
    {
        "section": "Performance Dashboard",
        "questions": [
            {
                "question": "Where can I see my progress?",
                "answer": "Click Dashboard in the left navigation bar. You can view performance trends and improvement over time there.",
            },
            {
                "question": "What should I focus on improving?",
                "answer": "On SCA, open Dashboard and read the Important Observations section and the recommendation panel. On PLAB and other tracks the dashboard layout differs; use your charts and latest station feedback to choose what to practise next in AI Practice.",
            },
            {
                "question": "Where are important observations?",
                "answer": "Important Observations is a section on the SCA dashboard. It is not part of the PLAB dashboard in the current app.",
            },
        ],
    },
    {
        "section": "Recommendations",
        "questions": [
            {
                "question": "How does the recommendation system work?",
                "answer": "On SCA, the dashboard recommendations first highlight regressions, then stagnations, then if neither applies they fall back to your lowest scoring skill.",
            },
            {
                "question": "How are skills prioritized in recommendations?",
                "answer": "On SCA, the focus skill picks the worst regression if any exist, otherwise the worst stagnation, otherwise the lowest score. Alternative skills get higher priority when drops are larger, scores are lower, or a skill appears in more than one list.",
            },
            {
                "question": "What benefits do recommendations give me?",
                "answer": "On SCA you get a primary focus skill plus alternative skills to choose from, driven by your recent data. Other exam dashboards may not show this same panel.",
            },
            {
                "question": "Why is Athena suggesting this skill?",
                "answer": "On SCA, open Dashboard and read the recommendations area next to Important Observations. Elsewhere, follow the feedback from your latest stations.",
            },
        ],
    },
    {
        "section": "Understanding your feedback scores",
        "questions": [
            {
                "question": "What do Red, Amber, and Green scores mean?",
                "answer": "On SCA station feedback, skills are shown with Red, Amber, and Green levels. Green means strong, Amber means acceptable with room to grow, Red means needs work. Green and Amber are both treated as satisfactory in summaries like X out of Y skills.",
            },
            {
                "question": "What does a score like 7 of 11 mean?",
                "answer": "In SCA style feedback it usually means seven skills were Green or Amber out of eleven assessed in that area, leaving four Red. PLAB and other tracks may present scores differently in their own feedback screens.",
            },
            {
                "question": "Should I worry about Red scores?",
                "answer": "Where Red appears, it simply marks a skill to prioritise. It is common early on and improves with targeted practice.",
            },
            {
                "question": "What is RAG scoring?",
                "answer": "RAG means Red, Amber, Green, the three colour levels used on SCA skill breakdowns in feedback.",
            },
        ],
    },
    {
        "section": "Practice with colleagues",
        "questions": [
            {
                "question": "How do I practice with a colleague?",
                "answer": "These features are built for SCA. On the SCA dashboard, click Practice with colleague, then pick Live Practice for an instant queue match, or use Schedule Practice to go to Marketplace for booked slots. After a mock, SCA users can also see Live Practice and Schedule Practice on the session end screen.",
            },
            {
                "question": "What is Live Practice?",
                "answer": "On SCA, Live Practice is started from Practice with colleague on the dashboard or from the session end screen. It places you in a queue to be matched with another user. The human practice UI recommends using a laptop.",
            },
            {
                "question": "How does the Marketplace work?",
                "answer": "SCA only: open Marketplace from the left navigation to post availability or claim slots. Use the Upcoming Sessions tab to join booked sessions. Prefer a laptop for video sessions.",
            },
            {
                "question": "How do I join a scheduled Marketplace session?",
                "answer": "SCA: open Marketplace, then the Upcoming Sessions tab. You can join from twenty minutes before the scheduled start time until one hour after it. A popup may also appear when a session becomes joinable.",
            },
            {
                "question": "Marketplace says too early even though it is my start time",
                "answer": "Confirm you are on Upcoming Sessions and within the join window starting twenty minutes before the booked time. Refresh the page and check your device clock. If it still says too early at the correct time, use Contact Us with the session time.",
            },
            {
                "question": "How are doctor and patient roles assigned?",
                "answer": "Roles are assigned automatically when you join, with fairness so you experience both sides over time.",
            },
            {
                "question": "Can I join on my phone?",
                "answer": "For colleague practice, use a laptop. Mobile does not support the full video and interaction experience.",
            },
            {
                "question": "What if my partner does not show up?",
                "answer": "You can cancel from Upcoming Sessions if they do not join in time. Reminder emails for marketplace sessions are intended to go out about one hour before the scheduled start.",
            },
        ],
    },
    {
        "section": "Community",
        "questions": [
            {
                "question": "How does the community work?",
                "answer": "Community is a space to share thoughts, ask questions, and learn from peers preparing for similar exams. Be respectful and follow guidelines. Offensive content may be removed.",
            },
        ],
    },
    {
        "section": "Settings, subscription, and billing",
        "questions": [
            {
                "question": "Where do I manage my subscription?",
                "answer": "Open Settings, then the Payments tab. Profile is separate for name, email, and password.",
            },
            {
                "question": "How do I subscribe or pay?",
                "answer": "Open Settings, then the Payments tab, choose a plan, and complete checkout. You may also see an upgrade prompt when Create Session needs a paid plan. After paying, refresh or log out and log in again, then go to AI Practice to create a session.",
            },
            {
                "question": "How do I upgrade my plan?",
                "answer": "If the API returns an upgrade prompt, a modal may open from the practice flow. Otherwise open Settings and use the Payments tab.",
            },
            {
                "question": "I paid but I still cannot access sessions or cases",
                "answer": "Log out, log back in, then open Settings, Payments to confirm the plan shows as active. Next go to AI Practice, Setup, and Create Session. If Payments still looks unpaid or Create Session is blocked, use Contact Us and include the email you paid with and the approximate payment time.",
            },
            {
                "question": "How long does payment take to activate?",
                "answer": "Access is usually immediate after a successful checkout. If nothing changes within a few minutes, refresh, log out and in again, then check Settings Payments. If it still fails, use Contact Us.",
            },
            {
                "question": "I paid with the wrong email",
                "answer": "Subscriptions are tied to the account email used at checkout. Use Contact Us from the account you should have, and include both email addresses so support can link the payment.",
            },
            {
                "question": "How do I cancel my subscription?",
                "answer": "You cannot cancel mid plan after payment. Access continues until the end of the subscription period you bought, then it ends. There is a strict no refund policy after you access any station. Read the refund policy before purchasing, or email hello at fourintegers dot com if you are unsure.",
            },
            {
                "question": "When does my subscription end?",
                "answer": "Open Settings, Payments. Your current plan and timing details appear there. Use Download receipt for a payment confirmation (also emailed when you subscribed).",
            },
            {
                "question": "Can I get an invoice for tax?",
                "answer": "Open Settings, Payments and tap Download receipt for your payment confirmation (emailed at purchase). For a full VAT tax invoice, contact hello@fourintegers.com with the email on your account.",
            },
            {
                "question": "Where do I enter a promo or referral code?",
                "answer": "The referral programme is paused for now. There are no active promo or referral codes at the moment. We will announce when codes return. Do not pay twice hoping a code will apply.",
            },
            {
                "question": "Who do I email for billing questions?",
                "answer": "Email hello at fourintegers dot com before purchasing if you need clarification. For questions not covered here, use Contact Us in the app.",
            },
        ],
    },
    {
        "section": "Pricing and access",
        "questions": [
            {
                "question": "Do I need to pay for OSCE Guide?",
                "answer": "Yes, OSCE Guide requires a subscription. Typical plans include 1 month, 3 months, and 6 months. Exact prices and station counts depend on your exam. Check the public pricing section on the website for current numbers.",
            },
            {
                "question": "How many stations or cases do I get?",
                "answer": "Station counts depend on the plan you bought and your exam track. Check the pricing page before purchase, and after payment open AI Practice to create sessions under that access. The help assistant cannot quote a live inventory number.",
            },
            {
                "question": "What is your refund policy?",
                "answer": "There is a strict no refund policy after you access any station. By paying you agree that each subscription is its own purchase and that access to any station makes the payment non refundable. Email hello at fourintegers dot com before buying if unsure.",
            },
            {
                "question": "Can I get extra time for reading or the consultation?",
                "answer": "Station timers follow the standard exam style shown in the app. There is no self serve control to set longer reading or consultation times. Use Contact Us if you need support about accommodations.",
            },
        ],
    },
    {
        "section": "Referral and discount codes",
        "questions": [
            {
                "question": "Do you offer referral codes or discount codes?",
                "answer": "Referrals and discount codes are paused. There are no active promo codes right now. We will announce when they return.",
            },
            {
                "question": "How can I get a discount?",
                "answer": "Discount codes are not available at the moment. The referral programme is paused.",
            },
            {
                "question": "Can I share a referral code?",
                "answer": "Not while the programme is paused. We will notify users when sharing codes is possible again.",
            },
        ],
    },
    {
        "section": "Voice help and Athena",
        "questions": [
            {
                "question": "How does voice help work?",
                "answer": "You can speak with Athena from the help panel. Ask how to use the app. Athena uses the FAQ knowledge base and can highlight controls on screen when UI guidance is enabled.",
            },
            {
                "question": "Can Athena answer clinical exam content questions?",
                "answer": "Use Athena in help mode for navigation and how to use the product. For medical decisions always follow your own clinical judgement and official exam guidance.",
            },
        ],
    },
    {
        "section": "Orthodontics CV",
        "questions": [
            {
                "question": "How do I upload my CV for ortho?",
                "answer": "On the orthodontics track, you can upload a PDF from Settings, Profile tab, using the Upload CV button. Onboarding may also prompt you from the ortho dashboard modal when first setting up.",
            },
            {
                "question": "Where is ortho onboarding?",
                "answer": "The ortho dashboard can open an onboarding modal for steps such as CV upload. You can also manage CV from Settings under Profile when app type is ortho.",
            },
        ],
    },
    {
        "section": "Technical troubleshooting",
        "questions": [
            {
                "question": "Microphone or audio is not working",
                "answer": "Allow microphone permission in the browser, use Chrome or Edge if possible, check system input volume, and disconnect Bluetooth headsets that conflict. For Live Practice use a laptop with a stable connection.",
            },
            {
                "question": "Microphone permission fails on my tablet or phone",
                "answer": "Open the site in Chrome on Android or Safari on iOS, check site permissions for microphone, and avoid in-app browsers. For the most reliable AI practice audio, use a laptop with Chrome or Edge.",
            },
            {
                "question": "The consultation crashes or cuts off mid station",
                "answer": "Use a stable connection on a laptop browser, avoid switching apps mid station, and refresh if the voice link drops. If the timer kept running without a real consultation, use Contact Us with session and station names so attempts can be reviewed.",
            },
            {
                "question": "The page is blank or stuck loading",
                "answer": "Hard refresh the page, try another browser, disable aggressive ad blockers for this site, and check your internet connection. If it persists, use Contact Us with what you were doing.",
            },
            {
                "question": "I cannot see Marketplace or A to Z",
                "answer": "Those items are for SCA accounts. PLAB and some other exam types hide them. Your sidebar only shows what applies to your exam.",
            },
            {
                "question": "Which browser works best?",
                "answer": "Use an up to date Chrome or Edge on desktop for the most reliable audio, video, and colleague practice features.",
            },
            {
                "question": "Is there a mobile app?",
                "answer": "OSCE Guide runs in the browser as a progressive web app. You can add it to your home screen from Chrome or Safari. There is no separate store app.",
            },
            {
                "question": "Images are missing on a station or flagged scenario",
                "answer": "Refresh and reopen the station from Review Last Attempt or Flagged Stations. If images still do not show, use Contact Us with the station name.",
            },
        ],
    },
    {
        "section": "Achievements and account",
        "questions": [
            {
                "question": "What are Achievements?",
                "answer": "Achievements track milestones as you use the platform, such as completing sessions or hitting learning goals. Open Achievements in the left navigation to see your progress.",
            },
            {
                "question": "How do I log out?",
                "answer": "Use the Logout control at the bottom of the left navigation sidebar.",
            },
            {
                "question": "How do I change my profile or email?",
                "answer": "Open Settings, Profile tab. You can update your username and save. The email field is read only in the app; to change email, use Contact Us so support can help. Password updates use the change password control on the same Profile screen.",
            },
        ],
    },
    {
        "section": "Questions not in the FAQ",
        "questions": [
            {
                "question": "What if my question is not listed here?",
                "answer": "Open Contact Us in the left navigation and send a message to the team. Include session and station names for practice problems, and the payment email for billing. For pre purchase questions you can also email hello at fourintegers dot com.",
            },
            {
                "question": "Can you reset my exam for me?",
                "answer": "The help assistant cannot change your account or exam data. Use Contact Us and the team will assist.",
            },
            {
                "question": "Can I upload my own case scenarios?",
                "answer": "You cannot add custom patient cases into AI Practice yourself. Use Contact Us for feature requests.",
            },
        ],
    },
]


_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "can",
        "i",
        "me",
        "my",
        "we",
        "you",
        "your",
        "it",
        "its",
        "this",
        "that",
        "what",
        "where",
        "when",
        "how",
        "why",
        "which",
        "who",
        "to",
        "of",
        "in",
        "on",
        "at",
        "for",
        "with",
        "and",
        "or",
        "but",
        "not",
        "there",
        "here",
        "get",
        "find",
    }
)


def _tokenize(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw in text.lower().split():
        token = "".join(ch for ch in raw if ch.isalnum())
        if len(token) >= 2 and token not in _STOPWORDS:
            tokens.add(token)
    return tokens


def _score_faq(query: str, question: str, answer: str, section: str) -> float:
    query_norm = query.strip().lower()
    if not query_norm:
        return 0.0

    question_norm = question.lower()
    answer_norm = answer.lower()
    section_norm = section.lower()
    haystack = f"{question_norm} {answer_norm} {section_norm}"

    score = 0.0
    if query_norm in question_norm:
        score += 12.0
    elif query_norm in haystack:
        score += 6.0

    query_tokens = _tokenize(query_norm)
    if not query_tokens:
        return score

    question_tokens = _tokenize(question_norm)
    answer_tokens = _tokenize(answer_norm)
    section_tokens = _tokenize(section_norm)

    overlap_q = len(query_tokens & question_tokens)
    overlap_a = len(query_tokens & answer_tokens)
    overlap_s = len(query_tokens & section_tokens)
    score += overlap_q * 4.0 + overlap_a * 1.5 + overlap_s * 1.0

    for token in query_tokens:
        if token in question_norm:
            score += 1.0
        elif token in answer_norm:
            score += 0.35

    return score


def search_common_queries(query: str, *, limit: int = 3) -> tuple[str, int]:
    """
    Return up to `limit` best-matching FAQ entries for the user's question.
    Returns (formatted_text, match_count).
    """
    cleaned = (query or "").strip()
    if not cleaned:
        return (
            "No search query provided. Ask the user to repeat their question, "
            "or direct them to Contact Us in the left navigation bar.",
            0,
        )

    ranked: list[tuple[float, str, dict[str, str]]] = []
    for section in COMMON_QUERIES:
        section_name = section["section"]
        for qa in section["questions"]:
            question = qa["question"]
            answer = qa["answer"]
            score = _score_faq(cleaned, question, answer, section_name)
            if score > 0:
                ranked.append((score, section_name, qa))

    ranked.sort(key=lambda item: item[0], reverse=True)
    top = ranked[: max(1, limit)]

    if not top:
        return (
            "No matching FAQs found for this question. "
            "Tell the user you cannot answer from the FAQ list and direct them to "
            "Contact Us in the left navigation bar.",
            0,
        )

    lines = [
        "Use ONLY the FAQ answers below. If none fit, direct the user to Contact Us.",
        "",
    ]
    for _score, section_name, qa in top:
        lines.append(f"[{section_name}]")
        lines.append(f"QUESTION: {qa['question']}")
        lines.append(f"ANSWER: {qa['answer']}")
        lines.append("")

    return "\n".join(lines).strip(), len(top)


def get_all_common_queries() -> str:
    """
    Returns all common queries and answers in a formatted text with clear demarcations.
    """
    formatted_text = """
    NOTE: For questions not covered in these FAQs, please use the Contact Us tab
    in the left navigation bar to contact our support team directly.
    """

    for section in COMMON_QUERIES:
        formatted_text += "\n<<SECTION_START>>\n"
        formatted_text += f"[{section['section']}]\n"

        for qa in section["questions"]:
            formatted_text += "\n<<QA_PAIR_START>>\n"
            formatted_text += f"QUESTION: {qa['question']}\n"
            formatted_text += f"ANSWER: {qa['answer']}\n"
            formatted_text += "<<QA_PAIR_END>>\n"

        formatted_text += "<<SECTION_END>>\n"
        formatted_text += "#####################################\n"

    return formatted_text
