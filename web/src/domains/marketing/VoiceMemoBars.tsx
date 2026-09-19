const BAR_HEIGHTS = [
  5, 9, 14, 20, 16, 22, 12, 18, 10, 15, 8, 13, 19, 11, 17, 14, 9, 6, 12, 21, 15,
  10, 7,
];

type VoiceMemoBarsProps = {
  barClassName?: string;
  gapClassName?: string;
  heightClassName?: string;
  size?: "default" | "compact";
};

export function VoiceMemoBars({
  barClassName = "w-[3px] rounded-full bg-white/95 sm:w-1",
  gapClassName = "gap-[3px] sm:gap-1",
  heightClassName = "h-7 sm:h-8",
  size = "default",
}: VoiceMemoBarsProps) {
  const heightScale = size === "compact" ? 0.65 : 1;
  const barsClassName =
    size === "compact"
      ? `${heightClassName} showcase-voice-bars showcase-voice-bars--compact`
      : heightClassName;

  return (
    <div className={`flex items-center justify-center ${barsClassName} ${gapClassName}`}>
      {BAR_HEIGHTS.map((height, index) => (
        <span
          key={index}
          className={`voice-memo-bar ${barClassName}`}
          style={{
            height: `${Math.round(height * heightScale)}px`,
            animationDelay: `${index * 0.06}s`,
          }}
        />
      ))}
    </div>
  );
}
