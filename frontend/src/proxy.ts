import { clerkMiddleware } from "@clerk/nextjs/server";
import { needsSignIn } from "@/lib/protected-routes";

// Signed-out visitors to /ask or /contracts are sent to sign in, then back to where they were
// (the Query in /ask?q=… is kept). This is an optimistic check: the backend verifies the token.
export default clerkMiddleware(async (auth, req) => {
  if (needsSignIn(req.nextUrl.pathname)) await auth.protect();
});

export const config = {
  matcher: [
    // Skip Next.js internals and static files, unless found in search params.
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
