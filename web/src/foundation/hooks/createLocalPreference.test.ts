import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import { createLocalPreference } from "./createLocalPreference";

const store = new Map<string, string>();
const fake = {
  getItem: (k: string) => store.get(k) ?? null,
  setItem: (k: string, v: string) => void store.set(k, v),
  removeItem: (k: string) => void store.delete(k),
};
Object.defineProperty(globalThis, "localStorage", { value: fake, configurable: true });
afterEach(() => store.clear());

const flag = () => createLocalPreference<boolean>({ key: "k", fallback: false, decode: (s) => s === "1", encode: (v) => (v ? "1" : null) });

test("reads the fallback, stores a value, clears on null, and notifies", () => {
  const p = flag();
  let calls = 0;
  const off = p.subscribe(() => calls++);
  assert.equal(p.get(), false);
  p.set(true);
  assert.equal(store.get("k"), "1");
  assert.equal(p.get(), true);
  p.set(false);
  assert.equal(store.has("k"), false);
  off();
  p.set(true);
  assert.equal(calls, 2);
  assert.equal(p.getServer(), false);
});

test("throwing storage falls back and still notifies", () => {
  const p = flag();
  let calls = 0;
  p.subscribe(() => calls++);
  Object.defineProperty(globalThis, "localStorage", { value: { getItem: () => { throw new Error("x"); }, setItem: () => { throw new Error("x"); }, removeItem: () => { throw new Error("x"); } }, configurable: true });
  assert.equal(p.get(), false);
  p.set(true);
  assert.equal(calls, 1);
  Object.defineProperty(globalThis, "localStorage", { value: fake, configurable: true });
});
