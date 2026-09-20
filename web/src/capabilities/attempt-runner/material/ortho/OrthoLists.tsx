"use client";

import { b2cReadingTones, b2cSectionTitle, type B2CReadingToneKey } from "@/foundation/ui/productTokens";
import type { WardPatient, TheatreItem } from "./model";

export const PatientList = ({
  patients,
  title,
  bgColor,
  showNotes = true,
}: {
  patients: WardPatient[];
  title: string;
  bgColor: B2CReadingToneKey;
  showNotes?: boolean;
}) => (
  <div className={`${b2cReadingTones[bgColor].card} rounded-osce-lg border overflow-hidden`}>
    {" "}
    <div className="p-4 border-b">
      {" "}
      <h4 className={b2cSectionTitle}>{title}</h4>{" "}
    </div>{" "}
    <div className="overflow-x-auto">
      {" "}
      <table className="w-full">
        {" "}
        <thead className="bg-b2c-surface-muted border-b">
          {" "}
          <tr>
            {" "}
            <th className="px-4 py-3 text-left text-osce-caption font-medium text-b2c-text-secondary uppercase tracking-wider">
              Patient
            </th>{" "}
            <th className="px-4 py-3 text-left text-osce-caption font-medium text-b2c-text-secondary uppercase tracking-wider">
              Age/Gender
            </th>{" "}
            <th className="px-4 py-3 text-left text-osce-caption font-medium text-b2c-text-secondary uppercase tracking-wider">
              Summary
            </th>{" "}
            {showNotes && (
              <th className="px-4 py-3 text-left text-osce-caption font-medium text-b2c-text-secondary uppercase tracking-wider">
                Notes
              </th>
            )}{" "}
          </tr>{" "}
        </thead>{" "}
        <tbody className="bg-white divide-y divide-b2c-border">
          {" "}
          {patients.map((patient, idx) => (
            <tr key={idx} className="hover:bg-b2c-surface-muted">
              {" "}
              <td className="px-4 py-3 text-osce-body font-medium text-osce-ink-900">
                #{patient.number}
              </td>{" "}
              <td className="px-4 py-3 text-osce-body text-b2c-text-secondary">
                {patient.age}yo {patient.gender}
              </td>{" "}
              <td className="px-4 py-3 text-osce-body text-b2c-text-secondary">
                {patient.summary}
              </td>{" "}
              {showNotes && (
                <td className="px-4 py-3 text-osce-body text-b2c-text-secondary">
                  {" "}
                  {(patient.notes?.length ?? 0) > 0 ? (
                    <ul className="list-disc list-inside space-y-1">
                      {" "}
                      {patient.notes?.map((note: string, noteIdx: number) => (
                        <li key={noteIdx}>{note}</li>
                      ))}{" "}
                    </ul>
                  ) : (
                    <span className="text-b2c-text-muted">-</span>
                  )}{" "}
                </td>
              )}{" "}
            </tr>
          ))}{" "}
        </tbody>{" "}
      </table>{" "}
    </div>{" "}
  </div>
);
export const TheatreList = ({
  items,
  title,
  tone,
}: {
  items: TheatreItem[];
  title: string;
  tone: B2CReadingToneKey;
}) => (
  <div className={`${b2cReadingTones[tone].card} ${b2cReadingTones[tone].title} p-4 rounded-osce-lg border`}>
    {" "}
    <h4 className={`${b2cSectionTitle} mb-3`}>{title}</h4>{" "}
    <div className="space-y-3">
      {" "}
      {items.map((item, idx) => (
        <div key={idx} className="bg-white p-3 rounded border">
          {" "}
          <div className="font-medium text-osce-ink-900">
            {item.title}
          </div>{" "}
          <ul className="list-disc list-inside text-osce-body text-b2c-text-secondary mt-2 space-y-1">
            {" "}
            {item.reasons.map((reason: string, reasonIdx: number) => (
              <li key={reasonIdx}>{reason}</li>
            ))}{" "}
          </ul>{" "}
        </div>
      ))}{" "}
    </div>{" "}
  </div>
);
