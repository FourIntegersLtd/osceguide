"use client";

import Image from "next/image";

const DOCTOR_IMAGE = "/images/landing/hero-doctor.png";
const PATIENT_IMAGE = "/images/landing/practice-patient.jpg";

function ParticipantPhoto({
  src,
  alt,
  label,
  objectPosition = "50% 20%",
}: {
  src: string;
  alt: string;
  label: string;
  objectPosition?: string;
}) {
  return (
    <div className="min-w-0 flex-1">
      <div className="relative aspect-[4/3] overflow-hidden rounded-[var(--landing-radius-card,0.5rem)] border border-landing-warm bg-landing-card-muted">
        <Image
          src={src}
          alt={alt}
          fill
          quality={90}
          className="object-cover"
          style={{ objectPosition }}
          sizes="(max-width: 640px) 44vw, (max-width: 1280px) 280px, 400px"
        />
      </div>
      <p className="mt-2 text-center font-landing-body text-xs text-b2c-text-secondary">
        {label}
      </p>
    </div>
  );
}

export function PracticeColleaguesShowcase() {
  return (
    <div className="rounded-[var(--landing-radius-panel,0.75rem)] border border-landing-warm bg-landing-card p-5 shadow-landing-soft sm:p-6">
      <div className="flex gap-3 sm:gap-4">
        <ParticipantPhoto
          src={DOCTOR_IMAGE}
          alt="Doctor"
          label="Doctor"
          objectPosition="50% 15%"
        />
        <ParticipantPhoto
          src={PATIENT_IMAGE}
          alt="Patient"
          label="Patient"
        />
      </div>

      <div className="mt-6 grid gap-6 border-t border-landing-hairline pt-6 sm:grid-cols-2 sm:gap-8">
        <div>
          <p className="font-landing-body text-xs font-medium text-osce-accent">
            Patient problem
          </p>
          <p className="mt-2 font-landing-body text-sm leading-relaxed text-landing-ink-body">
            You are Oliver, 15, with headaches for three weeks. You are worried
            something is wrong, but you do not want to worry your dad.
          </p>
        </div>
        <div>
          <p className="font-landing-body text-xs font-medium text-b2c-text-secondary">
            Doctor prompt
          </p>
          <p className="mt-2 font-landing-body text-sm leading-relaxed text-landing-ink-body">
            Oliver Wilson, 15. No prior headache visits. Childhood asthma
            resolved. Lives with father and stepmother.
          </p>
        </div>
      </div>
    </div>
  );
}
