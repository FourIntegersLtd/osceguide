export interface Testimonial {
  quote: string;
  name: string;
}
export const TESTIMONIALS: Testimonial[] = [
  {
    quote:
      "Great interactive software that allowed me practice SCA cases on my own to gain confidence in speaking with others. It clearly helped fine tune me away from common errors and hone my consultation skills towards RCGP standard. I also loved the convenience of on demand access to practise whenever I wanted. In the end I passed on 1st attempt. OSCE guide definitely helped!",
    name: "Dr Elizabeth Okuonghae",
  },
  {
    quote:
      "I passed my exam! OSCE Guide is an excellent resource and tool to practice. I found it very useful as it helped me to understand what areas I need to improve in my consultation - Would definitely recommend to trainees preparing for the SCA.",
    name: "Dr Nazia Qadeer",
  },
  {
    quote:
      "I used OSCE Guide to practice for my SCA exams. It was very helpful for me especially when friends were busy. I gained from the feedback from Athena and also acted as the patient so I could see how she will handle some cases. I also attended SCA courses and used other relevant materials for the exam preparation. Overall, it was a positive experience for me. I passed my exam.",
    name: "Dr I.O",
  },
  {
    quote:
      "I love practicing with AI and being able to check my improvements in the various domains. I love the fact that my SCA preparation is as flexible as my schedule.",
    name: "Dr Marion Ogunmola",
  },
  {
    quote:
      "It was quite helpful having AI role players and Athena for debriefs. Most times colleagues are not free when I am, but with OSCE Guide, I can role play anytime, even at night. This was truly a game changer in my SCA preparation.",
    name: "Dr C.O",
  },
  {
    quote:
      "It was instrumental in my preparation for the exam. I was hooked as soon as I did the trial. I passed my exam.",
    name: "Dr Adeleke",
  },
  {
    quote:
      "Provided real-time guidance for practicing consultations, with structured feedback aligned to SCA marking domains. Progress was consistently tracked, boosting my confidence and morale. Support is available 24/7. Highly recommended! I passed my exam!",
    name: "Dr S",
  },
  {
    quote:
      "Amazing idea, AI is fast and responsive. I no longer need to search for a study group all the time. I passed my exam",
    name: "Dr R",
  },
  {
    quote:
      "Perfect practice partner, invaluable feedback. AMAZING. I passed my exam!",
    name: "Dr L",
  },
  {
    quote:
      "The OSCE Guide app was a helpful tool in my SCA preparation. It provided concise, structured clinical scenarios that mirrored real consultation formats. The case-based approach helped reinforce my consultation structure, red flag screening, and patient-centred communication. I particularly found the clear prompts, differentials, and management plans useful for quick revision and long term revision.",
    name: "Dr Emmanuel Okojie",
  },
  {
    quote:
      "I started preparing for the SCA really late and honestly had no idea where to start. I was added to lots of groups and recommended different websites for revision and practice, and I tried most of them. OSCE Guide was by far the best. The AI practice is really responsive, the cases are excellent, and the customer support is amazing. I used it to practice alone and we used it during my tutorial sessions but they have so many great features I haven't even explored yet. Every time I've sent a panicked email (which was usually because of a silly mistake I'd made!), the team has replied almost immediately and helped me sort things out. They've been incredibly helpful throughout my preparation, and I'd definitely recommend OSCE Guide to anyone studying for the SCA.",
    name: "Dr Zahra",
  },
];

export interface MarqueeTestimonial {
  name: string;
  role: string;
  excerpt: string;
  highlight: string;
}

export const MARQUEE_TESTIMONIALS: MarqueeTestimonial[] = [
  {
    name: "Dr Elizabeth Okuonghae",
    role: "Passed SCA",
    excerpt:
      "I practised SCA cases on my own whenever I wanted. In the end I passed on 1st attempt. @OSCEGuide definitely helped!",
    highlight: "passed on 1st attempt",
  },
  {
    name: "Dr Nazia Qadeer",
    role: "Passed SCA",
    excerpt:
      "I passed my exam! @OSCEGuide is an excellent resource. Would definitely recommend to trainees preparing for the SCA.",
    highlight: "I passed my exam!",
  },
  {
    name: "Dr I.O",
    role: "Passed SCA",
    excerpt:
      "I used @OSCEGuide when friends were busy. I gained from Athena's feedback and also acted as the patient. I passed my exam.",
    highlight: "I passed my exam",
  },
  {
    name: "Dr Marion Ogunmola",
    role: "SCA candidate",
    excerpt:
      "I love practising with AI and checking my improvements across domains. Prep with @OSCEGuide is as flexible as my schedule.",
    highlight: "as flexible as my schedule",
  },
  {
    name: "Dr C.O",
    role: "SCA candidate",
    excerpt:
      "Colleagues are often busy when I am, but with @OSCEGuide I can role play anytime, even at night. A game changer in my SCA prep.",
    highlight: "A game changer",
  },
  {
    name: "Dr Adeleke",
    role: "Passed SCA",
    excerpt:
      "I was hooked as soon as I did the trial. @OSCEGuide was instrumental in my preparation. I passed my exam.",
    highlight: "I passed my exam",
  },
  {
    name: "Dr S",
    role: "Passed SCA",
    excerpt:
      "Structured feedback aligned to SCA marking domains. Support is available 24/7. Highly recommended! I passed my exam!",
    highlight: "I passed my exam!",
  },
  {
    name: "Dr R",
    role: "Passed SCA",
    excerpt:
      "Amazing idea. The AI is fast and responsive. I no longer need to search for a study group. I passed my exam.",
    highlight: "I passed my exam",
  },
  {
    name: "Dr L",
    role: "Passed SCA",
    excerpt:
      "Perfect practice partner, invaluable feedback from @OSCEGuide. AMAZING. I passed my exam!",
    highlight: "I passed my exam!",
  },
  {
    name: "Dr Emmanuel Okojie",
    role: "SCA candidate",
    excerpt:
      "The @OSCEGuide app mirrored real consultation formats. Clear prompts, differentials, and management plans for revision.",
    highlight: "mirrored real consultation formats",
  },
  {
    name: "Dr Zahra",
    role: "SCA candidate",
    excerpt:
      "I started late and tried most sites. @OSCEGuide was by far the best. The AI is really responsive and the cases are excellent.",
    highlight: "by far the best",
  },
];
