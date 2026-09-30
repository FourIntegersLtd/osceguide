interface Activity {
  about: string;
  educationalActivity: string[];
  keyPoints?: string[];
  commonPitfalls?: string[];
  relatedSkills?: string[];
}
interface ConsultationToolkit {
  tasks: Record<string, Activity>;
  relatingToOthers: Record<string, Activity>;
  clinicalManagement: Record<string, Activity>;
  globalSkills: Record<string, Activity>;
}
export const consultationToolkit: ConsultationToolkit = {
  tasks: {
    opens_consultation: {
      about:
        "The way you open a consultation sets the foundation for the entire interaction. In your OSCE Guide practice sessions, focus on making a clear introduction, using an engaging open question, and establishing early rapport. Your opening should demonstrate genuine interest while giving patients space to share their story. This is particularly crucial in phone consultations, where your voice tone, clarity, and privacy checks become your main tools. Poor openings often lead to disjointed consultations and weak rapport, as shown in your transcript feedback.",
      educationalActivity: [
        "Review your OSCE Guide transcripts with Athena to analyze your openings: Did you (1) introduce yourself clearly, (2) verify the patient's identity, (3) use an effective open question, and (4) let them respond fully?",
        "Use Athena's role-reversal feature to practice different opening styles. Notice how she opens consultations - what makes her approach effective? How does she establish rapport quickly?",
        "Study your RAG ratings for consultation openings. Pick two new opening phrases to practice with Athena and track how they affect your ratings.",
        "During transcript review, focus on clarity and professionalism. Did you check for privacy? Was your tone appropriate? Let Athena help identify areas for improvement.",
        "Work with Athena to create your personal opening checklist (e.g., greeting → identity check → open question → active listening). Practice until it feels natural.",
        "Ask Athena to simulate both rushed and well-paced consultations. Compare the differences in patient engagement and your RAG ratings.",
        "Draft several opening phrases and practice them with Athena until they sound authentic and professional.",
        "Review your voice modulation in telephone consultations - practice adjusting your tone for warmth and clarity.",
      ],
    },
    discovers_psychosocial_context: {
      about:
        "Understanding a patient's life context is crucial for patient-centered care. Your OSCE Guide transcripts should show how you explore work, home, and social factors that impact health. Many doctors either skip this or approach it mechanically, leading to lower ratings. When done well, this exploration helps patients feel understood and leads to more practical management plans. In telephone consultations, while you'll need to probe more actively, patients often feel more comfortable sharing sensitive information.",
      educationalActivity: [
        "Review some recent transcripts with Athena. Track how often you explored psychosocial context and how you used this information in your management plans.",
        "In your next few debriefs with Athena, make psychosocial exploration a priority. Ask about daily impacts, stressors, and how their circumstances affect health choices.",
        "After each consultation, debrief with Athena about what you learned about the patient's life context. How did this information shape your management approach?",
        "Use Athena's debrief to focus on psychosocial factors (like work stress or family caregiving). Practice incorporating these details into your explanations.",
        "During feedback sessions with Athena, analyze how naturally you asked about home/work life. Were your questions open-ended? Did you use the information effectively?",
        "Build a collection of natural conversation prompts with Athena's help, like 'How has this been affecting your daily routine?' Practice using these smoothly.",
        "Practice taking brief notes about psychosocial factors during consultations. Review these with Athena to ensure you're capturing key information effectively.",
      ],
    },
    identifies_cues: {
      about:
        "Patients often drop subtle verbal or non-verbal hints - 'cues' - that signal underlying worries, feelings, or needs. In your OSCE Guide transcripts, look for moments where patients hint at deeper concerns, like saying 'I've been worried about getting back to work' Or showing anxiety through speech patterns. During consultations, these cues often reveal the true reason for the visit. During phone consultations, pay special attention to vocal changes, pauses, or shifts in speaking pace since you won't have visual cues to rely on. If you notice a potential cue but aren't certain, always ask for clarification rather than making assumptions.",
      educationalActivity: [
        "Review your OSCE Guide consultation transcripts with Athena. Together, identify moments where patients dropped hints about their concerns. Ask Athena to help spot cues you might have missed.",
        "During transcript review, highlight both verbal cues (word choice, hesitations) and described non-verbal signals. Create a list with Athena of what you noticed versus what was missed.",
        "After spotting a cue in your transcript, debrief with Athena about your response: Did you explore it effectively? Practice alternative ways to address similar cues in future consultations.",
        "Use Athena's debrief feature to practice responding to subtle cues. For example, when she says 'It's probably nothing...', practice different ways to explore this hint.",
        "Compare your cue detection across multiple transcripts. Work with Athena to identify patterns - are you missing certain types of cues more often?",
        "With Athena's help, build a personal reference list of common cues from your transcripts. Categorize them by type (emotional, social, health-related) and review regularly.",
        "When reviewing a consultation where you missed important cues, ask Athena to help you replay the scenario with different responses. Practice various ways to ask follow-up questions.",
        "During debriefs with Athena, analyze which types of cues you consistently overlook. Is it emotional cues? Social context? Work with her to develop specific strategies for improvement.",
      ],
    },
    discovers_ice: {
      about:
        "Discovering Ideas, Concerns, and Expectations (ICE) is fundamental to effective consultations, not just a box-ticking exercise. Your OSCE Guide transcripts should demonstrate how well you understand what patients think is happening, what worries them, and what they hope to achieve. This understanding directly shapes your diagnosis and management decisions. For example, knowing whether a patient is worried about a serious condition or expecting specific treatment helps you tailor your approach. In telephone consultations, while some patients may hesitate to share freely, others might feel more comfortable discussing sensitive topics without face-to-face interaction. Your RAG ratings will reflect how effectively you gather and use this information.",
      educationalActivity: [
        "Review your recent OSCE Guide transcripts with Athena. Check if you discovered all three ICE components separately - remember each provides unique insights. Track your RAG ratings for ICE discovery.",
        "Study how Athena elicits ICE during role-reversal sessions. Note her phrasing and timing. Which approaches feel most natural? Add effective phrases to your consultation toolkit.",
        "Practice consultations with Athena where you focus specifically on ICE. Try different ways of asking - both direct questions and encouraging natural narrative through open questions.",
        "Use Athena's feedback to refine how naturally you incorporate ICE questions. Work on timing and flow so they don't feel forced or random.",
        "During debriefs with Athena, analyze consultations where patients volunteered ICE without direct questions. What techniques encouraged this natural sharing?",
        "Practice summarizing ICE information back to patients during consultations. Let Athena help you refine how you use this information in your management plans.",
        "Review your RED or AMBER ratings with Athena. Identify whether ICE discovery was missed entirely or just not used effectively in your planning.",
      ],
    },
    interprets_tests: {
      about:
        "In consultations, examination and test findings are as crucial as history-taking for refining your diagnostic process. You'll encounter various scenarios where you need to interpret previous results, self-monitoring data (like blood pressure readings), or submitted photos. Your RAG ratings will reflect how effectively you use this information to support or exclude diagnoses. In telephone consultations, while physical examination is limited, you can gather valuable information through careful listening - for example, assessing breathing patterns, speech characteristics, or conducting mental state examinations. When reviewing photos or test results, clearly document how these findings influence your clinical reasoning and whether they warrant in-person assessment.",
      educationalActivity: [
        "Review your OSCE Guide transcripts with Athena to analyze how effectively you used available examination and test data. Check your RAG ratings for interpretation skills.",
        "During transcript review with Athena, evaluate each piece of examination/test information using three key questions: Is it reliable and current? How does it inform your diagnosis? Did you identify any knowledge gaps?",
        "Practice with Athena how to verbalize your interpretation of findings clearly. For example, explain how a photo's features support or challenge your diagnostic hypotheses.",
        "In audio consultation practice, work with Athena to enhance your ability to gather examination clues through listening - like assessing breathing patterns or speech characteristics.",
        "Use Athena's feedback to improve how you guide patients through self-examination or simple tasks during phone consultations. Practice clear, safe instructions.",
        "When reviewing mental state examinations in your transcripts, analyze with Athena how effectively you conducted and interpreted these assessments remotely.",
        "Practice scenarios with Athena where you need to decide whether remote assessment is sufficient or if in-person examination is necessary. Focus on patient safety.",
        "Compare your examination interpretation skills across different consultation types in your transcripts. Work with Athena to identify patterns in your RED or AMBER ratings.",
      ],
    },
    generates_hypotheses: {
      about:
        "Generating diagnostic hypotheses is fundamental to safe practice in consultations. Your RAG ratings will reflect how systematically you develop and test possible diagnoses. Start with open questions to gather initial information, then use targeted closed questions to test specific hypotheses. Always consider both common conditions and serious possibilities, ranking them by likelihood. This process is especially crucial in phone consultations where physical examination is limited - you'll need to be even more thorough in your questioning to make safe decisions about next steps, whether that's giving advice, arranging face-to-face assessment, or urgent referral.",
      educationalActivity: [
        "Review your OSCE Guide transcripts with Athena. for each consultation, list your differential diagnoses before checking the feedback. Compare your thinking with the model answers.",
        "Use the feedback to analyze your RED or AMBER ratings in hypothesis generation. Are you missing particular types of diagnoses? Create a structured improvement plan.",
        "Practice with Athena using common presenting complaints (like headache or abdominal pain). Generate comprehensive differentials considering patient factors like age and risk factors.",
        "Work through challenging symptom scenarios with Athena. Focus on developing targeted questions that help discriminate between possible diagnoses.",
        "During debriefs, demonstrate to Athena how you generate and test hypotheses without physical examination. Get feedback on your questioning strategy.",
        "Role-play with Athena scenarios requiring 'red flag' Assessment. Practice incorporating critical questions (like neurological symptoms in headache) systematically.",
        "Review your transcripts to assess how well you balance open and closed questions in hypothesis testing. Are you gathering enough information before narrowing down?",
        "Practice explaining your diagnostic reasoning to patients during consultations. Let Athena help you refine how you communicate your thought process.",
      ],
    },
    rules_in_out_disease: {
      about:
        "Actively checking for serious conditions ('red flags') is crucial for patient safety in consultations. Your RAG ratings will specifically assess how thoroughly you identify and investigate potential red flags. While common conditions are more likely, missing a serious diagnosis could have severe consequences. This means systematically asking about warning symptoms for each presenting complaint. In phone consultations, where physical examination isn't possible, your questioning about red flags becomes even more critical - it will determine both your management plan and its urgency. Never skip this process, even if you're planning a face-to-face review.",
      educationalActivity: [
        "Review your OSCE Guide transcripts with Athena, focusing on RED or AMBER ratings for red flag assessment. Create a list of serious conditions you might have missed.",
        "Practice with Athena using common presentations. for each case, systematically work through relevant red flags. For example, in back pain: bladder/bowel control, saddle anesthesia, progressive weakness.",
        "Use Athena's feedback to analyze how effectively you investigate red flags. Are you asking the right questions? Are you documenting your reasoning clearly?",
        "Work through challenging scenarios with Athena where serious conditions might be masked by common symptoms. Practice recognizing subtle warning signs.",
        "During debriefs, demonstrate to Athena how you compensate for the lack of physical examination by thorough red flag questioning.",
        "Role-play with Athena scenarios where patients are reluctant to discuss sensitive symptoms. Develop techniques to ask about red flags sensitively but thoroughly.",
        "Review your transcripts to assess whether you're consistently considering serious conditions across all consultation types. Look for patterns in missed red flags.",
        "Practice explaining to patients why you're asking about specific warning symptoms. Let Athena help you refine your communication approach.",
      ],
    },
    reaches_diagnosis: {
      about: `Reaching an accurate working diagnosis or analysis is fundamental to effective consultations. Your RAG ratings will reflect how well you deduce and justify your diagnostic conclusions. While it's essential to make a diagnosis, avoid jumping to conclusions too early - be prepared to revise your thinking as new information emerges. In telephone consultations, where examination is limited, focus on thorough history-taking and existing test results. For follow-up consultations where diagnosis is established, analyze the current situation carefully to inform management decisions.`,
      educationalActivity: [
        `Review your OSCE Guide transcripts with Athena. How often do you reach and share a clear working diagnosis? Check your RAG ratings for diagnostic accuracy.`,
        `Practice with Athena to identify where premature diagnostic decisions led to missed information. Focus on keeping an open mind throughout data gathering.`,
        `Use Athena's feedback to analyze cases where your diagnosis was incorrect or unjustified. What information did you miss or misinterpret?`,
        `In audio consultation, demonstrate how you reach diagnostic conclusions with limited examination findings. Let Athena help refine your approach.`,
        `Work through scenarios with Athena where the diagnosis is pre-established but requires careful analysis of current issues.`,
        `Review your knowledge gaps with Athena - are certain conditions or presentations consistently challenging? `,
        `Practice articulating your diagnostic reasoning clearly before sharing with patients. Let Athena help you develop confident, clear explanations.`,
        `Compare your diagnostic accuracy across face-to-face versus telephone consultations. Work with Athena to improve areas where you're less confident.`,
      ],
    },
  },
  relatingToOthers: {
    generates_rapport: {
      about:
        "Rapport is the foundation of effective communication and involves creating a state of mutual trust and understanding with the patient. It enhances every other part of the consultation and is closely linked to empathy. Doctors who build rapport demonstrate warmth, curiosity, and responsiveness, using both verbal and non-verbal cues. Poor rapport can make consultations feel rushed, judgmental, or disconnected, which may discourage patients from opening up. While rapport can happen naturally with some patients, it usually depends on specific communication behaviours - like using open body language, asking open questions, adapting tone, and listening actively. In telephone consultations, rapport is harder to build without visual cues, so tone, pacing, and verbal empathy become even more important.",
      educationalActivity: [
        "Watch recordings of your face-to-face consultations and assess your rapport-building behaviours - ignore clinical content and focus on how you interact.",
        "Ask yourself: Do I appear interested and engaged? Do I use open questions? Do I look bored or distracted? What is my posture and body language?",
        "Identify if and when you repeated questions unnecessarily - this can signal poor listening or disengagement and weaken rapport.",
        "Pay attention to non-verbal rapport signals: do you nod, smile, or use affirming phrases to show understanding?",
        "With Athena, review transcripts and identify any moments where your tone or phrasing felt jarring, scripted, or insincere.",
        "Reflect on whether you used empathy phrases appropriately and in context - or whether they came across as forced or mismatched to the patient's tone.",
        "Observe the consultation style of clinicians who build strong rapport - note their body language, tone, phrasing, and timing, then try to apply similar techniques.",
        "Repeat this observation with several different colleagues across settings (face-to-face and audio) and reflect on what makes each approach effective.",
        "List any rapport-damaging habits you notice in yourself (e.g. Inappropriate social questions, poor posture, or rigid tone) and make a plan to consciously avoid them.",
        "Ask Athena to role play difficult consultations, and practice adjusting your responses to match the patient's emotional state.",
        "In telephone consultations, review your tone - especially at the start of the call. Are you warm and friendly, or neutral and clipped?",
        "Check whether you picked up and explored verbal cues (e.g. Flat, depressed tone) or missed them entirely.",
        "Note how many open questions you asked in each consultation and whether you gave the patient space to speak without interruption.",
        "Review any inappropriate or jarring psychosocial questions - e.g. Asking about marriage or employment out of context - and plan how to introduce such topics more sensitively.",
        "Share your self-analysis with Athena and use her structured guidance to improve areas where rapport could be stronger.",
        "Continue reviewing and refining your approach to verbal empathy, tone modulation, and patient-led questioning to make your consultations feel more natural and connected.",
      ],
    },
    uses_open_questions: {
      about:
        "Open questions are a powerful tool in GP consultations for building trust, eliciting deeper information, and understanding the patient's perspective. They invite narrative responses rather than simple yes/no answers, helping uncover psychosocial context, ideas, concerns, and expectations (ICE). Using open questions early in the consultation allows the patient's agenda to surface naturally and supports a fluent, patient-centred conversation. This approach not only strengthens rapport but can improve time management by making the rest of the consultation more focused. In telephone consultations, where visual rapport cues are absent, open questions become even more important to create space for patients to share freely without interruption or bias.",
      educationalActivity: [
        "Create a personal list of open questions that feel natural to you and that you can use regularly in consultations.",
        "Ask colleagues or Athena which open questions they use most often and consider adapting any that might work for your style.",
        "Familiarise yourself with effective phrasing - questions beginning with 'what' Or 'how' Often work well (e.g., 'What's been happening?' Or 'How is this affecting your daily life?').",
        "Practice softening direct questions like 'why' By saying 'I'm interested in why you think that...' To avoid sounding confrontational.",
        "Do an exercise where you build further open questions based on the patient's own words (e.g., 'You mentioned your wife was worried - what was she thinking might happen?').",
        "Review video consultations/OSCE Guide transcripts to assess how soon you switch to closed questions - ask yourself: 'Did I give the patient enough space to speak freely?'",
        "Watch for habits of asking closed questions prematurely - note when clarification is truly needed and whether you've allowed open exploration first.",
        "In a consultation review session with Athena, focus on the balance and timing of open vs closed questions, and identify improvements.",
        "Read through a batch of your transcripts and write down all the open questions you used, noting when they appeared during the consultation.",
        "Challenge yourself to begin your next few consultations using only open questions for the first two minutes - then review the impact on patient engagement.",
        "Use Athena to role-play narrative-style consultations where your only prompt is an open question, and reflect on how the conversation flows.",
      ],
    },
    clarifies_cues: {
      about:
        "Clarifying and exploring cues are essential skills for understanding a patient's problem, concerns, and expectations fully. Clarification helps resolve confusion, vagueness, or ambiguity in the patient's story. This can involve repeating questions with a different emphasis, using open or closed questions, summarising complex information, or checking for understanding. Exploring cues builds on this by drawing attention to emotional or narrative hints - like tone of voice or incomplete statements - that reveal underlying ideas or concerns. In some cases, these skills help 'rescue' A muddled consultation. In telephone consultations, the lack of visual feedback makes listening carefully and responding sensitively to cues even more important.",
      educationalActivity: [
        "Review your transcripts and identify any moments where the patient's story was unclear, vague, or confusing.",
        "Pause at those moments and ask yourself: Did I clarify the issue, or did I move on without resolving it?",
        "For each attempt at clarification, evaluate whether your response actually helped - did it make the situation clearer or simply repeat the confusion?",
        "Practice using mini-summaries (chunking and checking) to structure long or disorganised patient narratives, then check if the patient agrees with your summary.",
        "Develop a bank of phrases for clarifying cues, such as: 'You mentioned you were worried - was it about something specific?' Or 'That sounds difficult, could you tell me more about it?'",
        "Use open questions first to clarify uncertainty, followed by focused closed questions only when needed to confirm specifics.",
        "Try role reversal with Athena or colleagues and write down techniques they use to clarify or sensitively follow up on vague patient statements.",
        "Apply those strategies in your next few consultations, then review with Athena to assess if clarity improved.",
        "Repeat this cycle of analysis and practice to build confidence and fluency in identifying and resolving unclear communication.",
        "During telephone consultations, pay close attention to subtle vocal cues - flat tone, hesitation, or changes in pace may signal uncertainty or distress.",
        "Make a habit of verbalising clarifications in telephone consultations (e.g., 'Just to check I've understood you correctly - you've had this for two weeks and it's getting worse, is that right?').",
        "Track how often you miss or delay responding to cues in audio consults and reflect on ways to bring them into the conversation more naturally.",
        "Avoid jarring or out-of-context psychosocial questions; instead, build questions naturally from what the patient has shared so far.",
        "Use Athena to simulate muddled consultations and practice techniques for regaining clarity while staying empathic and structured.",
      ],
    },
    listens_curiosity: {
      about: `Curiosity is the strong desire to know or learn something, and being genuinely interested in the patient is key to understanding the reasons behind their presentation and illness behaviour. A curious approach in consultation helps build rapport, uncover ICE (Ideas, Concerns, Expectations) and psychosocial cues, enrich the diagnostic process, and tailor management plans to individual needs. Active listening means focusing fully on the patient's contributions, showing interest, and facilitating their story. It requires concentration and sensitivity. Good listening helps you detect subtle cues and respond appropriately. On the phone or in audio-only consultations, without visual cues, verbal encouragement like "I'm interested in that" Is essential to show curiosity and prevent silence from feeling like disinterest.`,
      educationalActivity: [
        "Watch recordings of your consultations and note how often you repeat questions or suggest management plans the patient has already addressed.",
        "Identify moments where poor listening may have caused you to miss important cues; note what you would do differently next time.",
        "Conduct a series of consultations where you deliberately avoid interrupting or rushing to solutions, then review with Athena whether your listening improved.",
        "Practice expanding curiosity about patients' Lives and illness in subsequent consultations; reflect on whether this yields useful information, and adjust focus accordingly.",
        "In telephone consultations, listen carefully for verbal cues indicating opportunities to ask follow-up questions like 'That's interesting, tell me more' Or 'I'm curious about...'.",
        "Use phrases that demonstrate your curiosity and encourage disclosure, especially when visual feedback is absent.",
      ],
    },
    uses_closed_questions: {
      about:
        "Closed questions elicit specific facts (yes/no or brief answers) and are best used after open exploration to confirm hypotheses or screen for red flags. In consultations, delaying closed questions until the patient's narrative is complete preserves rapport and ensures you don't miss important contextual details. Systematic, hypothesis-driven closed questioning - introduced with signposting or permission for sensitive topics - enhances efficiency and diagnostic accuracy without cutting off the patient's story prematurely.",
      educationalActivity: [
        "Observe your transcript and note the timestamp when you first switch to closed questions - aim to begin no earlier than two minutes into the history-taking phase.",
        "List every closed question you asked and map each to a diagnostic hypothesis or red flag; remove any that don't serve a clear purpose.",
        "Practice signposting before sensitive closed questions (e.g. 'I'm going to ask some brief yes/no questions about your mood - would that be okay?') so the patient knows what to expect.",
        "Role-play with Athena: start with open questions only, then introduce closed questions in logical order - reflect on how this affects flow and rapport.",
        "Simulate a muddled history scenario with Athena and practice using targeted closed questions to 'rescue' Key facts - evaluate speed and accuracy of information gathered.",
      ],
    },
    explains_rationale: {
      about:
        "Verbalizing your clinical reasoning - 'thinking aloud' - helps patients follow your thought process, builds trust, and makes data gathering more transparent. Stating why you ask each question (e.g., 'I'd like to ask about chest pain to rule out heart issues') clarifies your hypotheses and engages the patient in decision-making. In consultations, explaining rationale ties your questions to diagnostic reasoning, improves efficiency, and substitutes for visual cues in audio or remote exams.",
      educationalActivity: [
        "Review your transcripts and highlight every instance where you explain your reasoning; tally ratios of rationale statements per case and set a target to increase by 25% over five sessions.",
        "Create a 'rationale phrase bank' Of at least ten sentences linking questions to hypotheses or red flags; practice using two new phrases in each new simulation.",
        "Simulate a muddled history with Athena and practice 'rescuing' It by thinking aloud: narrate your hypotheses ('I'm considering X because of Y') and compare information gathering speed.",
        "Review your transcripts, tally how often you say 'I'm asking this to check for...' And aim for at least one rationale statement every three minutes.",
        "During debrief sessions with Athena: review whether each piece of data you gathered was prefaced by a rationale and discuss any missed opportunities.",
        "Challenge yourself in the next three consultations to preface every closed question with a brief rationale, then review transcripts to assess naturalness and efficiency.",
      ],
    },
    verbalises_diagnosis: {
      about:
        "Communicating your working diagnosis (or differential diagnoses) to the patient is essential for trust, understanding, and shared decision-making. Stating what you think is happening - and briefly how you reached that conclusion - helps patients make sense of their symptoms and prepares them for the management plan. Verbalising your diagnosis (or analysis when certainty is low) demonstrates clear clinical reasoning and ensures patients stay engaged, even in audio-only encounters where visual confirmation is absent.",
      educationalActivity: [
        "Read your transcripts. Did you name a working diagnosis or differential? Did you explain your reasoning? Tally your success rate and aim for 100% by your next five runs.",
        "Pause after your diagnosis statement and ask 'Have you heard of this condition?' To gauge patient understanding - repeat until you do this in every station.",
        "Create a 'diagnosis script' Of three concise phrasing templates (e.g., 'I'm thinking this may be [X] because of [Y] and [Z]') and use a different template in each of your next three practice sessions.",
        "Practice sharing a range of possible diagnoses ('It could be A, B or C') and outline the next steps you'd take to narrow these down, then compare speed and clarity across two trials.",
        "Track how often you verbalise uncertainty ('I'm not completely certain, but my leading possibility is...') and set a goal to include a clear rationale in every simulation.",
      ],
    },
    shares_ice_plan: {
      about:
        "When planning management, explicitly link options to the patient's Ideas, Concerns & Expectations (ICE). Sharing choices in small 'chunks' - then inviting feedback - ensures the plan reflects what matters to the patient, builds buy-in, and prevents confusion. Signpost each option ('One approach we could try is...') and check understanding ('How does that fit with what you expected?') to maintain a collaborative feel.",
      educationalActivity: [
        "Review transcripts: count each time you reference ICE before proposing an option and aim to include ICE in every future consultation - essentially always 'ICE into management'.",
        "Develop a 'chunk and check' Routine: practice delivering management in 3–4 sentence segments, pausing to ask 'Does that make sense so far?' And 'Would you like me to go over this again?'.",
        "After each consultation, go through your feedback: identify missed ICE links and practice including them in future practice sessions.",
        "Review transcripts and feedback: identify where ICE was omitted and brainstorm concise ways to weave it into your explanations.",
        "In your next session, try to include ICE as much as possible within the management plan and check understanding with direct questions.",
      ],
    },
    negotiates_psychosocial_plan: {
      about:
        "Effective negotiation integrates the psychosocial details you've gathered - like work, family, or financial concerns - into management discussions. By linking recommendations to what matters most to the patient, you make options relatable and build collaboration. Begin negotiation only once you've explored their context fully, listen actively to their priorities or fears, and then propose a middle ground that respects their circumstances without compromising care.",
      educationalActivity: [
        "Review transcripts of recent consultations where negotiation was required; note how often you referenced psychosocial factors and aim to include at least one such link in every negotiation.",
        "Role-play common scenarios (e.g. Lifestyle change, medication adherence) with Athena: before proposing your plan, explicitly connect it to a psychosocial detail (e.g. 'I know you're busy with work…').",
        "Create a list of three negotiation phrases that weave in psychosocial context (e.g. 'Given your childcare responsibilities, how could we adjust this plan?') and practice using one per consultation.",
        "After each consultation, debrief with Athena: identify any missed opportunities to tie management to the patient's life context.",
        "While debriefing with Athena, try a challenging negotiation in a practice session: intentionally propose an option that conflicts with a known patient priority, then explore their objections and renegotiate based on their reasons.",
        "Set a personal metric: in your next five consultations, track how many times you ask a follow-up question about why the patient resists an option (e.g. 'Can you tell me more about your concern?').",
        "Observe a colleague's recorded consultation and note strategies they use to step into the patient's shoes; borrow one technique and integrate it into your next negotiation.",
      ],
    },
  },
  clinicalManagement: {
    offers_management_plan: {
      about:
        "A safe and effective management plan must be based on up-to-date clinical guidelines and tailored to the individual patient's context. One of the most common causes of failure in GP consultations is outdated or incorrect management due to knowledge gaps or rushed planning. Inadequate use of time, failure to explore psychosocial issues or ICE, and poor communication - especially in telephone consultations - can all compromise safety. A strong management phase involves adequate preparation, shared decision-making, and checking for understanding. In remote settings, it's especially important to supplement verbal instructions with written summaries or links and to verify that the patient comprehends the plan to avoid unsafe outcomes.",
      educationalActivity: [
        "Use the RCGP Super-Condensed Curriculum Topic Guides to identify personal knowledge gaps in clinical management.",
        "Complete a self-assessment of your knowledge in common GP conditions and note areas requiring focused revision.",
        "Address these gaps using trusted evidence-based resources like NICE, Clinical Knowledge Summaries, Guidelines.co.uk, or Patient.info.",
        "Avoid passive reading - practice applying new knowledge with your patients, or do more scenarios on OSCE Guide.",
        "Internalise key management plans by regularly reviewing the treatment and follow-up for common conditions until they become second nature.",
        "Develop the habit of writing down conditions you were unsure about during real consultations - then read up immediately after and note what you've learned (PUNS → DENS approach).",
        "Where possible, discuss new learning points with Athena or experienced colleagues to consolidate understanding and get additional insights.",
        "Ensure your consultations allow enough time for shared decision-making. Avoid rushing this stage, especially if previous tasks ran over.",
        "Use ICE and psychosocial details gathered earlier in the consultation to personalise the management plan.",
        "During telephone consultations, supplement verbal instructions with written information via text or links to trusted resources.",
        "Always check the patient's understanding of the plan - ask them to repeat it back in their own words or ask clarifying questions.",
        "If management plans are consistently rated RED or AMBER in your OSCE Guide feedback, download your transcripts and review them with Athena to identify recurring issues.",
      ],
    },
    manages_comorbidity: {
      about:
        "Managing co-morbidities means treating the patient as a whole, not just addressing their presenting problem. It involves understanding how current medications, past medical history, and allergies may interact with new treatment plans or affect clinical decisions such as prescribing, referrals, or investigations. Failing to consider co-existing conditions or treatments can lead to unsafe, inappropriate, or overly burdensome plans. Patients should be involved in decisions about starting or stopping medications, especially when balancing the risks and benefits across their broader health context.",
      educationalActivity: [
        "Get into the habit of quickly reviewing the patient's medication list at the start of each consultation.",
        "While reading medications, ask yourself: Could this medication contribute to the current problem or interfere with a proposed plan?",
        "Actively review the patient's past medical history - not just passively - by considering how chronic conditions might influence today's management.",
        "Before initiating a plan, check for potential interactions or contraindications related to co-existing conditions or current prescriptions.",
        "Think holistically about the patient: would stopping a medication improve their quality of life? Are they already on too many treatments?",
        "Discuss with the patient any decisions about adding, adjusting, or stopping medication, taking into account their lifestyle, values, and expectations.",
        "Do the same when considering referrals or imaging - ask whether their conditions influence feasibility or appropriateness of these decisions.",
        "Reflect with Athena on any differences in your consideration of co-morbidity across consultation types, and strategize how to standardize your approach.",
        "Practice asking patients directly about their views on changes to long-term treatments - are they comfortable adding more medication?",
        "Review OSCE Guide feedback for any AMBER or RED ratings related to co-morbidity handling, and discuss patterns or improvements with Athena.",
        "Rehearse 'whole person' Thinking by practicing clinical reasoning that takes into account lifestyle, preferences, history, and clinical risks - not just the symptom in front of you.",
      ],
    },
    provides_safety_net: {
      about:
        "Providing clear, appropriate follow-up and safety netting is essential for patient safety and effective shared care. Without it, patients may become anxious, delay seeking help, or take harmful actions. A well-designed safety net is SMART: Specific, Measurable, Achievable, Relevant, and Timely. Follow-up should be tailored to the condition and the patient's context, and it should include clear instructions about when and how to seek help if things change. In telephone consultations, follow-up and safety netting become even more critical - patients rely more on verbal advice alone, so confirming their understanding and providing supplementary information (via text or links) is vital.",
      educationalActivity: [
        "In each case, ask yourself: Would this advice help the patient return at the right time - not too soon or too late?",
        "Ask patients directly whether they feel confident about the follow-up plan. Can they repeat back when and how they would seek further help?",
        "If patients struggle to recall or explain the follow-up advice, clarify it again, using simpler terms or written formats, then re-check their understanding.",
        "Practice consistently asking patients to explain the follow-up plan in their own words - this builds clarity and flags misunderstandings early.",
        "Review your OSCE Guide feedback for RED or AMBER ratings in follow-up and safety netting. Note patterns or omissions and practice them with Athena.",
        "Adapt follow-up strategies to patient preferences and clinical context - consider whether a phone call or face-to-face appointment is most appropriate.",
        "Reflect on how often your follow-up timing is vague - e.g. 'come back if worse' - and instead practice giving specific timeframes or red flag symptoms to watch for.",
        "Observe follow-up approaches in role reversal provided by Athena, and note how timing, delivery, and patient comprehension are managed.",
      ],
    },
  },
  globalSkills: {
    structures_consultation: {
      about:
        "A well-structured consultation flows logically and efficiently, starting with an introduction, then history, examination, diagnosis, and plan, with clear signposting at each stage. This helps keep the consultation on track and makes it easier for the patient to follow.",
      educationalActivity: [
        "Review consultation transcripts with Athena to identify areas causing poor structure.",
        "Assess whether there is a logical flow between consultation tasks, such as from history to management.",
        "Check if you provide helpful summaries during complex exchanges to keep the patient and yourself aligned.",
        "Look for evidence of signposting when changing topics or approaching sensitive or personal questions.",
        "Focus on one structural issue at a time (e.g. Improving signposting), and apply fixes incrementally.",
        "Use other sections of the Toolkit to guide your improvement on each structural element.",
      ],
    },
    avoids_repetition: {
      about:
        "Repeating questions during a consultation can disrupt flow and confuse patients. This often happens when the clinician is distracted, thinking ahead, or uncertain about what to do next. Other causes include poor phrasing of the original question, not registering the patient's answer, or not exploring puzzling responses in real time. Sometimes repetition is used to fill silences or to compensate for insecurity about earlier parts of the consultation. Recognising and addressing the underlying cause of repetition is key to maintaining a clear, efficient consultation.",
      educationalActivity: [
        "Review your consultation transcripts and count how many times you repeated a question.",
        "Reflect on why you repeated each question - were you distracted, unclear, or unsure how to proceed?",
        "Repeat the exercise during debrief with Athena in a new consultation with the goal of eliminating all repetition.",
        "Focus on active listening and clarify responses immediately if they are unclear.",
        "Consider whether you explain repetition to the patient when it happens, and practice doing so if needed.",
        "Discuss with Athena to identify patterns and develop strategies for reducing repetition.",
      ],
    },
    progresses_through_tasks: {
      about:
        "Efficiently progressing through the tasks of a consultation - such as opening, data gathering, diagnosis, and management - ensures nothing is overlooked and allows time for each step. When progression is poor, tasks may be repeated unnecessarily, rushed, or omitted altogether. This can happen if interpersonal skills like cue recognition or open questioning are weak. For example, if ICE or psychosocial details are missed initially, the doctor may circle back later, disrupting flow. Reviewing your consultation structure helps identify whether each task is addressed once, at the right time, and with enough depth.",
      educationalActivity: [
        "Select a few recorded consultations and draw a timeline for each, marking where each key task (e.g. Opens consultation, discovers ICE, explains diagnosis) occurs.",
        "Look for tasks that are repeated or missed entirely - consider whether certain skills (like using open questions) contributed to this.",
        "Review these consultations with Athena and identify which interpersonal skills may need improvement to address tasks more effectively the first time.",
        "Use the OSCE Guide RAG Rating Grid to assess each task in several consultations.",
        "For any tasks rated RED, discuss with Athena why the task was missed or poorly handled and whether a related skill was weak.",
        "Identify one or two weak tasks and focus on improving them in future consultations, ensuring you execute them clearly and only once.",
        "Review your past OSCE Guide feedback to spot repeated RED or AMBER patterns - these often point to issues with consultation flow.",
        "Try role reversal with Athena and watch closely how the consultation is structured.",
        "Pay particular attention to how tasks like discovering psychosocial context, identifying cues, and uncovering ICE are completed early, clearly, and without repetition.",
        "Apply what you've observed by structuring your own consultations with deliberate, logical task progression and minimal backtracking.",
      ],
    },
    recognises_ethical_implications: {
      about:
        "Ethical awareness means recognising and addressing moral dilemmas and professional responsibilities during a consultation. This includes respecting confidentiality, obtaining informed consent, being honest with the patient, and making fair decisions. Ethical situations often arise subtly - such as when a patient requests something inappropriate, or when there's a conflict between safety and autonomy. Clinicians should be prepared to consider the consequences of different options and seek relevant guidance. Practising reflective decision-making helps ensure ethical standards are upheld in complex scenarios.",
      educationalActivity: [
        "As you encounter ethical dilemmas in your consultations, keep a log or journal of the situations.",
        "For each case, reflect on what additional information you needed to fully understand the ethical issue.",
        "List the management options available to you and consider the pros and cons of each.",
        "Think about what formal guidance, regulations, or professional standards apply to the scenario.",
        "Use Athena to explore comparable ethical cases and review recommended approaches.",
        "Decide what the most ethically sound action was in hindsight, and whether you would do anything differently next time.",
        "Discuss challenging ethical scenarios with Athena to get structured feedback and alternative perspectives.",
        "Look back over previous OSCE Guide feedback to see whether any decisions or actions could have had ethical implications you missed.",
        "Practice verbalizing your ethical reasoning in mock consultations to make your decision-making process more transparent.",
      ],
    },
    finishes_data_gathering: {
      about:
        "Completing the data gathering phase in a timely and focused manner - typically by around the 6-minute mark - is essential for ensuring enough time remains for diagnosis and management. When this skill is lacking, it often stems from poor progression through tasks or inefficient interpersonal techniques. Common issues include asking excessive or unfocused questions, performing unnecessary tests, failing to act on cues, or using closed questions too early. Identifying and addressing these patterns can help streamline your consultations and improve overall clarity.",
      educationalActivity: [
        "If your OSCE Guide feedback frequently shows RED or AMBER ratings for this skill, begin by breaking down what you're doing during the data gathering phase.",
        "Ask yourself if you're progressing through tasks logically - refer to your rating for 'Progresses through tasks' To cross-check.",
        "Identify habits such as over-questioning 'just in case,' Or offering unnecessary tests and examinations.",
        "Create a written list of specific problem areas you've identified during consultations.",
        "Tackle each problem one at a time - make small changes during your consultations to track progress.",
        "Review and reflect on whether you're using interpersonal skills appropriately, such as 'Identifies cues', 'Uses open questions', 'Explores cues', and 'Uses closed questions'.",
        "Ask Athena to help you audit whether closed questions are being used too early, or if you're missing and not exploring cues effectively.",
        "Evaluate whether poor listening, repetition, or excessive permission-seeking are contributing to delays.",
        "Try adjusting one variable at a time - such as focusing more on open questions - and measure how this changes your consultation pacing.",
      ],
    },
    uses_clear_language: {
      about:
        "Using clear, jargon-free language helps ensure patients understand their condition and treatment plan. Miscommunication can occur when doctors use technical terms or rush through explanations. Patients may not always admit they're confused, so it's important to check understanding actively. Matching the patient's own words can enhance clarity and build rapport. In both face-to-face and telephone consultations, being sensitive to verbal and non-verbal signs of confusion - like silence, loss of eye contact, or hesitancy - is crucial for spotting when things need to be rephrased.",
      educationalActivity: [
        "Ask patients directly if the explanation you've given makes sense - if they seem unsure or say no, follow up by asking what confused them.",
        "During face-to-face consultations, watch for visual signs that the patient is confused, such as looking down or avoiding eye contact.",
        "In telephone consultations, be alert to pauses, hesitations, or flat responses - these may indicate the patient hasn't understood.",
        "Gently check understanding without sounding interrogative; patients may feel embarrassed about not understanding and need encouragement to admit it.",
        "Practice mirroring the patient's own phrasing in your responses - for example, if they say they're stressed, acknowledge it using their words.",
        "Use role-play scenarios with Athena where you respond to a patient using their language to reinforce understanding.",
        "Review OSCE Guide feedback where clarity of explanation was rated AMBER or RED, and reflect on how your language might have caused confusion.",
        "Ask Athena to simulate patient reactions to common jargon and test your ability to rephrase explanations clearly and empathetically.",
        "Build a habit of using short sentences and familiar words when explaining diagnoses, treatments, or next steps.",
        "Develop a personal checklist of common medical phrases you tend to use and write down simpler alternatives you can use in practice.",
      ],
    },
    remains_responsive_to_patient: {
      about:
        "Responsiveness is the ability to truly listen, adapt, and follow the patient's lead during a consultation. Without it, the interaction can feel rushed, cold, or even dismissive - making the patient less likely to engage or share key information. This skill includes active listening, acknowledging cues, allowing patients to speak freely, and showing genuine interest in their concerns. It's essential to strike a balance: a structured consultation without responsiveness feels robotic, while an unstructured one without responsiveness feels chaotic. In telephone consultations, responsiveness is even more challenging, as you must rely on tone, pauses, and subtle verbal signs instead of visual cues.",
      educationalActivity: [
        "Ask yourself: Do I interrupt the patient unnecessarily? Do I allow them space to finish their thoughts or share preferences?",
        "Check whether you explored patient cues with sensitivity and followed up on them rather than moving on too quickly.",
        "Reflect on whether you acknowledged the patient's concerns or ideas clearly - did the patient appear heard and understood?",
        "Review if and how you used information from cues and ICE to guide discussion and personalise your management plan.",
        "Watch for signs of disengagement: Did the patient seem confused, frustrated, or withdrawn at any point? What might have caused it?",
        "Use Athena to role play moments where responsiveness could have been stronger and brainstorm alternative ways to handle them.",
        "Pay special attention to responsiveness in telephone consultations - did you talk over the patient or miss cues due to poor audio or interruptions?",
        "Practice slowing your pace in calls, allowing silences, and using explicit check-ins (e.g. 'Is this making sense so far?') to gauge patient engagement.",
        "Aim to improve your flexibility - follow the patient's emotional tone, redirect when needed, and adjust your consultation structure without losing empathy or clarity.",
        "Reflect on whether you're consistently demonstrating behaviours that seem unresponsive, and ask yourself why this might be happening.",
        "Consider if issues such as lack of time, lack of interest, stress, or low confidence in the topic are affecting your responsiveness.",
        "If you identify an issue like time pressure or knowledge gaps, explore strategies to reduce these - for example, better planning, targeted revision, or consulting Athena for support to practice these specific issues.",
      ],
    },
  },
};
