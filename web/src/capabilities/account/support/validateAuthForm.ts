import { z } from "zod";

/**
 * Single source of truth for register, reset and change password. It must equal
 * platform-api's MIN_PASSWORD_LENGTH (features/identity/domain.py); when it said 8,
 * the form accepted passwords the server then refused as `weak_password`.
 */
export const PASSWORD_MIN_LENGTH = 12;
export const PASSWORD_HINT = `At least ${PASSWORD_MIN_LENGTH} characters.`;

export const emailSchema = z
  .string()
  .trim()
  .min(1, "Enter your email address")
  .email("Enter a valid email address");

export const passwordSchema = z
  .string()
  .min(1, "Enter a password")
  .min(PASSWORD_MIN_LENGTH, `Use at least ${PASSWORD_MIN_LENGTH} characters`);

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, "Enter your password"),
});

export const registerSchema = z
  .object({
    username: z
      .string()
      .trim()
      .min(3, "Use at least 3 characters")
      .max(50, "Use fewer than 50 characters"),
    email: emailSchema,
    password: passwordSchema,
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
  });

export const resetPasswordSchema = z
  .object({
    password: passwordSchema,
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
  });

export type FieldErrors<TField extends string = string> = Partial<
  Record<TField, string>
>;

export type ValidationResult<T, TField extends string> =
  | { success: true; data: T; fieldErrors: FieldErrors<TField> }
  | { success: false; data: null; fieldErrors: FieldErrors<TField> };

/** First error per field, keyed by the field name, so forms can render inline. */
export function validateWith<T, TField extends string>(
  schema: z.ZodType<T>,
  values: unknown,
): ValidationResult<T, TField> {
  const result = schema.safeParse(values);
  if (result.success) {
    return { success: true, data: result.data, fieldErrors: {} };
  }
  const fieldErrors: FieldErrors<TField> = {};
  for (const issue of result.error.issues) {
    const field = String(issue.path[0] ?? "") as TField;
    if (field && !fieldErrors[field]) fieldErrors[field] = issue.message;
  }
  return { success: false, data: null, fieldErrors };
}
