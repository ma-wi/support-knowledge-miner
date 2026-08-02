import path from "node:path";
import { fileURLToPath } from "node:url";

import react from "../../frontend/node_modules/@vitejs/plugin-react/dist/index.js";

const TOOL_DIRECTORY = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = path.resolve(TOOL_DIRECTORY, "../../frontend");

export default {
  root: FRONTEND_ROOT,
  plugins: [react()],
  clearScreen: false,
  server: {
    host: "127.0.0.1",
    strictPort: true,
    fs: {
      strict: true,
      allow: [FRONTEND_ROOT],
      deny: [".env", ".env.*", "*.{crt,pem}", "**/.git/**"],
    },
    hmr: {
      host: "127.0.0.1",
      protocol: "ws",
    },
  },
};
