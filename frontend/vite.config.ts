import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
    hmr: {
      overlay: false,
    },
    proxy: {
      "/api": {
        target: "http://api:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },

  plugins: [
    react(),

    mode === "development" && componentTagger(),

    VitePWA({
      registerType: "autoUpdate",
      strategies: "generateSW",

      devOptions: {
        enabled: false,
      },

      includeAssets: [
        "favicon.ico",
        "apple-touch-icon.png",
        "robots.txt",
      ],

      manifest: {
        name: "Provectus - Sistema de Ensino",
        short_name: "Provectus",
        description:
          "Provectus - Sistema de controle estatístico para EsPCEx",
        theme_color: "#1a2419",
        background_color: "#0d130c",
        display: "fullscreen",
        orientation: "portrait",
        scope: "/",
        start_url: "/",
        lang: "pt-BR",
        icons: [
          {
            src: "/favicon.ico",
            sizes: "256x256",
            type: "image/x-icon",
            purpose: "any",
          },
        ],
      },

      workbox: {
        cleanupOutdatedCaches: true,

        globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],

        navigateFallbackDenylist: [/^\/api/],

        runtimeCaching: [
          {
            urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
            handler: "CacheFirst",
            options: {
              cacheName: "google-fonts-cache",
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 * 365,
              },
            },
          },
          {
            urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
            handler: "CacheFirst",
            options: {
              cacheName: "gstatic-fonts-cache",
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 * 365,
              },
            },
          },
        ],
      },
    }),
  ].filter(Boolean),

  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));