import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { AppShell } from "./AppShell";

const manifest = {
  schema_version: 1,
  default_target: "couple",
  targets: { viewers: ["partner", "primary"], groups: { couple: ["primary", "partner"] } },
  vocabulary: {},
  profiles: {},
  recommendations: {},
  works: [],
};

function response() {
  return Promise.resolve({
    ok: true,
    json: async () => manifest,
  } as Response);
}

function renderShell() {
  return render(
    <MemoryRouter initialEntries={["/today?target=couple"]}>
      <AppShell><div>content ready</div></AppShell>
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("AppShell manifest refresh", () => {
  it("refreshes the manifest when the window regains focus after the throttle window", async () => {
    let now = 1_000;
    vi.spyOn(Date, "now").mockImplementation(() => now);
    const fetchMock = vi.fn(response);
    vi.stubGlobal("fetch", fetchMock);

    renderShell();
    expect(await screen.findByText("content ready")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);

    now += 15_001;
    fireEvent.focus(window);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });

  it("refreshes the manifest when a hidden tab becomes visible after the throttle window", async () => {
    let now = 5_000;
    vi.spyOn(Date, "now").mockImplementation(() => now);
    const visibility = vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
    const fetchMock = vi.fn(response);
    vi.stubGlobal("fetch", fetchMock);

    renderShell();
    expect(await screen.findByText("content ready")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);

    now += 15_001;
    fireEvent(document, new Event("visibilitychange"));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    visibility.mockRestore();
  });
});
