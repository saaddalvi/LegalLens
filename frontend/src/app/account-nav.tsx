"use client";

import { SignInButton, UserButton, useAuth } from "@clerk/nextjs";

// Sign-in and the user menu for the page headers. Shows nothing until Clerk has loaded, so a
// signed-in visitor never sees "Sign in" flash.
export default function AccountNav() {
  const { isLoaded, isSignedIn } = useAuth();
  if (!isLoaded) return null;
  if (isSignedIn) return <UserButton />;
  return (
    <SignInButton>
      <button type="button" className="inline-flex min-h-11 items-center text-sm font-medium underline underline-offset-4">
        Sign in
      </button>
    </SignInButton>
  );
}
