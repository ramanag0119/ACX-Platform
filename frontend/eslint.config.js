import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": "off",
      /*
        Was "off", which is how thirty-odd unused imports, dead helpers and
        write-only state accumulated unseen -- including a Holidays Edit button
        wired to a dialog with no inputs while the handler that would have
        seeded the real form sat uncalled, and five pagination footers whose
        buttons carried no onClick.

        "warn", not "error": it must surface this class of rot on every lint
        run without failing a build over a deliberately unused binding. The
        `^_` escape hatch covers those -- a discarded callback argument is
        named `_item`, not silently tolerated.
      */
      "@typescript-eslint/no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],
    },
  },
);
