import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { brokerBaseUrl } from "./config";
import {
  BrokerHttpError,
  getOperationStatus as fetchOperationStatus,
  submitFeedback as postFeedback,
} from "./client";
import type { FeedbackEditInput, OperationStatusResponse, SubmittedOperation } from "./types";

export type BrokerSessionValue = {
  configured: boolean;
  authenticated: boolean;
  login(): void;
  logout(): void;
  submitFeedback(input: FeedbackEditInput): Promise<SubmittedOperation>;
  getOperationStatus(operationId: string): Promise<OperationStatusResponse>;
};

const BrokerSessionContext = createContext<BrokerSessionValue | null>(null);

type BrokerSessionProviderProps = {
  children: ReactNode;
  baseUrl?: string | null;
};

function unauthenticated(): BrokerHttpError {
  return new BrokerHttpError(401, "unauthorized");
}

export function BrokerSessionProvider({ children, baseUrl }: BrokerSessionProviderProps) {
  const configuredBaseUrl = baseUrl === undefined ? brokerBaseUrl() : brokerBaseUrl(baseUrl ?? undefined);
  const [token, setToken] = useState<string | null>(null);
  const popupRef = useRef<Window | null>(null);

  const logout = useCallback(() => {
    setToken(null);
    popupRef.current = null;
  }, []);

  const login = useCallback(() => {
    if (!configuredBaseUrl) return;
    const popup = window.open(
      `${configuredBaseUrl}/v1/auth/start`,
      "media-broker-auth",
      "popup=yes,width=720,height=760,resizable=yes,scrollbars=yes",
    );
    popupRef.current = popup;
  }, [configuredBaseUrl]);

  useEffect(() => {
    if (!configuredBaseUrl) return;
    const expectedOrigin = new URL(configuredBaseUrl).origin;
    const onMessage = (event: MessageEvent) => {
      if (event.origin !== expectedOrigin || event.source !== popupRef.current) return;
      const data = event.data as { type?: unknown; token?: unknown } | null;
      if (!data || data.type !== "media-broker-auth" || typeof data.token !== "string" || !data.token) return;
      setToken(data.token);
      popupRef.current = null;
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [configuredBaseUrl]);

  const withSession = useCallback(async <T,>(call: (base: string, bearer: string) => Promise<T>): Promise<T> => {
    if (!configuredBaseUrl || !token) throw unauthenticated();
    try {
      return await call(configuredBaseUrl, token);
    } catch (error) {
      if (error instanceof BrokerHttpError && error.status === 401) setToken(null);
      throw error;
    }
  }, [configuredBaseUrl, token]);

  const submitFeedback = useCallback(
    (input: FeedbackEditInput) => withSession((base, bearer) => postFeedback(base, bearer, input)),
    [withSession],
  );
  const getOperationStatus = useCallback(
    (operationId: string) => withSession((base, bearer) => fetchOperationStatus(base, bearer, operationId)),
    [withSession],
  );

  const value = useMemo<BrokerSessionValue>(() => ({
    configured: configuredBaseUrl !== null,
    authenticated: token !== null,
    login,
    logout,
    submitFeedback,
    getOperationStatus,
  }), [configuredBaseUrl, token, login, logout, submitFeedback, getOperationStatus]);

  return <BrokerSessionContext.Provider value={value}>{children}</BrokerSessionContext.Provider>;
}

export function useBrokerSession(): BrokerSessionValue {
  const value = useContext(BrokerSessionContext);
  if (!value) throw new Error("Broker session context is unavailable");
  return value;
}
