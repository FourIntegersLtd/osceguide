import { FiChevronDown } from "react-icons/fi";

export type AccordionItem = { title: string; body: string };

/** Native `<details>` rows with a rotating chevron. The caller's class strings set the layout and type size. */
export function Accordion({ items, openFirst = false, className = "", itemClassName = "", summaryClassName = "", bodyClassName = "" }: { items: readonly AccordionItem[]; openFirst?: boolean; className?: string; itemClassName?: string; summaryClassName?: string; bodyClassName?: string }) {
  return (
    <div className={className}>
      {items.map((item, i) => (
        <details key={item.title} open={openFirst && i === 0} className={`group ${itemClassName}`}>
          <summary className={`flex cursor-pointer list-none items-center justify-between gap-4 font-semibold text-site-ink [&::-webkit-details-marker]:hidden ${summaryClassName}`}>
            {item.title}
            <FiChevronDown aria-hidden className="shrink-0 transition-transform group-open:rotate-180" />
          </summary>
          <p className={`leading-relaxed text-site-body ${bodyClassName}`}>{item.body}</p>
        </details>
      ))}
    </div>
  );
}
