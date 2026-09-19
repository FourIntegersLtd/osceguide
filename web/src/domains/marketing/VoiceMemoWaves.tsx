import { VoiceMemoBars } from "./VoiceMemoBars";

export function VoiceMemoWaves() {
  return (
    <div
      className="absolute left-1/2 top-[61%] z-10 -translate-x-1/2 rounded-lg bg-osce-accent px-5 py-2.5 shadow-[0_8px_24px_rgba(37,99,235,0.4)] sm:px-6 sm:py-3"
      aria-hidden
    >
      <VoiceMemoBars />
    </div>
  );
}
