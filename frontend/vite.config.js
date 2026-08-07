// Test bloğunun tanınması için config vitest'ten alınır (vite'ınki test alanını yok sayar).
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({

    // GitHub Pages / custom domain deployment
    base: "/",

    plugins: [
        react(),
        tailwindcss(),
    ],

    server: {
        host: true,

        proxy: {
            "/api": {
                target: "http://127.0.0.1:8000",
                changeOrigin: true,
                rewrite: (yol) => yol.replace(/^\/api/, ""),
            },
        },
    },

    test: {
        environment: "jsdom",
        globals: true,
        setupFiles: "./src/test/setup.js",
    },

});