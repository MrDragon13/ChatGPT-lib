import { describe, expect, it } from "vitest";

import { cardMotion, heroMotion, revealMotion } from "./transitions";

describe("cinematic motion grammar", () => {
  it("uses bounded transform/opacity transitions for the hero", () => {
    expect(heroMotion.enter).toMatchObject({ opacity: 1, x: 0, y: 0 });
    expect(heroMotion.exit).toMatchObject({ opacity: 0 });
    expect(heroMotion.transition.type).toBe("spring");
  });

  it("keeps card interaction subtle and transform-only", () => {
    expect(cardMotion.hover).toMatchObject({ y: -6, scale: 1.015 });
    expect(cardMotion.tap).toMatchObject({ scale: 0.985 });
  });

  it("provides an entrance reveal without layout animation", () => {
    expect(revealMotion.hidden).toMatchObject({ opacity: 0, y: 24 });
    expect(revealMotion.visible).toMatchObject({ opacity: 1, y: 0 });
  });
});
