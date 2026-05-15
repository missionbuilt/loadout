/**
 * OAuth handler for The Warmup MCP server.
 *
 * Identical flow to The Spotter's auth.ts — Google OAuth 2.1 via
 * @cloudflare/workers-oauth-provider. Only the branding constants,
 * page routes, and manifest content differ.
 *
 * Flow:
 *   1. Claude Desktop redirects user to /authorize with OAuth params
 *   2. We redirect to Google for sign-in
 *   3. Google redirects back to /google/callback with auth code
 *   4. We exchange the code with Google for user identity
 *   5. We call OAUTH_PROVIDER.completeAuthorization() with the user info
 *   6. Library issues an MCP auth code and redirects back to Claude Desktop
 */

import type { OAuthHelpers } from "@cloudflare/workers-oauth-provider";
import { brandCss, STENCIL } from "./design";
import { renderLanding } from "./landing";
import { renderPreview } from "./preview";

const WARMUP_VERSION = "0.1.0";
const SERVER_VERSION = "0.1.0";
const GITHUB_URL = "https://github.com/missionbuilt/loadout";

export interface AuthEnv {
  OAUTH_PROVIDER: OAuthHelpers;
  GOOGLE_CLIENT_ID: string;
  GOOGLE_CLIENT_SECRET: string;
  COOKIE_ENCRYPTION_KEY: string;
}

export interface UserProps extends Record<string, unknown> {
  email: string;
  name: string;
  picture?: string;
  sub: string; // Google's stable user identifier
}

/**
 * Default handler — receives any request that isn't an OAuth protocol
 * endpoint (/.well-known/oauth-authorization-server, /token, /register).
 */
export const authHandler = {
  async fetch(request: Request, env: AuthEnv, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    // OAuth flow
    if (url.pathname === "/authorize") {
      return handleAuthorize(request, env);
    }

    if (url.pathname === "/google/callback") {
      return handleGoogleCallback(request, env);
    }

    // Public routes
    if (url.pathname === "/" || url.pathname === "/index.html") {
      return new Response(
        renderLanding({
          origin: url.origin,
          githubUrl: GITHUB_URL,
          warmupVersion: WARMUP_VERSION,
          serverVersion: SERVER_VERSION,
          stencil: STENCIL,
        }),
        { headers: { "Content-Type": "text/html; charset=utf-8" } }
      );
    }

    if (url.pathname === "/preview") {
      return new Response(renderPreview({ origin: url.origin, githubUrl: GITHUB_URL }), {
        headers: { "Content-Type": "text/html; charset=utf-8" },
      });
    }

    if (url.pathname === "/brand.css") {
      return new Response(brandCss(), {
        headers: {
          "Content-Type": "text/css; charset=utf-8",
          "Cache-Control": "public, max-age=3600",
          "Access-Control-Allow-Origin": "*",
        },
      });
    }

    // Favicon — served at every common path browsers and OS-level fetchers probe
    if (
      url.pathname === "/favicon.svg" ||
      url.pathname === "/favicon.ico" ||
      url.pathname === "/favicon.png" ||
      url.pathname === "/favicon-16x16.png" ||
      url.pathname === "/favicon-32x32.png" ||
      url.pathname === "/favicon-96x96.png" ||
      url.pathname === "/favicon-192x192.png" ||
      url.pathname === "/apple-touch-icon.png" ||
      url.pathname === "/apple-touch-icon-precomposed.png" ||
      url.pathname === "/apple-touch-icon-120x120.png" ||
      url.pathname === "/apple-touch-icon-152x152.png" ||
      url.pathname === "/apple-touch-icon-180x180.png" ||
      url.pathname === "/android-chrome-192x192.png" ||
      url.pathname === "/android-chrome-512x512.png"
    ) {
      // The canonical Mission Built favicon — barbell with two red plates
      // and a cream bar on warm charcoal. Matches missionbuilt.io exactly.
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" fill="#171513"/>
  <rect x="6" y="13" width="6" height="6" fill="#a8211a"/>
  <rect x="13" y="15" width="6" height="2" fill="#ebe5d8"/>
  <rect x="20" y="13" width="6" height="6" fill="#a8211a"/>
</svg>`;
      return new Response(svg, {
        headers: {
          "Content-Type": "image/svg+xml",
          "Cache-Control": "public, max-age=86400",
        },
      });
    }

    if (url.pathname === "/site.webmanifest" || url.pathname === "/manifest.json") {
      return new Response(
        JSON.stringify({
          name: "The Warmup",
          short_name: "Warmup",
          icons: [
            { src: "/favicon.svg", sizes: "any", type: "image/svg+xml" },
          ],
          theme_color: "#171513",
          background_color: "#171513",
          display: "standalone",
        }),
        {
          headers: {
            "Content-Type": "application/manifest+json",
            "Cache-Control": "public, max-age=3600",
          },
        }
      );
    }

    if (url.pathname === "/health") {
      return new Response(
        JSON.stringify(
          {
            ok: true,
            server: "the-warmup-mcp",
            server_version: SERVER_VERSION,
            warmup_version: WARMUP_VERSION,
            auth: "oauth-google",
            transports: { sse: "/sse", streamable_http: "/mcp" },
            github: GITHUB_URL,
          },
          null,
          2
        ),
        { headers: { "Content-Type": "application/json" } }
      );
    }

    return new Response("Not Found", { status: 404 });
  },
};

async function handleAuthorize(request: Request, env: AuthEnv): Promise<Response> {
  const oauthReqInfo = await env.OAUTH_PROVIDER.parseAuthRequest(request);
  const stateForGoogle = btoa(JSON.stringify(oauthReqInfo));
  const url = new URL(request.url);
  const redirectUri = `${url.origin}/google/callback`;

  const googleAuthUrl = new URL("https://accounts.google.com/o/oauth2/v2/auth");
  googleAuthUrl.searchParams.set("client_id", env.GOOGLE_CLIENT_ID);
  googleAuthUrl.searchParams.set("redirect_uri", redirectUri);
  googleAuthUrl.searchParams.set("response_type", "code");
  googleAuthUrl.searchParams.set("scope", "openid email profile");
  googleAuthUrl.searchParams.set("state", stateForGoogle);
  googleAuthUrl.searchParams.set("access_type", "online");
  googleAuthUrl.searchParams.set("prompt", "select_account");

  return Response.redirect(googleAuthUrl.toString(), 302);
}

async function handleGoogleCallback(request: Request, env: AuthEnv): Promise<Response> {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const stateRaw = url.searchParams.get("state");

  if (!code || !stateRaw) {
    return errorPage("Missing code or state in Google callback. Try again from your MCP client.");
  }

  let oauthReqInfo;
  try {
    oauthReqInfo = JSON.parse(atob(stateRaw));
  } catch {
    return errorPage("Invalid state in Google callback. The auth request may have expired.");
  }

  const redirectUri = `${url.origin}/google/callback`;
  const tokenResponse = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code,
      client_id: env.GOOGLE_CLIENT_ID,
      client_secret: env.GOOGLE_CLIENT_SECRET,
      redirect_uri: redirectUri,
      grant_type: "authorization_code",
    }),
  });

  if (!tokenResponse.ok) {
    const errText = await tokenResponse.text();
    return errorPage(`Google rejected the authorization code: ${errText}`);
  }

  const tokens = (await tokenResponse.json()) as { access_token: string };

  const userInfoResponse = await fetch("https://www.googleapis.com/oauth2/v2/userinfo", {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  });

  if (!userInfoResponse.ok) {
    return errorPage("Could not fetch user identity from Google.");
  }

  const userInfo = (await userInfoResponse.json()) as {
    id: string;
    email: string;
    name?: string;
    picture?: string;
  };

  const props: UserProps = {
    sub: userInfo.id,
    email: userInfo.email,
    name: userInfo.name ?? userInfo.email,
    picture: userInfo.picture,
  };

  const { redirectTo } = await env.OAUTH_PROVIDER.completeAuthorization({
    request: oauthReqInfo,
    userId: userInfo.id,
    metadata: { label: userInfo.name ?? userInfo.email },
    scope: oauthReqInfo.scope,
    props,
  });

  return Response.redirect(redirectTo, 302);
}

function errorPage(message: string): Response {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#171513">
  <title>The Warmup · Sign-in error</title>
  <style>${brandCss()}</style>
</head>
<body>
  <div class="mb-container">
    <p class="mb-stencil"><span class="mb-stencil-bars">${STENCIL}</span> Sign-in error</p>
    <h1 class="mb-hero">Something didn't connect<span class="mb-hero-period">.</span></h1>
    <p class="mb-tagline">${escapeHtml(message)}</p>
    <p class="mb-p" style="margin-top: 2rem;"><a class="mb-link" href="/">← Back to The Warmup</a></p>
    <div class="mb-footer">
      <p class="mb-footer-line">Know what moved. Then go move things.</p>
    </div>
  </div>
</body>
</html>`;

  return new Response(html, {
    status: 400,
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
