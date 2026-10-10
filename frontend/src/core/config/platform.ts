/**
 * Platform identity shown on the About page and in the footer.
 *
 * Version and release date are resolved at build time (see vite.config.ts):
 * the version is package.json's, the release date is VITE_PLATFORM_RELEASE_DATE
 * or the build date. The API version is not here -- the About page asks the
 * running backend for it, so it can never drift from what is deployed.
 */
export const PLATFORM_VERSION = __PLATFORM_VERSION__;
export const PLATFORM_RELEASE_DATE = __PLATFORM_RELEASE_DATE__;
export const PLATFORM_VENDOR = "Inspironics Corporation, USA";
export const PLATFORM_LICENSE = import.meta.env.VITE_PLATFORM_LICENSE || "Enterprise";
