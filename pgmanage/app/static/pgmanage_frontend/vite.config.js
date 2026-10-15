/// <reference types="vitest" />
import { fileURLToPath, URL } from "node:url";

import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "node:path";
import { nodePolyfills } from "vite-plugin-node-polyfills";
import inject from "@rollup/plugin-inject";

const outDir = path.join("..", "dist");
const isDebugBuild = process.env.DEBUG === 'true'

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd());
  const isEnterprise = mode === 'enterprise';
  // vite-plugin-node-polyfills 0.27.0+ runs an inject transform in dev, also on pre-bundled
  // deps (https://github.com/davidmyersdev/vite-plugin-node-polyfills/pull/152).
  // This adds a huge inline sourcemap: sql-autocomplete.js is 268 MB instead of 30 MB.
  // "dev" adds the globals with the optimizer banner only. Set all 3: one `true` keeps the transform.
  const polyfillGlobals = command === "serve" ? "dev" : true;
  return {
    plugins: [
      inject({
        $: "jquery",
        jQuery: "jquery",
        include: "**/*.js",
        sourceMap: isDebugBuild,
      }),
      vue(),
      nodePolyfills({
        globals: {
          Buffer: polyfillGlobals,
          global: polyfillGlobals,
          process: polyfillGlobals,
        },
      }),
    ],
    server: {
      host: "127.0.0.1",
      port: 3000,
      open: false,
      watch: {
        usePolling: true,
        disableGlobbing: false,
      },
    },
    build: {
      manifest: true,
      minify: !isDebugBuild,
      rollupOptions: {
        input: ["./src/main.js", "./src/login.js"],
        output: {
          entryFileNames: `assets/[name].[hash].js`,
          chunkFileNames: `assets/[name].[hash].js`,
          assetFileNames: `assets/[name].[hash].[ext]`,
        },
      },
      outDir: outDir,
    },
    base: "/static/",
    define: {
      __VITE_ENTERPRISE__: isEnterprise
    },
    resolve: {
      alias: {
        "@src": path.resolve(__dirname, "src"),
        "@enterprise": path.resolve(__dirname, "enterprise"),
        "@conditional": isEnterprise ? path.resolve(__dirname, "enterprise") : path.resolve(__dirname, "src"),
        vue: "vue/dist/vue.esm-bundler.js",
        "~bootstrap": path.resolve(__dirname, "node_modules/bootstrap"),
        moment: path.resolve(__dirname, "node_modules/moment/moment.js"),
      },
      preserveSymlinks: true,
    },
    test: {
      environment: "happy-dom",
      coverage: {
        reporter: ["html"],
        enabled: true
      },
      setupFiles: ["./test/global_setup.js"],
    },
    css: {
      preprocessorOptions: {
        scss: {
          silenceDeprecations: ['mixed-decls', 'color-functions', 'legacy-js-api'],
          additionalData: `@import '@src/assets/scss/common/variables';`,
        },
      }
    },
  };
});