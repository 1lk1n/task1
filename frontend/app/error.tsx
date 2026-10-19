"use client";

export default function CatalogError({ reset }: { error: Error; reset: () => void }) {
  return (
    <main>
      <h1>Каталог</h1>
      <p>Не удалось загрузить каталог.</p>
      <button type="button" onClick={reset}>
        Попробовать ещё раз
      </button>
    </main>
  );
}
