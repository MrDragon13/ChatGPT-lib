import { describe, expect, it } from "vitest";

import { libraryHref, resolveTarget, workHref } from "./router";

const targetConfig = {
  default_target: "couple",
  targets: {
    viewers: ["partner", "primary"],
    groups: { couple: ["primary", "partner"] },
  },
};

describe("target routing", () => {
  it("defaults to couple when no target parameter is present", () => {
    expect(resolveTarget(targetConfig, new URLSearchParams())).toBe("couple");
  });

  it("lets a configured URL target override the default", () => {
    expect(resolveTarget(targetConfig, new URLSearchParams("target=primary"))).toBe("primary");
  });

  it("falls back for an unknown target", () => {
    expect(resolveTarget(targetConfig, new URLSearchParams("target=someone"))).toBe("couple");
  });
});

describe("hash hrefs", () => {
  it("creates a refresh-safe work deep link", () => {
    expect(workHref("arrival-2016", "couple")).toBe("#/work/arrival-2016?target=couple");
  });

  it("preserves target and library filters", () => {
    expect(libraryHref("couple", { viewing: "unwatched", genre: "genre.drama" })).toBe(
      "#/library?target=couple&viewing=unwatched&genre=genre.drama",
    );
  });
});
