"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

export type ToastTone = "success" | "error" | "warning" | "info";

export interface ToastAction {
  label: string;
  href?: string;
  onClick?: () => void;
}

export interface ToastInput {
  /** Supply an id to replace an existing toast in place (e.g. one per job). */
  id?: string;
  tone?: ToastTone;
  title: string;
  message?: string;
  /** Stays until dismissed. Default for errors with an action. */
  persistent?: boolean;
  durationMs?: number;
  action?: ToastAction;
  /** Called when the toast is dismissed by the user or by its action. */
  onDismiss?: () => void;
}

export interface ToastItem extends ToastInput {
  id: string;
  tone: ToastTone;
  createdAt: number;
  /** Resolved auto-dismiss delay, or null when the toast is persistent. */
  resolvedDurationMs: number | null;
}

export interface ToastContextValue {
  toasts: ToastItem[];
  show: (input: ToastInput) => string;
  success: (title: string, message?: string) => string;
  error: (title: string, message?: string) => string;
  warning: (title: string, message?: string) => string;
  info: (title: string, message?: string) => string;
  dismiss: (id: string) => void;
  dismissAll: () => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const MAX_VISIBLE = 3;
const DEFAULT_DURATION_MS = 4500;
const ERROR_DURATION_MS = 8000;

let counter = 0;
const nextId = () => `toast-${Date.now()}-${(counter += 1)}`;

const durationFor = (input: ToastInput, tone: ToastTone): number | null => {
  if (input.persistent) return null;
  if (input.durationMs) return input.durationMs;
  return tone === "error" ? ERROR_DURATION_MS : DEFAULT_DURATION_MS;
};

interface ToastProviderProps {
  children: ReactNode;
  /** Each host (B2C, B2B) supplies its own chrome for the toast stack. */
  renderViewport: (
    toasts: ToastItem[],
    dismiss: (id: string) => void,
  ) => ReactNode;
}

/** Headless toast queue. Token-free so B2C and B2B can share it. */
export function ToastProvider({
  children,
  renderViewport,
}: ToastProviderProps) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
  const callbacks = useRef<Map<string, () => void>>(new Map());

  const clearTimer = useCallback((id: string) => {
    const timer = timers.current.get(id);
    if (timer) clearTimeout(timer);
    timers.current.delete(id);
  }, []);

  const remove = useCallback(
    (id: string) => {
      clearTimer(id);
      setToasts((current) => current.filter((toast) => toast.id !== id));
    },
    [clearTimer],
  );

  const dismiss = useCallback(
    (id: string) => {
      const onDismiss = callbacks.current.get(id);
      callbacks.current.delete(id);
      remove(id);
      onDismiss?.();
    },
    [remove],
  );

  const show = useCallback(
    (input: ToastInput): string => {
      const id = input.id ?? nextId();
      const tone = input.tone ?? "info";
      const duration = durationFor(input, tone);
      const item: ToastItem = {
        ...input,
        id,
        tone,
        createdAt: Date.now(),
        resolvedDurationMs: duration,
      };
      if (input.onDismiss) callbacks.current.set(id, input.onDismiss);
      clearTimer(id);
      setToasts((current) => {
        const rest = current.filter((toast) => toast.id !== id);
        return [...rest, item].slice(-MAX_VISIBLE);
      });
      if (duration !== null) {
        timers.current.set(
          id,
          setTimeout(() => remove(id), duration),
        );
      }
      return id;
    },
    [clearTimer, remove],
  );

  const dismissAll = useCallback(() => {
    timers.current.forEach((timer) => clearTimeout(timer));
    timers.current.clear();
    callbacks.current.clear();
    setToasts([]);
  }, []);

  useEffect(() => {
    const pending = timers.current;
    return () => pending.forEach((timer) => clearTimeout(timer));
  }, []);

  const value = useMemo<ToastContextValue>(
    () => ({
      toasts,
      show,
      success: (title, message) => show({ tone: "success", title, message }),
      error: (title, message) => show({ tone: "error", title, message }),
      warning: (title, message) => show({ tone: "warning", title, message }),
      info: (title, message) => show({ tone: "info", title, message }),
      dismiss,
      dismissAll,
    }),
    [toasts, show, dismiss, dismissAll],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastViewportSlot render={renderViewport} />
    </ToastContext.Provider>
  );
}

function ToastViewportSlot({
  render,
}: {
  render: ToastProviderProps["renderViewport"];
}) {
  const { toasts, dismiss } = useToastContext();
  return <>{render(toasts, dismiss)}</>;
}

export function useToastContext(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToastContext must be used within a ToastProvider");
  }
  return context;
}

/** Non-throwing variant for components that may render outside a provider. */
export function useOptionalToastContext(): ToastContextValue | null {
  return useContext(ToastContext);
}
