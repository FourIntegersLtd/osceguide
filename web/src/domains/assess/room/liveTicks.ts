/** Saving a tick: tried a few times before the person is told it did not save. */
export type TickSave = "idle" | "saving" | "saved" | "failed";

export async function saveWithRetry(
  save: () => Promise<unknown>,
  attempts = 3,
  wait: (ms: number) => Promise<void> = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
): Promise<TickSave> {
  for (let i = 0; i < attempts; i++) {
    try {
      await save();
      return "saved";
    } catch {
      if (i < attempts - 1) await wait(300 * (i + 1));
    }
  }
  return "failed";
}

/**
 * Saves one at a time, in the order the ticks happened.
 *
 * `touch` says something changed; `flush` saves it. A flush while a save is in flight joins that
 * run, which goes round again for whatever changed meanwhile, so a re-tick during a save is not lost
 * and two saves can never land out of order. `save` reads the latest state when it runs.
 */
export function createSaveQueue(
  save: () => Promise<unknown>,
  onStatus: (status: TickSave) => void,
  wait?: (ms: number) => Promise<void>,
) {
  let version = 0;
  let saved = 0;
  let running: Promise<void> | null = null;

  async function drain() {
    while (saved < version) {
      const at = version;
      onStatus("saving");
      if ((await saveWithRetry(save, 3, wait)) === "failed") return onStatus("failed");
      saved = at;
    }
    onStatus("saved");
  }

  return {
    touch() {
      version++;
    },
    flush(): Promise<void> {
      running ??= drain().finally(() => {
        running = null;
      });
      return running;
    },
  };
}
