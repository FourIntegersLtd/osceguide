// The two practice partners of the live-practice illustration, lifted from the approved design.
// Decorative: the figure that holds them is labelled as a whole.

const SVG_PROPS = { viewBox: "0 0 200 240", "aria-hidden": true, className: "h-full w-full object-contain" } as const;

export function DoctorAvatar() {
  return (
    <svg {...SVG_PROPS}>
      <ellipse cx="61" cy="116" rx="7" ry="10" fill="#A86F47"/><ellipse cx="139" cy="116" rx="7" ry="10" fill="#A86F47"/>
      <path d="M18 240c4-44 36-68 82-68s78 24 82 68z" fill="#FFFFFF"/>
      <path d="M80 174l20 38 20-38z" fill="#CDDCF8"/>
      <path d="M85 148h30v26a15 15 0 0 1-30 0z" fill="#A86F47"/>
      <ellipse cx="100" cy="112" rx="39" ry="45" fill="#BC8257"/>
      <path d="M60 108c-6-38 18-60 44-58 28 2 42 22 37 56-5-14-13-22-25-25-18 10-36 12-56 27z" fill="#22263A"/>
      <path d="M77 103q9-5 17 0M106 103q9-5 17 0" stroke="#22263A" strokeWidth="3.5" fill="none" strokeLinecap="round"/>
      <circle cx="86" cy="116" r="4" fill="#22263A"/><circle cx="114" cy="116" r="4" fill="#22263A"/>
      <path d="M97 122q3 8-2 10" stroke="#8E5A37" strokeWidth="2.5" fill="none" strokeLinecap="round"/>
      <path d="M87 138q13 10 26 0" stroke="#6B3322" strokeWidth="3.5" fill="none" strokeLinecap="round"/>
      <path d="M70 180l30 60M130 180l-30 60" stroke="#DCE1EA" strokeWidth="3"/>
      <path d="M82 176c-8 24-2 40 18 44M118 176c8 24 2 40-18 44" stroke="#2B3445" strokeWidth="4" fill="none" strokeLinecap="round"/>
      <circle cx="100" cy="222" r="7" fill="#94A3B8" stroke="#2B3445" strokeWidth="3"/>
    </svg>
  );
}

export function PatientAvatar() {
  return (
    <svg {...SVG_PROPS}>
      <path d="M50 126c-6-52 18-80 50-80s56 28 50 80c4 32-2 50-10 62H60c-8-12-14-30-10-62z" fill="#5A3825"/>
      <path d="M18 240c4-44 36-68 82-68s78 24 82 68z" fill="#D9A86C"/>
      <path d="M78 176q22 16 44 0" stroke="#C4904F" strokeWidth="6" fill="none" strokeLinecap="round"/>
      <path d="M86 148h28v24a14 14 0 0 1-28 0z" fill="#DDA27A"/>
      <ellipse cx="100" cy="112" rx="37" ry="44" fill="#EBB892"/>
      <path d="M62 112c0-34 16-54 40-54 22 0 38 16 36 44-14-4-30-16-38-30-6 18-20 32-38 40z" fill="#5A3825"/>
      <path d="M78 104q8-6 15-2M107 102q7-4 15 2" stroke="#3E2618" strokeWidth="3.5" fill="none" strokeLinecap="round"/>
      <circle cx="87" cy="116" r="4" fill="#3E2618"/><circle cx="113" cy="116" r="4" fill="#3E2618"/>
      <path d="M98 122q3 7-2 9" stroke="#C98763" strokeWidth="2.5" fill="none" strokeLinecap="round"/>
      <path d="M90 140q10-4 20 0" stroke="#9E4A3A" strokeWidth="3.5" fill="none" strokeLinecap="round"/>
    </svg>
  );
}
