import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { asksTestimonial, composeFeedbackBody } from "@/capabilities/help/productFeedbackModel";

const base = { name: "A", email: "a@b.co", source: "contact" as const, experience: "ok" };

describe("testimonial question", () => {
  it("is asked from 3 stars up", () => {
    assert.equal(asksTestimonial(2), false);
    assert.equal(asksTestimonial(3), true);
  });

  it("is left out of the body for a low rating, kept for a high one", () => {
    const low = composeFeedbackBody({ ...base, rating: 2, testimonialPermission: "" });
    assert.ok(!low.includes("Testimonial permission"));
    const high = composeFeedbackBody({ ...base, rating: 4, testimonialPermission: "yes_anonymous" });
    assert.ok(high.includes("Testimonial permission: Yes, anonymously"));
  });
});
