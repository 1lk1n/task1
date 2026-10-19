import type { Metadata } from "next";
import Script from "next/script";
import type { ReactNode } from "react";

import { TelegramInit } from "./telegram-init";

export const metadata: Metadata = {
  title: "Каталог",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body>
        {/* Telegram Mini App SDK: inside Telegram it connects the page to the client, in a browser it does nothing. */}
        <Script src="https://telegram.org/js/telegram-web-app.js" strategy="beforeInteractive" />
        <TelegramInit />
        {children}
      </body>
    </html>
  );
}
