import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";

import { afterEach, beforeEach, vi } from "vitest";


// jsdom penceresinde `localStorage` bu sürümde tanımsız geliyor (Node'un bayrak isteyen
// yerleşik Storage'ı gölgeliyor); uygulama kodu çıplak `localStorage` kullandığı için
// bellek içi basit bir depo global'e yerleştirilir.
const kayitlar = new Map();

const depo = {
    getItem: (anahtar) => (kayitlar.has(anahtar) ? kayitlar.get(anahtar) : null),
    setItem: (anahtar, deger) => kayitlar.set(anahtar, String(deger)),
    removeItem: (anahtar) => kayitlar.delete(anahtar),
    clear: () => kayitlar.clear(),
};

Object.defineProperty(globalThis, "localStorage", { value: depo, configurable: true });

Object.defineProperty(window, "localStorage", { value: depo, configurable: true });


beforeEach(() => {
    localStorage.clear();
});


afterEach(() => {
    cleanup();
    vi.clearAllMocks();
});
