"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  HiOutlineArrowPath,
  HiOutlineSquare3Stack3D,
  HiOutlineXCircle,
} from "react-icons/hi2";
import {
  Alert,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardFooter,
  B2CPanelCardHeader,
  ModalCallout,
  ModalContent,
  ModalHelper,
  ModalPrimaryButton,
  ModalTitle,
  cn,
  productTokens,
} from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import type { LibraryStation } from "@/capabilities/stations";
import { createSet } from "@/domains/train/api";
import { incompleteVersionIds } from "@/domains/train/mocks/model";
import { examByCode, type MockWorkspace } from "@/domains/train/mocks/useMockWorkspace";

/**
 * Build a focused session out of stations you started and did not finish.
 *
 * The old client asked the backend which stations those were
 * (`/api/attempted_incomplete_stations`). The set list already carries every
 * entry with its attempt count, so the question is answered from what is
 * already loaded — and it stays right for a station whose attempts ran out in
 * one session but not another, which the endpoint got wrong.
 */
export function CombineStations({
  workspace,
  onCreated,
}: {
  workspace: MockWorkspace;
  onCreated: () => void;
}) {
  const router = useRouter();
  const { hrefFor } = useSurface();
  const [mockName, setMockName] = useState("");
  const [selected, setSelected] = useState<LibraryStation[]>([]);
  const [stationSearch, setStationSearch] = useState("");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorText, setErrorText] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const availableStations = useMemo(() => {
    const byVersion = new Map(workspace.stations.map((station) => [station.version_id, station]));
    const limits = new Map(workspace.exams.map((exam) => [exam.code, exam.station_attempt_limit]));
    const ids = new Set<string>();
    for (const set of workspace.sets) {
      const limit = limits.get(set.exam_code) ?? 3;
      for (const id of incompleteVersionIds([set], limit)) ids.add(id);
    }
    return [...ids].map((id) => byVersion.get(id)).filter((item): item is LibraryStation => !!item);
  }, [workspace]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // One set is one exam's stations; mixing them would have no clock.
  const pinnedExamCode = selected[0]?.exam_code ?? null;

  const filteredStations = availableStations.filter((station) => {
    const notSelected = !selected.some((item) => item.version_id === station.version_id);
    const matches = station.title.toLowerCase().includes(stationSearch.toLowerCase());
    const sameExam = pinnedExamCode === null || pinnedExamCode === station.exam_code;
    return notSelected && matches && sameExam;
  });

  const handleCreate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pinnedExamCode === null) {
      setErrorText("Select at least one attempted station.");
      return;
    }
    setIsCreating(true);
    setErrorText(null);
    try {
      const set = await createSet({
        name: mockName,
        examCode: pinnedExamCode,
        stationVersionIds: selected.map((station) => station.version_id),
      });
      setMockName("");
      setSelected([]);
      setSuccessMessage("Combined session created successfully");
      onCreated();
      router.push(hrefFor(`/mocks/${set.id}`));
    } catch (cause) {
      setErrorText(errorMessage(cause));
    } finally {
      setIsCreating(false);
    }
  };

  const selectedExam = examByCode(workspace, pinnedExamCode ?? "");

  return (
    <ModalContent className="max-w-2xl space-y-3 pb-24">
      <div>
        <ModalTitle>Combine Attempted Stations</ModalTitle>
        <ModalHelper>
          Create a focused practice session by combining stations you have attempted across several
          mocks.
        </ModalHelper>
      </div>

      {availableStations.length === 0 ? (
        <ModalCallout label="Note" className="mt-0">
          This feature becomes available after you attempt some mocks. You can then create a custom
          session from stations you have already tried.
        </ModalCallout>
      ) : (
        <form onSubmit={handleCreate} className="space-y-3">
          <B2CPanelCard className="mt-0">
            <B2CPanelCardHeader>
              <HiOutlineSquare3Stack3D className="h-4 w-4 text-osce-accent" aria-hidden />
              Session details
            </B2CPanelCardHeader>
            <B2CPanelCardBody className="space-y-5">
              <div>
                <label htmlFor="mock_name" className={productTokens.b2cFieldLabel}>
                  Session name
                </label>
                <input
                  id="mock_name"
                  required
                  value={mockName}
                  onChange={(event) => setMockName(event.target.value)}
                  className={cn(productTokens.b2cInputBase, "mt-1.5")}
                  placeholder="Enter session name"
                />
              </div>

              <div ref={dropdownRef} className="relative">
                <label className={productTokens.b2cFieldLabel}>Select attempted stations</label>
                <input
                  type="text"
                  placeholder="Search stations..."
                  value={stationSearch}
                  onChange={(event) => setStationSearch(event.target.value)}
                  onFocus={() => setIsDropdownOpen(true)}
                  className={cn(productTokens.b2cInputBase, "mt-1.5")}
                />
                {isDropdownOpen && filteredStations.length > 0 ? (
                  <div className="absolute z-10 mt-1.5 max-h-60 w-full overflow-auto rounded-md border border-b2c-border bg-osce-surface">
                    {filteredStations.map((station) => (
                      <button
                        key={station.version_id}
                        type="button"
                        className={productTokens.b2cDropdownItem}
                        onClick={() => {
                          setSelected((prev) => [...prev, station]);
                          setStationSearch("");
                          setIsDropdownOpen(false);
                        }}
                      >
                        {station.title}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            </B2CPanelCardBody>

            {selected.length > 0 ? (
              <div className="border-t border-b2c-border">
                <div className={productTokens.b2cPanelSubheader}>
                  Selected stations ({selected.length})
                  {selectedExam ? ` · ${selectedExam.name}` : ""}
                </div>
                <div className="divide-y divide-b2c-border">
                  {selected.map((station) => (
                    <div
                      key={station.version_id}
                      className="flex items-center justify-between gap-3 px-4 py-3"
                    >
                      <span className="min-w-0 text-osce-body text-osce-ink-900">
                        {station.title}
                      </span>
                      <button
                        type="button"
                        onClick={() =>
                          setSelected((prev) =>
                            prev.filter((item) => item.version_id !== station.version_id),
                          )
                        }
                        className="shrink-0 text-b2c-text-muted transition hover:text-osce-danger"
                        aria-label={`Remove ${station.title}`}
                      >
                        <HiOutlineXCircle className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {errorText ? (
              <div className="border-t border-b2c-border px-4 pt-3">
                <Alert tone="danger">{errorText}</Alert>
              </div>
            ) : null}
            {successMessage ? (
              <div className="border-t border-b2c-border px-4 pt-3">
                <Alert tone="success">{successMessage}</Alert>
              </div>
            ) : null}

            <B2CPanelCardFooter>
              <ModalPrimaryButton type="submit" disabled={isCreating} className="gap-2">
                {isCreating ? (
                  <>
                    <HiOutlineArrowPath className="h-4 w-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  "Create Session"
                )}
              </ModalPrimaryButton>
            </B2CPanelCardFooter>
          </B2CPanelCard>
        </form>
      )}
    </ModalContent>
  );
}
