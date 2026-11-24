import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import AccountNav from "./account-nav";

let signedIn: boolean | undefined;
vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ isLoaded: signedIn !== undefined, isSignedIn: signedIn }),
  SignInButton: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  UserButton: () => <div data-testid="user-button" />,
}));

describe("AccountNav", () => {
  it("offers sign in to a signed-out visitor", () => {
    signedIn = false;
    render(<AccountNav />);
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByTestId("user-button")).not.toBeInTheDocument();
  });

  it("shows the user button once signed in", () => {
    signedIn = true;
    render(<AccountNav />);
    expect(screen.getByTestId("user-button")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sign in" })).not.toBeInTheDocument();
  });

  it("shows neither while Clerk is still loading", () => {
    signedIn = undefined;
    render(<AccountNav />);
    expect(screen.queryByRole("button", { name: "Sign in" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("user-button")).not.toBeInTheDocument();
  });
});
