"use client";

import {
  Children,
  cloneElement,
  isValidElement,
  useId,
  type ReactNode,
} from "react";
type B2CFormFieldProps = {
  label: string;
  error?: string;
  hint?: string;
  required?: boolean;
  className?: string;
  children:
    | ReactNode
    | ((ids: {
        inputId: string;
        descriptionId: string | undefined;
      }) => ReactNode);
};
export function B2CFormField({
  label,
  error,
  hint,
  required = false,
  className = "",
  children,
}: B2CFormFieldProps) {
  const inputId = useId();
  const descriptionId = error || hint ? `${inputId}-desc` : undefined;
  const message = error ?? hint;
  const isError = Boolean(error);
  const renderedChildren =
    typeof children === "function"
      ? children({ inputId, descriptionId })
      : children;
  return (
    <div
      className={["flex flex-col gap-1", className].filter(Boolean).join(" ")}
    >
      {" "}
      <label
        htmlFor={inputId}
        className="text-osce-body font-medium text-osce-ink-900"
      >
        {" "}
        {label}{" "}
        {required ? (
          <span className="ml-0.5 text-osce-danger" aria-hidden="true">
            {" "}
            *{" "}
          </span>
        ) : null}{" "}
      </label>{" "}
      {typeof children !== "function" ? (
        <ChildWithId inputId={inputId} descriptionId={descriptionId}>
          {" "}
          {renderedChildren}{" "}
        </ChildWithId>
      ) : (
        renderedChildren
      )}{" "}
      {message ? (
        <p
          id={descriptionId}
          role={isError ? "alert" : undefined}
          className={[
            "text-osce-caption",
            isError ? "text-osce-danger" : "text-b2c-text-muted",
          ].join(" ")}
        >
          {" "}
          {message}{" "}
        </p>
      ) : null}{" "}
    </div>
  );
}
function ChildWithId({
  inputId,
  descriptionId,
  children,
}: {
  inputId: string;
  descriptionId: string | undefined;
  children: ReactNode;
}) {
  const child = Children.only(children);
  if (!isValidElement(child)) return <>{children}</>;
  return cloneElement(child as React.ReactElement<Record<string, unknown>>, {
    id: inputId,
    ...(descriptionId ? { "aria-describedby": descriptionId } : {}),
  });
}