# Naming Refactor QA Report

## Brand Rule Status

*   **Socratink wordmark casing**: PASS (except in the Webmanifest where it remains capitalized). All UI instances use `socratink` lowercase.
*   **No hype/Socratic Canvas**: FAIL. The login page title (`http://localhost:8000/login.html`) incorrectly reads `socratink — the Socratic Canvas`.
*   **Domain language (Reading Room / Field Journal)**: PASS. All labels correctly use "New Entry", "Desk", "Library", and "Settings".

## Console Logs
*   **404s or Asset failures**: FAIL. One 404 error was observed `Failed to load resource: the server responded with a status of 404 (Not Found)`.
*   **JS Errors**: PASS. No same-origin JS errors or unhandled promise rejections.

## Viewport Audit
*   **Login Flow**: P1 Failure on brand name in `<title>` (`socratink — the Socratic Canvas`).
*   **Sidebar**: PASS. Labels are correct: `New Entry`, `Desk`, `Library`, `Settings`.
*   **Creation Flow (New Entry)**: PASS. "draft path" / "lightweight draft" / "Write what you can reconstruct from memory." labels are correct.
*   **Desk (Map / Graph)**: PASS. Route and Graph mode toggles work. Node kickers read `SECTION`, `ENTRY`, and `BACKBONE PRINCIPLE` correctly. The detail copy for locked nodes correctly uses "Locked section" and "Locked entry".
*   **Library**: PASS. List of saved drafts and "Try from memory" options operate smoothly.
*   **Settings**: PASS. Title "Your reading room" is correct. Toggles for Theme, Reduced motion, and Threshold sounds are present and update `localStorage` states accurately (`socratink.motion: reduced`, etc).

## P1/P2 Regression List

1.  **[P1] Login Title Violation**: The HTML title of the login page violates the strict "no hype" branding rule by including "the Socratic Canvas".
    *   **Fix**: Update the title tag in `login.html` to `socratink — sign in`.
2.  **[P1] PWA Manifest Violation**: The `manifest.webmanifest` contains the capitalized "Socratink" and "Socratic learning canvas" which violates the strict casing and branding rules.
    *   **Fix**: Update `manifest.webmanifest` description to: "A study tool for learning by reconstruction. See what you can actually explain." and change name to `socratink`.
3.  **[P2] Console 404 Error**: A 404 error was logged in the console upon initial load or navigation, suggesting a missing asset (possibly favicon or font).
    *   **Fix**: Identify and resolve the missing asset request.

## Overall Verdict
The application is functionally sound and the majority of the UI has successfully adopted the new "Reading Room" and "Field Journal" terminology. However, due to the P1 brand violations in the login page title and PWA manifest, the release is **BLOCKED** pending these corrections.
