/**
 * PadSpan — Vendored Preact + Hooks + htm bundle
 *
 * Re-exports everything needed for Preact views.
 * No CDN dependency — all files are local.
 *
 * Preact 10.25.4 — https://preactjs.com (MIT License)
 * htm 3.1.1 — https://github.com/developit/htm (Apache-2.0 License)
 */

// Core Preact
export { h, render, Component, Fragment, createContext, createElement, createRef, cloneElement, toChildArray, isValidElement, options } from "./preact.mjs";

// Hooks
export { useState, useEffect, useRef, useCallback, useMemo, useReducer, useContext, useLayoutEffect, useErrorBoundary, useId } from "./preact-hooks-local.mjs";

// htm — tagged template literal JSX alternative
import _htm from "./htm.mjs";
import { h as _h } from "./preact.mjs";

/** Pre-bound htm template tag: html`<div>...</div>` */
export const html = _htm.bind(_h);
