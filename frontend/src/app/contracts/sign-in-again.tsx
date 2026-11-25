"use client";

import { SignInButton } from "@clerk/nextjs";
import { BUTTON_CLASS } from "../ask-box";

// What to say when the service answers 401. `toDo` finishes "Sign in again to …".
export function sessionMessage(isSignedIn: boolean | undefined, toDo: string): string {
  return isSignedIn === false
    ? `Your session has expired. Sign in again to ${toDo}.`
    : "We could not confirm your sign-in. Please try again.";
}

// Signs in over the page, so a chosen file or pasted text is not left behind.
export default function SignInAgain({ returnTo = "/contracts" }: { returnTo?: string }) {
  return (
    <SignInButton mode="modal" forceRedirectUrl={returnTo} signUpForceRedirectUrl={returnTo}>
      <button type="button" className={BUTTON_CLASS}>
        Sign in again
      </button>
    </SignInButton>
  );
}
