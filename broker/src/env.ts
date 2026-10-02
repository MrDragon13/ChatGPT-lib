export type RateLimitBinding = {
  limit(options: { key: string }): Promise<{ success: boolean }>;
};

export type BrokerEnv = {
  REPO_OWNER: string;
  REPO_NAME: string;
  ALLOWED_ORIGIN: string;
  GITHUB_APP_ID?: string;
  GITHUB_APP_CLIENT_ID?: string;
  GITHUB_APP_INSTALLATION_ID?: string;
  OWNER_GITHUB_USER_ID?: string;
  GITHUB_APP_PRIVATE_KEY?: string;
  GITHUB_APP_CLIENT_SECRET?: string;
  BROKER_SESSION_SECRET?: string;
  AUTH_RATE_LIMITER: RateLimitBinding;
  WRITE_RATE_LIMITER: RateLimitBinding;
};
