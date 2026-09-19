import { HiOutlineListBullet } from "react-icons/hi2";
import { B2CPanelCard, B2CPanelCardBody, B2CPanelCardHeader } from "@/foundation/ui";
import { Dropdown } from "@/foundation/table";
import type { CompetencyGroup } from "@/capabilities/feedback/model";

function Column({
  title,
  items,
  empty,
  borderClassName,
  titleClassName,
  bullet,
}: {
  title: string;
  items: string[];
  empty: string;
  borderClassName: string;
  titleClassName: string;
  bullet?: string;
}) {
  return (
    <div className={`w-full border-l-4 ${borderClassName} pl-4 lg:w-1/3`}>
      <h4 className={`mb-4 font-medium ${titleClassName}`}>{title}</h4>
      <ul className="space-y-3">
        {items.length > 0 ? (
          items.map((item, index) => (
            <li key={index} className="text-osce-body text-b2c-text-secondary">
              {bullet ? <span className="text-osce-accent-light">{bullet} </span> : null}
              {item}
            </li>
          ))
        ) : (
          <li className="text-osce-body text-b2c-text-secondary">{empty}</li>
        )}
      </ul>
    </div>
  );
}

/**
 * The narrative beside the scores: what went well, what to work on, what to do.
 *
 * The old screen named its three categories in the markup, so a framework with
 * four produced three cards and dropped one. Here each scored group brings its
 * own narrative through the normaliser, which is the pairing the payload
 * already expresses.
 */
export function FeedbackCategories({ groups }: { groups: CompetencyGroup[] }) {
  const withNarrative = groups.filter(
    (group) =>
      group.strengths.length > 0 || group.improvements.length > 0 || group.actions.length > 0,
  );
  if (withNarrative.length === 0) return null;

  return (
    <Dropdown defaultOpen title="Categories Feedback" icon={<HiOutlineListBullet className="h-5 w-5" />}>
      <div className="flex flex-col space-y-4">
        {withNarrative.map((group) => (
          <B2CPanelCard key={group.key} className="mt-0">
            <B2CPanelCardHeader>{group.label}</B2CPanelCardHeader>
            <B2CPanelCardBody>
              <div className="flex flex-col gap-6 lg:flex-row">
                <Column
                  title="Strengths"
                  items={group.strengths}
                  empty="No strengths generated"
                  borderClassName="border-osce-success-icon"
                  titleClassName="text-osce-success-text"
                />
                <Column
                  title="Areas for Improvement"
                  items={group.improvements}
                  empty="No areas for improvement generated"
                  borderClassName="border-osce-danger"
                  titleClassName="text-osce-danger-hover"
                />
                <Column
                  title="Suggested Actions"
                  items={group.actions}
                  empty="No suggested actions generated"
                  borderClassName="border-osce-accent-light"
                  titleClassName="text-osce-accent-hover"
                  bullet="→"
                />
              </div>
            </B2CPanelCardBody>
          </B2CPanelCard>
        ))}
      </div>
    </Dropdown>
  );
}
