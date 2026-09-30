import { ModalContent, ModalHeader, ModalHelper } from "@/foundation/ui";

/** The note somebody sees in the week of their exam. */
export default function ExamWishes() {
  return (
    <ModalContent className="mx-auto max-w-md text-center">
      <ModalHeader
        title="Good luck this week"
        description="Thanks for using OSCE Guide to prepare."
        className="text-center"
      />
      <ModalHelper className="mt-2">
        We&apos;re rooting for you. Get in touch if we can help before your exam.
      </ModalHelper>
      <p className="mt-4 text-osce-meta text-ink-muted">
        You&apos;ve put the work in. Go show what you can do.
      </p>
    </ModalContent>
  );
}
