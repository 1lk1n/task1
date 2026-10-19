"use client";

import { useEffect } from "react";

type TelegramWebApp = {
  ready: () => void;
  expand: () => void;
};

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

/** Tells Telegram the Mini App is ready and opens it full height. Outside Telegram there is no WebApp object. */
export function TelegramInit() {
  useEffect(() => {
    const webApp = window.Telegram?.WebApp;
    webApp?.ready();
    webApp?.expand();
  }, []);
  return null;
}
