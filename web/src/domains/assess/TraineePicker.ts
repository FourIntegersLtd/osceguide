/** The rows and sets the candidate picker works over. */
export type TraineeRow = {
  id: string;
  user_id: string | null;
  email: string;
  first_name: string | null;
  last_name: string | null;
  cohort_id?: string | null;
};

/** A named set of roster ids the picker can tick in one go. */
export type PickerSet = { id: string; label: string; count?: number; loadMemberIds: () => Promise<string[]> };
