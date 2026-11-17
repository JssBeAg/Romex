"use client";

import {
  type ChangeEvent,
  type FocusEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import ErrorDialog from "@/components/ErrorDialog";
import type { ApiResult, FieldErrors } from "@/lib/http";

// How long to wait after the last change before asking the server
const CHECK_DELAY_MS = 400;

type Options<T> = {
  // What the form would send right now; the server checks it whenever it changes
  payload: T;
  // Asks the server to check the payload without saving it
  validate: (payload: T) => Promise<ApiResult<unknown>>;
  // Problems the browser can see by itself (e.g. two passwords that differ)
  localErrors?: FieldErrors;
  // Field name -> the label the person sees, used in the error window
  labels: Record<string, string>;
};

// The field a form event comes from: data-field, then name, then id
function fieldOf(target: EventTarget): string | undefined {
  const element = target as HTMLElement & { name?: string };
  return element.dataset?.field || element.name || element.id || undefined;
}

// Messages for the error window: "Label: message", or only the message for general problems
function toMessages(errors: FieldErrors, labels: Record<string, string>): string[] {
  const messages: string[] = [];
  for (const [field, list] of Object.entries(errors)) {
    for (const message of list) {
      messages.push(labels[field] ? `${labels[field]}: ${message}` : message);
    }
  }
  return messages;
}

/**
 * Feedback for the errors of a form:
 *  - under each field, while it is being filled in (the server checks the whole form a moment
 *    after the last change, so rules like "already registered" show up without sending it);
 *  - in a window in the middle of the screen when sending fails.
 * Messages of a field appear once the person has touched it, or after a failed send.
 */
export function useFormFeedback<T>({ payload, validate, localErrors = {}, labels }: Options<T>) {
  const [touched, setTouched] = useState<Set<string>>(new Set());
  const [attempted, setAttempted] = useState(false); // a send has failed at least once
  const [serverErrors, setServerErrors] = useState<FieldErrors>({});
  // Errors from the last failed send; they only apply to the data that was sent
  const [sendErrors, setSendErrors] = useState<{ key: string; errors: FieldErrors } | null>(null);
  const [dialog, setDialog] = useState<{ title: string; messages: string[] } | null>(null);

  const key = JSON.stringify(payload);
  const latest = useRef({ payload, validate });
  useEffect(() => {
    latest.current = { payload, validate };
  });

  const active = touched.size > 0 || attempted;
  const turn = useRef(0);

  // Ask the server about the form a moment after the last change
  useEffect(() => {
    if (!active) return;
    const mine = ++turn.current;
    const timer = setTimeout(async () => {
      const res = await latest.current.validate(latest.current.payload);
      if (mine !== turn.current) return; // a newer check took over
      if (res.ok) setServerErrors(res.errors ?? {});
    }, CHECK_DELAY_MS);
    return () => clearTimeout(timer);
  }, [key, active]);

  const touch = useCallback((field: string | undefined) => {
    if (!field) return;
    setTouched((previous) => (previous.has(field) ? previous : new Set(previous).add(field)));
  }, []);

  // Everything known about each field: what the server said, what the browser sees and what
  // the last failed send said (until the data changes)
  const all: FieldErrors = {};
  const sources = [serverErrors, localErrors, sendErrors?.key === key ? sendErrors.errors : {}];
  for (const source of sources) {
    for (const [field, list] of Object.entries(source)) {
      for (const message of list) {
        if (!all[field]?.includes(message)) (all[field] ??= []).push(message);
      }
    }
  }

  // Put on the <form>: no browser bubbles (the messages are ours) and track the touched fields
  const formProps = {
    noValidate: true,
    onChange: (e: ChangeEvent<HTMLFormElement>) => touch(fieldOf(e.target)),
    onBlur: (e: FocusEvent<HTMLFormElement>) => touch(fieldOf(e.target)),
  };

  // The messages shown under a field
  function fieldErrors(name: string): ReactNode {
    if (!attempted && !touched.has(name)) return null;
    return (all[name] ?? []).map((message) => (
      <div key={message} className="field-error" aria-live="polite">
        {message}
      </div>
    ));
  }

  // The form cannot be sent: mark every field and open the window. Pass the errors by field
  // and/or a general message (e.g. the server could not be reached).
  function reject(errors: FieldErrors | undefined, general?: string, title = "No se pudo guardar") {
    setAttempted(true);
    setSendErrors({ key, errors: errors ?? {} });
    const messages = toMessages(errors ?? {}, labels);
    if (general && !messages.includes(general)) messages.unshift(general);
    setDialog({ title, messages: messages.length > 0 ? messages : [title] });
  }

  // Same, for the result of a request that failed
  function rejectResult(res: ApiResult<unknown>) {
    reject(res.errors, res.error);
  }

  // The form was not sent because of what the browser itself found: show everything known
  function rejectKnown() {
    reject(all);
  }

  const dialogElement: ReactNode = dialog && (
    <ErrorDialog title={dialog.title} messages={dialog.messages} onClose={() => setDialog(null)} />
  );

  return {
    formProps,
    touch,
    fieldErrors,
    localHasErrors: Object.keys(localErrors).length > 0,
    reject,
    rejectResult,
    rejectKnown,
    dialog: dialogElement,
  };
}
