import { act, render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  BrokerSessionProvider,
  type BrokerSessionValue,
  useBrokerSession,
} from "./BrokerSessionProvider";

let session: BrokerSessionValue | null = null;

function Probe() {
  session = useBrokerSession();
  return <div data-testid="state">{session.authenticated ? "authenticated" : session.configured ? "ready" : "read-only"}</div>;
}

afterEach(() => {
  session = null;
  vi.restoreAllMocks();
});

describe("BrokerSessionProvider", () => {
  it("stays read-only when no broker is configured", () => {
    const open = vi.spyOn(window, "open");
    render(<BrokerSessionProvider baseUrl={null}><Probe /></BrokerSessionProvider>);
    expect(session?.configured).toBe(false);
    act(() => session?.login());
    expect(open).not.toHaveBeenCalled();
  });

  it("accepts an auth token only from the exact broker origin and opened popup", async () => {
    const popup = window;
    const open = vi.spyOn(window, "open").mockReturnValue(popup);
    const storageWrite = vi.spyOn(Storage.prototype, "setItem");
    render(<BrokerSessionProvider baseUrl="https://broker.example"><Probe /></BrokerSessionProvider>);

    act(() => session?.login());
    expect(open).toHaveBeenCalledWith(
      "https://broker.example/v1/auth/start",
      "media-broker-auth",
      expect.any(String),
    );

    act(() => window.dispatchEvent(new MessageEvent("message", {
      origin: "https://evil.example",
      source: popup,
      data: { type: "media-broker-auth", token: "evil-token" },
    })));
    expect(session?.authenticated).toBe(false);

    act(() => window.dispatchEvent(new MessageEvent("message", {
      origin: "https://broker.example",
      source: null,
      data: { type: "media-broker-auth", token: "wrong-source" },
    })));
    expect(session?.authenticated).toBe(false);

    act(() => window.dispatchEvent(new MessageEvent("message", {
      origin: "https://broker.example",
      source: popup,
      data: { type: "media-broker-auth", token: "broker-token" },
    })));
    await waitFor(() => expect(session?.authenticated).toBe(true));
    expect(storageWrite).not.toHaveBeenCalled();
  });

  it("clears the memory session on 401 and supports local logout", async () => {
    const open = vi.spyOn(window, "open").mockReturnValue(window);
    render(<BrokerSessionProvider baseUrl="https://broker.example"><Probe /></BrokerSessionProvider>);
    act(() => session?.login());
    act(() => window.dispatchEvent(new MessageEvent("message", {
      origin: "https://broker.example",
      source: window,
      data: { type: "media-broker-auth", token: "broker-token" },
    })));
    await waitFor(() => expect(session?.authenticated).toBe(true));

    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ error: "unauthorized" }), {
      status: 401,
      headers: { "content-type": "application/json" },
    }));
    await act(async () => {
      await expect(session!.getOperationStatus("11111111-2222-4333-8444-555555555555")).rejects.toMatchObject({ status: 401 });
    });
    expect(session?.authenticated).toBe(false);

    act(() => session?.login());
    expect(open).toHaveBeenCalledTimes(2);
    act(() => window.dispatchEvent(new MessageEvent("message", {
      origin: "https://broker.example",
      source: window,
      data: { type: "media-broker-auth", token: "broker-token-2" },
    })));
    await waitFor(() => expect(session?.authenticated).toBe(true));
    act(() => session?.logout());
    expect(session?.authenticated).toBe(false);
  });
});
