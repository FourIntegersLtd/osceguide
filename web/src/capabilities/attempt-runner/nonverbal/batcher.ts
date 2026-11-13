// Groups samples into numbered batches. Posting is triggered by sample count, never by a timer.
import type { Sample } from "./sampler";

export interface Batch {
  seq: number;
  client_sent_at_ms: number;
  samples: Sample[];
}

export class Batcher {
  private pending: Sample[] = [];
  private seq: number;

  private readonly size: number;

  /** `startSeq` continues the numbering of an attempt whose capture paused: the server drops a repeated seq. */
  constructor(size: number, startSeq = 0) {
    this.size = size;
    this.seq = startSeq;
  }

  /** The seq the next batch will carry. */
  get nextSeq(): number {
    return this.seq;
  }

  /** Adds a sample; returns a batch when `size` samples have gathered. */
  add(sample: Sample, nowMs: number): Batch | null {
    this.pending.push(sample);
    return this.pending.length >= this.size ? this.flush(nowMs) : null;
  }

  /** Releases whatever is pending, or null when nothing is. */
  flush(nowMs: number): Batch | null {
    if (this.pending.length === 0) return null;
    const batch = { seq: this.seq++, client_sent_at_ms: nowMs, samples: this.pending };
    this.pending = [];
    return batch;
  }
}
