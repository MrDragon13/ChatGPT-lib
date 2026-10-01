import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { TargetSwitcher } from "./TargetSwitcher";

const targets = {
  viewers: ["partner", "primary"],
  groups: { couple: ["primary", "partner"] },
};

describe("TargetSwitcher", () => {
  it("shows configured household profiles and marks the active one", () => {
    render(
      <MemoryRouter initialEntries={["/today?target=couple"]}>
        <TargetSwitcher targets={targets} activeTarget="couple" />
      </MemoryRouter>,
    );

    const switcher = screen.getByRole("navigation", { name: "Профиль просмотра" });
    expect(switcher).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Я" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Партнёр" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Вместе" })).toHaveAttribute("aria-current", "page");
  });

  it("changes only target while preserving the current route filters", () => {
    render(
      <MemoryRouter initialEntries={["/library?target=couple&genre=genre.drama&viewing=unwatched"]}>
        <TargetSwitcher targets={targets} activeTarget="couple" />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Я" })).toHaveAttribute(
      "href",
      "/library?target=primary&genre=genre.drama&viewing=unwatched",
    );
    expect(screen.getByRole("link", { name: "Партнёр" })).toHaveAttribute(
      "href",
      "/library?target=partner&genre=genre.drama&viewing=unwatched",
    );
  });
});
