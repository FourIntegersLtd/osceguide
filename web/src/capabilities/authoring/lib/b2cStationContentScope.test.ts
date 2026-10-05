import assert from "node:assert/strict";
import { test } from "node:test";
import { contentSliceForSection, mergeSectionIntoContent } from "./b2cStationContentScope";

const doctorInformation = {
  id: "doctor_information",
  blocks: [
    { id: "doctor_patient_biodata", type: "longText" as const, label: "Biodata" },
    { id: "doctor_photos", type: "media" as const, label: "Photos" },
  ],
};

test("a b2c section's values are read and written back under their stored keys", () => {
  const content = { station_id: "sta-1", doctor_information: { patient_biodata: "Jo, 35", photos: ["a.png"] } };

  const slice = contentSliceForSection(content, doctorInformation);
  assert.equal(slice.doctor_patient_biodata, "Jo, 35");
  assert.deepEqual(slice.doctor_photos, ["a.png"]);

  const merged = mergeSectionIntoContent(content, doctorInformation, { ...slice, doctor_photos: ["a.png", "b.png"] });
  assert.deepEqual(merged, {
    station_id: "sta-1",
    doctor_information: { patient_biodata: "Jo, 35", photos: ["a.png", "b.png"] },
  });
});

test("a block with nothing stored yet is written under its own id", () => {
  const merged = mergeSectionIntoContent({ doctor_information: {} }, doctorInformation, { doctor_photos: ["a.png"] });
  assert.deepEqual(merged, { doctor_information: { doctor_photos: ["a.png"] } });
});

test("a station drafted against its template keeps its values flat, read and written by block id", () => {
  const content = { doctor_patient_biodata: "Jo, 35", doctor_photos: [] };

  const slice = contentSliceForSection(content, doctorInformation);
  assert.equal(slice.doctor_patient_biodata, "Jo, 35");

  const merged = mergeSectionIntoContent(content, doctorInformation, { ...slice, doctor_patient_biodata: "Jo, 36" });
  assert.deepEqual(merged, { doctor_patient_biodata: "Jo, 36", doctor_photos: [] });
});
