"use client";

import { SignInButton, UserButton, useAuth } from "@clerk/nextjs";

const TRIGGER = { width: "2.75rem", height: "2.75rem", justifyContent: "center", borderRadius: "999px" };

// Sign-in and the user menu for the page headers. Shows nothing until Clerk has loaded, so a
// signed-in visitor never sees "Sign in" flash.
export default function AccountNav() {
  const { isLoaded, isSignedIn } = useAuth();
  if (!isLoaded) return null;
  // The avatar is small, so its button is given the same target as the theme toggle's.
  if (isSignedIn) return <UserButton appearance={{ elements: { userButtonTrigger: TRIGGER } }} />;
  return (
    <SignInButton>
      <button type="button" className="inline-flex min-h-11 items-center text-sm font-medium underline underline-offset-4">
        Sign in
      </button>
    </SignInButton>
  );
}
