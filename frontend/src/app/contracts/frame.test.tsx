import { render, screen, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import ContractsFrame from "./frame";

vi.mock("@clerk/nextjs", () => ({ useAuth: () => ({ isLoaded: false }) }));

it("keeps the site header and footer outside <main>", () => {
  render(
    <ContractsFrame>
      <p>The page</p>
    </ContractsFrame>,
  );
  const main = screen.getByRole("main");
  expect(within(main).getByText("The page")).toBeInTheDocument();
  expect(main.contains(screen.getByRole("banner"))).toBe(false);
  expect(main.contains(screen.getByRole("contentinfo"))).toBe(false);
});
