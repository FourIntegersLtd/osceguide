import {
  HiOutlineChatBubbleLeftRight,
  HiOutlineClipboardDocumentList,
  HiOutlineSquare3Stack3D,
  HiOutlineUserGroup,
} from "react-icons/hi2";
import type { IconType } from "react-icons";
import { B2CPanelCard, B2CPanelCardBody, B2CPanelCardHeader } from "@/foundation/ui";
import { Dropdown } from "@/foundation/table";
import { GradeCircle } from "@/capabilities/feedback/GradeCircle";
import type { Competency, CompetencyGroup } from "@/capabilities/feedback/model";

/**
 * Cosmetic only. The old screen drew three fixed cards with three fixed icons;
 * every framework gets the same card here, and one whose domains this map has
 * never heard of gets the generic mark rather than no card.
 */
const GROUP_ICON: Record<string, IconType> = {
  global_skills: HiOutlineChatBubbleLeftRight,
  tasks: HiOutlineClipboardDocumentList,
  relating_to_others: HiOutlineUserGroup,
};

function FeedbackItem({ competency }: { competency: Competency }) {
  return (
    <div className="mb-4 hover:bg-b2c-surface-muted py-6 px-2 rounded-lg transition-colors">
      <div className="flex items-center mb-1">
        {competency.score ? <GradeCircle grade={competency.score} /> : null}
        <span className="text-osce-ink-900 font-medium">{competency.label}</span>
      </div>
      {competency.quote && (
        <div className="ml-9 text-osce-body text-b2c-text-secondary">
          <p className="relative">
            <span className="absolute -left-4 top-0 text-b2c-text-muted">&quot;</span>
            {competency.quote} <span className="text-b2c-text-muted">&quot;</span>
          </p>
        </div>
      )}
      {competency.explanation && (
        <div className="mt-3 p-3 text-osce-body text-b2c-text-secondary bg-osce-accent-muted rounded-md sm:ml-9 sm:mt-4 sm:pl-4">
          <p className="relative italic">{competency.explanation}</p>
        </div>
      )}
    </div>
  );
}

function DomainScores({ competencies }: { competencies: Competency[] }) {
  const green = competencies.filter((item) => item.score === "G").length;
  const amber = competencies.filter((item) => item.score === "A").length;
  const red = competencies.filter((item) => item.score === "R").length;

  return (
    <div className="mt-auto pt-4 border-t border-b2c-border">
      <div className="space-y-3">
        <ScoreRow grade="G" label="Green:" value={green} valueClassName="text-osce-success-text" />
        <ScoreRow grade="A" label="Amber:" value={amber} valueClassName="text-osce-warning-text" />
        <ScoreRow grade="R" label="Red:" value={red} valueClassName="text-osce-danger" />
        <div className="flex justify-between items-center pt-3 border-t border-b2c-border">
          <span className="text-b2c-text-secondary font-medium">Total</span>
          <div className="flex items-center gap-1">
            <span className="text-b2c-text-secondary text-osce-title">{green + amber}</span>
            <span className="text-b2c-text-muted">/</span>
            <span className="text-osce-ink-900 text-osce-title font-bold">
              {competencies.length}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function ScoreRow({
  grade,
  label,
  value,
  valueClassName,
}: {
  grade: "R" | "A" | "G";
  label: string;
  value: number;
  valueClassName: string;
}) {
  return (
    <div className="flex justify-between items-center">
      <div>
        <GradeCircle grade={grade} />
        <span className="text-b2c-text-secondary font-medium">{label}</span>
      </div>
      <span className={`${valueClassName} font-bold`}>{value}</span>
    </div>
  );
}

/**
 * The scored domains, one card each.
 *
 * Driven by whatever groups the payload contained rather than by the SCA's
 * three, so PLAB, CASC, Ortho and anything a new rubric introduces render
 * through this instead of through a copy of it — which is what the retiring
 * client had, four times over.
 */
export function FeedbackDomains({ groups }: { groups: CompetencyGroup[] }) {
  if (groups.length === 0) return null;

  return (
    <Dropdown defaultOpen title="Domains Feedback" icon={<HiOutlineSquare3Stack3D className="w-5 h-5" />}>
      <div className="overflow-y-auto max-h-[90vh] cursor-text">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {groups.map((group) => {
            const Icon = GROUP_ICON[group.key] ?? HiOutlineSquare3Stack3D;
            return (
              <B2CPanelCard key={group.key} className="mt-0 flex flex-col">
                <B2CPanelCardHeader>
                  <Icon className="h-4 w-4" /> {group.label}
                </B2CPanelCardHeader>
                <B2CPanelCardBody className="flex flex-1 flex-col">
                  <div>
                    {group.competencies.map((competency) => (
                      <FeedbackItem key={competency.key} competency={competency} />
                    ))}
                  </div>
                  <DomainScores competencies={group.competencies} />
                </B2CPanelCardBody>
              </B2CPanelCard>
            );
          })}
        </div>

        <div className="mt-8">
          <div className="p-4 bg-osce-warning-bg border border-osce-warning-border rounded-lg">
            <h3 className="text-osce-warning-text font-semibold mb-3 flex items-center gap-2">
              <HiOutlineChatBubbleLeftRight className="w-4 h-4" /> Understanding Your Scores
            </h3>
            <div className="space-y-2 text-osce-body text-osce-warning-text">
              <div className="flex items-center gap-2">
                <GradeCircle grade="G" />
                <span>
                  <strong>Green (G):</strong> Good performance - you demonstrated this skill well
                </span>
              </div>
              <div className="flex items-center gap-2">
                <GradeCircle grade="A" />
                <span>
                  <strong>Amber (A):</strong> Adequate performance - room for improvement but
                  acceptable
                </span>
              </div>
              <div className="flex items-center gap-2">
                <GradeCircle grade="R" />
                <span>
                  <strong>Red (R):</strong> Needs attention - this skill requires focused practice
                </span>
              </div>
              <div className="mt-3 pt-3 border-t border-osce-warning-border">
                <p>
                  <strong>Score Format (e.g., 7/11):</strong> Shows your combined Green + Amber
                  scores out of total skills assessed. Green and Amber both count as
                  &quot;satisfactory&quot; Performance, while Red indicates areas needing
                  improvement.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-4">
          <div className="rounded-lg p-4 bg-osce-accent-muted border border-osce-accent-muted">
            <p className="text-osce-body text-osce-accent-hover text-center font-medium">
              This consultation analysis is for formative training purposes only and cannot be used
              as an indication of performance in the exam.
            </p>
          </div>
        </div>
      </div>
    </Dropdown>
  );
}
