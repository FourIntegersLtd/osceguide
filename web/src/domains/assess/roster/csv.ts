/**
 * The spreadsheet import, parsed in the browser.
 *
 * The API takes rows of JSON rather than a file, so the file is read here.
 * That is the same division the old client had — it posted a parsed list too
 * — but the parsing lived inside the upload handler, quoted fields were split
 * on every comma, and a header called `Email ` with a trailing space silently
 * produced a column of empty addresses. This is that job, extracted, with a
 * test.
 *
 * The recognised headers come from the old import screen's own instructions,
 * so a file written for that screen still imports here.
 */

export interface CsvRow {
  email: string;
  firstName: string | null;
  lastName: string | null;
  cohort: string | null;
}

export interface CsvParse {
  rows: CsvRow[];
  /** File line numbers (1-based, header and blank lines counted) whose address cell was empty. */
  skippedLines: number[];
  /** File line numbers whose address cell had text but no `@`. */
  invalidLines: number[];
  /** File line numbers repeating an address already taken from an earlier line. */
  duplicateLines: number[];
  error: string | null;
}

const EMAIL_KEYS = ["email", "emailaddress", "e-mail"];
const FIRST_KEYS = ["firstname", "first", "forename", "givenname"];
const NAME_KEYS = ["name", "fullname"];
const LAST_KEYS = ["lastname", "last", "surname", "familyname"];
const COHORT_KEYS = ["cohort", "group"];

/** Header names are matched case- and punctuation-insensitively. */
function normalise(header: string): string {
  return header.trim().toLowerCase().replace(/[\s_]/g, "");
}

/**
 * One line of CSV, quotes honoured.
 *
 * `"Khan, Amina",a@b.com` is two fields, and a doubled quote inside a quoted
 * field is one literal quote. Splitting on commas — which is what the old
 * importer did — turns that row into three fields and shifts every column
 * after it.
 */
export function splitCsvLine(line: string, delimiter = ","): string[] {
  const fields: string[] = [];
  let value = "";
  let quoted = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (quoted) {
      if (char === '"') {
        if (line[index + 1] === '"') {
          value += '"';
          index += 1;
        } else {
          quoted = false;
        }
      } else {
        value += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === delimiter) {
      fields.push(value);
      value = "";
    } else {
      value += char;
    }
  }
  fields.push(value);
  return fields.map((field) => field.trim());
}

/** Comma, semicolon or tab, whichever splits the header row into the most columns. */
function detectDelimiter(header: string): string {
  return [",", ";", "\t"].reduce((best, candidate) =>
    splitCsvLine(header, candidate).length > splitCsvLine(header, best).length ? candidate : best,
  );
}

/** The file's lines, trailing space trimmed. Blank lines are dropped but every line keeps its file number. */
export function numberedLines(text: string): { text: string; number: number }[] {
  return text
    .split(/\r\n|\r|\n/)
    .map((line, index) => ({ text: line.trimEnd(), number: index + 1 }))
    .filter((line, index) => index === 0 || line.text.trim() !== "");
}

/** Whether the header row names an email column. */
export function hasEmailColumn(headers: string[]): boolean {
  return headers.some((entry) => EMAIL_KEYS.includes(entry));
}

/** An address cell is usable, empty (a skipped line) or text with no `@` (an invalid one). */
export function classifyAddress(cell: string | null | undefined): "ok" | "skipped" | "invalid" {
  if (!cell) return "skipped";
  return cell.includes("@") ? "ok" : "invalid";
}

function pick(row: Record<string, string>, keys: string[]): string | null {
  for (const key of keys) {
    const value = row[key];
    if (value != null && value.trim() !== "") return value.trim();
  }
  return null;
}

export function parseTraineeCsv(text: string): CsvParse {
  const lines = numberedLines(text.replace(/^\uFEFF/, ""));

  const header = lines[0]?.text ?? "";
  if (header.trim() === "") {
    return { rows: [], skippedLines: [], invalidLines: [], duplicateLines: [], error: "That file is empty." };
  }

  const delimiter = detectDelimiter(header);
  const headers = splitCsvLine(header, delimiter).map(normalise);
  if (!hasEmailColumn(headers)) {
    return {
      rows: [],
      skippedLines: [],
      invalidLines: [],
      duplicateLines: [],
      error: `The first row must name the columns, and one of them must be \`email\` (found: ${headers.filter(Boolean).join(", ") || "nothing"}).`,
    };
  }

  const rows: CsvRow[] = [];
  const skippedLines: number[] = [];
  const invalidLines: number[] = [];
  const duplicateLines: number[] = [];
  const seen = new Set<string>();

  for (let index = 1; index < lines.length; index += 1) {
    const cells = splitCsvLine(lines[index]?.text ?? "", delimiter);
    const record: Record<string, string> = {};
    headers.forEach((header, column) => {
      record[header] = cells[column] ?? "";
    });

    const email = pick(record, EMAIL_KEYS);
    const lineNumber = lines[index]?.number ?? index + 1;
    const verdict = classifyAddress(email);
    if (verdict !== "ok" || !email) {
      (verdict === "skipped" ? skippedLines : invalidLines).push(lineNumber);
      continue;
    }

    if (seen.has(email.toLowerCase())) {
      duplicateLines.push(lineNumber);
      continue;
    }
    seen.add(email.toLowerCase());

    let first = pick(record, FIRST_KEYS);
    let last = pick(record, LAST_KEYS);
    const full = first || last ? null : pick(record, NAME_KEYS);
    if (full) {
      const space = full.indexOf(" ");
      first = space === -1 ? full : full.slice(0, space);
      last = space === -1 ? null : full.slice(space + 1).trim() || null;
    }
    rows.push({
      email: email.toLowerCase(),
      firstName: first,
      lastName: last,
      cohort: pick(record, COHORT_KEYS),
    });
  }

  if (rows.length === 0) {
    return { rows, skippedLines, invalidLines, duplicateLines, error: "No rows in that file had an email address." };
  }
  return { rows, skippedLines, invalidLines, duplicateLines, error: null };
}

/** Why the backend skipped a row, in words an administrator can act on. */
export function skipReason(code: string): string {
  switch (code) {
    case "duplicate":
    case "trainee_exists":
      return "already on the roster";
    case "invalid_email":
      return "not a usable email address";
    default:
      return code.replace(/_/g, " ");
  }
}
