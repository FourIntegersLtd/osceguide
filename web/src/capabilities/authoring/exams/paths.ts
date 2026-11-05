/** Exam screens outside the tabbed `/authoring/{section}` shell. */

type HrefFor = (path: string) => string;

export const examsListPath = (hrefFor: HrefFor) => `${hrefFor("/authoring")}/exams`;
export const examNewPath = (hrefFor: HrefFor) => `${examsListPath(hrefFor)}/new`;
export const examDetailPath = (hrefFor: HrefFor, examId: string) => `${examsListPath(hrefFor)}/${encodeURIComponent(examId)}`;
export const examSettingsPath = (hrefFor: HrefFor, examId: string) => `${examDetailPath(hrefFor, examId)}/settings`;
export const examResumePath = (hrefFor: HrefFor, examId: string) => `${examNewPath(hrefFor)}?exam=${encodeURIComponent(examId)}`;
