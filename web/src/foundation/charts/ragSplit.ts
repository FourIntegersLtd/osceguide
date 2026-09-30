/**
 * One row's red/amber/green counts as percentages to one decimal place that
 * add up to exactly 100. Rounding each share on its own can make 100.1 (2/7,
 * 2/7, 3/7), and the chart then stretches its axis past 100%, so green takes
 * whatever the other two leave.
 */
export function percentSplit(red: number, amber: number, green: number): { red: number; amber: number; green: number } {
  const total = red + amber + green;
  const redShare = Math.round((red / total) * 1000) / 10;
  const amberShare = Math.round((amber / total) * 1000) / 10;
  return { red: redShare, amber: amberShare, green: Math.round((100 - redShare - amberShare) * 10) / 10 };
}
