import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  formatThresholdsForInput,
  parseThresholdsInput,
  pilotUpdateFromForm,
} from "@/capabilities/staff-growth/bmj/pilotForm";

describe("pilot settings form", () => {
  it("reads pounds as whole pence and drops what is not a number", () => {
    assert.deepEqual(parseThresholdsInput("500, 1000 ,x, 2500.50"), [50000, 100000, 250050]);
    assert.equal(formatThresholdsForInput([50000, 100000]), "500, 1000");
  });

  it("resets alert history only when the thresholds changed", () => {
    assert.deepEqual(pilotUpdateFromForm("0.40", "500, 1000", [50000, 100000]), {
      cost_per_click_pence: 40,
      spend_alert_thresholds_pence: [50000, 100000],
      reset_spend_alerts: false,
    });
    assert.equal(pilotUpdateFromForm("0.40", "500, 2000", [50000, 100000])?.reset_spend_alerts, true);
  });

  it("refuses a rate that is not a non-negative amount", () => {
    assert.equal(pilotUpdateFromForm("abc", "500", []), null);
    assert.equal(pilotUpdateFromForm("-1", "500", []), null);
  });
});
