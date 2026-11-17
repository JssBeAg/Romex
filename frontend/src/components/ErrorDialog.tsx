"use client";

import { useEffect, useRef } from "react";

type Props = {
  title?: string;
  messages: string[];
  onClose: () => void;
};

// A window in the middle of the screen that lists what went wrong, so it cannot be missed
// (an error at the top of a long form is easy to overlook). It closes with the button,
// with Escape or by clicking outside; the focus returns to where it was.
export default function ErrorDialog({ title = "No se pudo guardar", messages, onClose }: Props) {
  const closeButton = useRef<HTMLButtonElement>(null);
  // The latest onClose without restarting the effect below on every render of the parent
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  });

  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButton.current?.focus();

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onCloseRef.current();
      } else if (e.key === "Tab") {
        // The button is the only thing to reach: keep the focus on it
        e.preventDefault();
        closeButton.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus?.();
    };
  }, []);

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div
        className="dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        aria-describedby="dialog-messages"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="dialog-title" className="dialog-title">
          {title}
        </h2>
        <ul id="dialog-messages" className="dialog-messages">
          {messages.map((message, index) => (
            <li key={`${index}-${message}`}>{message}</li>
          ))}
        </ul>
        <div className="dialog-actions">
          <button ref={closeButton} type="button" className="dialog-close" onClick={onClose}>
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
}
