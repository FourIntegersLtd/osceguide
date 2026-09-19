/** * Formats seconds into MM:SS format * @param seconds - Total seconds to format * @returns Formatted time string (e.g., "5:30") */
export function formatTime(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
}
