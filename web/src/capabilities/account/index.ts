export { default as Login } from "@/capabilities/account/Login";
export { default as Register } from "@/capabilities/account/Register";
export { default as ForgotPassword } from "@/capabilities/account/ForgotPassword";
export { default as ConfirmEmail } from "@/capabilities/account/ConfirmEmail";
export { default as ResetPassword } from "@/capabilities/account/ResetPassword";
export { default as AuthShell } from "@/capabilities/account/AuthShell";
export { ChangePasswordRequired } from "@/capabilities/account/ChangePasswordRequired";
export { default as ChooseExam } from "@/capabilities/account/ChooseExam";
export { default as AuthFormField } from "@/capabilities/account/AuthFormField";
export { accountCapability } from "@/capabilities/account/capability";

/* The settings screen and its tabs. `Settings` is what the route mounts. */
export { Settings, type SettingsTab } from "@/capabilities/account/Settings";
export { default as ProfilePanel } from "@/capabilities/account/settings/ProfilePanel";
export { default as CvPanel } from "@/capabilities/account/settings/CvPanel";
export { default as PaymentsPanel } from "@/capabilities/account/settings/PaymentsPanel";
export { default as ReferralsPanel } from "@/capabilities/account/settings/ReferralsPanel";
export { default as ReferralDetail } from "@/capabilities/account/settings/ReferralDetail";
export { default as ChangePassword } from "@/capabilities/account/settings/ChangePassword";
export { default as PlanPicker } from "@/capabilities/account/settings/PlanPicker";

/*
 * The two Stripe return pages. Exported rather than mounted: they answer a
 * fixed address the backend puts in `success_url` and `cancel_url`, which is
 * outside a workspace and so outside this capability's one route. Their route
 * files are `app/billing/complete` and `app/(public)/pricing`.
 */
export { default as PaymentReturn, CheckoutCancelled } from "@/capabilities/account/PaymentReturn";

/* Served by `GET /me/achievements`; `AchievementsLive` is the caller. */
export { default as Achievements } from "@/capabilities/account/Achievements";
export { default as ExamWishes } from "@/capabilities/account/ExamWishes";
