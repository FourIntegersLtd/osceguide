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
  /** Line numbers (1-based, header included) that carried no usable address. */
  skippedLines: number[];
  error: string | null;
}

const EMAIL_KEYS = ["email", "emailaddress", "e-mail"];
const FIRST_KEYS = ["firstname", "first", "forename", "givenname"];
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
export function splitCsvLine(line: string): string[] {
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
    } else if (char === ",") {
      fields.push(value);
      value = "";
    } else {
      value += char;
    }
  }
  fields.push(value);
  return fields.map((field) => field.trim());
}

function pick(row: Record<string, string>, keys: string[]): string | null {
  for (const key of keys) {
    const value = row[key];
    if (value != null && value.trim() !== "") return value.trim();
  }
  return null;
}

export function parseTraineeCsv(text: string): CsvParse {
  const lines = text
    .split(/\r\n|\r|\n/)
    .map((line) => line.trimEnd())
    .filter((line, index) => index === 0 || line.trim() !== "");

  const header = lines[0] ?? "";
  if (header.trim() === "") {
    return { rows: [], skippedLines: [], error: "That file is empty." };
  }

  const headers = splitCsvLine(header).map(normalise);
  if (!headers.some((header) => EMAIL_KEYS.includes(header))) {
    return {
      rows: [],
      skippedLines: [],
      error: "The first row must name the columns, and one of them must be `email`.",
    };
  }

  const rows: CsvRow[] = [];
  const skippedLines: number[] = [];

  for (let index = 1; index < lines.length; index += 1) {
    const cells = splitCsvLine(lines[index] ?? "");
    const record: Record<string, string> = {};
    headers.forEach((header, column) => {
      record[header] = cells[column] ?? "";
    });

    const email = pick(record, EMAIL_KEYS);
    if (!email || !email.includes("@")) {
      skippedLines.push(index + 1);
      continue;
    }

    const first = pick(record, FIRST_KEYS);
    const last = pick(record, LAST_KEYS);
    rows.push({
      email: email.toLowerCase(),
      firstName: first,
      lastName: last,
      cohort: pick(record, COHORT_KEYS),
    });
  }

  if (rows.length === 0) {
    return { rows, skippedLines, error: "No rows in that file had an email address." };
  }
  return { rows, skippedLines, error: null };
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
