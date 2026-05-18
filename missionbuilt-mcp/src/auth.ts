/**
 * OAuth handler for the Mission Built MCP server.
 *
 * Google OAuth 2.1 via @cloudflare/workers-oauth-provider. The library
 * handles /.well-known/oauth-authorization-server, /token, and /register.
 * This handler is responsible for /authorize, /google/callback, and all
 * public routes (landing, preview, health, brand.css, favicon).
 *
 * Flow:
 *   1. Claude redirects user to /authorize with OAuth params
 *   2. We redirect to Google for sign-in
 *   3. Google redirects back to /google/callback with auth code
 *   4. We exchange the code with Google for user identity
 *   5. We call OAUTH_PROVIDER.completeAuthorization() with the user info
 *   6. Library issues an MCP auth code and redirects back to Claude
 */

import type { OAuthHelpers } from "@cloudflare/workers-oauth-provider";
import { z } from "zod";
import { brandCss, STENCIL } from "./design";
import { renderLanding } from "./landing";
import { renderPreview } from "./preview";
import { SERVER_VERSION } from "./constants";
import WARMUP_SHELL_JS from "./warmup-shell.rawjs";
import APPROACH_SHELL_JS from "./approach-shell.rawjs";
import SPOTTER_SHELL_JS from "./spotter-shell.rawjs";

// ── Google API response schemas ───────────────────────────────────────────────

const GoogleTokenSchema = z.object({
  access_token: z.string(),
  token_type: z.string().optional(),
  expires_in: z.number().optional(),
  scope: z.string().optional(),
});

const GoogleUserInfoSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  name: z.string().optional(),
  picture: z.string().url().optional(),
  verified_email: z.boolean().optional(),
});

const GITHUB_URL = "https://github.com/missionbuilt/loadout";

export interface AuthEnv {
  OAUTH_PROVIDER: OAuthHelpers;
  OAUTH_KV: KVNamespace;
  GOOGLE_CLIENT_ID: string;
  GOOGLE_CLIENT_SECRET: string;
  COOKIE_ENCRYPTION_KEY: string;
}

export interface UserProps extends Record<string, unknown> {
  email: string;
  name: string;
  picture?: string;
  sub: string;
}

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
        renderLanding({ origin: url.origin, githubUrl: GITHUB_URL, stencil: STENCIL }),
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

    // Favicon — all paths browsers and OS fetchers probe
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
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" fill="#171513"/>
  <rect x="6" y="13" width="6" height="6" fill="#a8211a"/>
  <rect x="13" y="15" width="6" height="2" fill="#ebe5d8"/>
  <rect x="20" y="13" width="6" height="6" fill="#a8211a"/>
</svg>`;
      return new Response(svg, {
        headers: { "Content-Type": "image/svg+xml", "Cache-Control": "public, max-age=86400" },
      });
    }

    if (url.pathname === "/site.webmanifest" || url.pathname === "/manifest.json") {
      return new Response(
        JSON.stringify({
          name: "Mission Built",
          short_name: "Loadout",
          icons: [{ src: "/favicon.svg", sizes: "any", type: "image/svg+xml" }],
          theme_color: "#171513",
          background_color: "#171513",
          display: "standalone",
        }),
        { headers: { "Content-Type": "application/manifest+json", "Cache-Control": "public, max-age=3600" } }
      );
    }

    if (url.pathname === "/health") {
      return new Response(
        JSON.stringify({ ok: true, server: "missionbuilt-mcp", server_version: SERVER_VERSION, status: "online" }, null, 2),
        { headers: { "Content-Type": "application/json" } }
      );
    }

    // Shell JS assets — served verbatim so artifact HTML can load them via <script src>
    if (url.pathname === "/warmup-shell.js") {
      if (request.method !== "GET" && request.method !== "HEAD") {
        return new Response("Method Not Allowed", { status: 405, headers: { "Allow": "GET, HEAD" } });
      }
      return new Response(request.method === "HEAD" ? null : WARMUP_SHELL_JS, {
        headers: {
          "Content-Type": "application/javascript; charset=utf-8",
          "Cache-Control": "public, max-age=3600",
          "Access-Control-Allow-Origin": "*",
        },
      });
    }

    if (url.pathname === "/approach-shell.js") {
      if (request.method !== "GET" && request.method !== "HEAD") {
        return new Response("Method Not Allowed", { status: 405, headers: { "Allow": "GET, HEAD" } });
      }
      return new Response(request.method === "HEAD" ? null : APPROACH_SHELL_JS, {
        headers: {
          "Content-Type": "application/javascript; charset=utf-8",
          "Cache-Control": "public, max-age=3600",
          "Access-Control-Allow-Origin": "*",
        },
      });
    }

    if (url.pathname === "/spotter-shell.js") {
      if (request.method !== "GET" && request.method !== "HEAD") {
        return new Response("Method Not Allowed", { status: 405, headers: { "Allow": "GET, HEAD" } });
      }
      return new Response(request.method === "HEAD" ? null : SPOTTER_SHELL_JS, {
        headers: {
          "Content-Type": "application/javascript; charset=utf-8",
          "Cache-Control": "public, max-age=3600",
          "Access-Control-Allow-Origin": "*",
        },
      });
    }

    return new Response("Not found", { status: 404 });
  },
};

async function handleAuthorize(request: Request, env: AuthEnv): Promise<Response> {
  const oauthReqInfo = await env.OAUTH_PROVIDER.parseAuthRequest(request);
  if (!oauthReqInfo.clientId) {
    return errorPage("Missing client_id in authorization request.");
  }

  // Explicitly extract all known fields before serializing — parseAuthRequest
  // may return a class instance with getters that JSON.stringify drops.
  const stateKey = crypto.randomUUID();
  const serializable = {
    clientId:            oauthReqInfo.clientId,
    redirectUri:         oauthReqInfo.redirectUri,
    scope:               oauthReqInfo.scope,
    state:               oauthReqInfo.state,
    codeChallenge:       oauthReqInfo.codeChallenge,
    codeChallengeMethod: oauthReqInfo.codeChallengeMethod,
    responseType:        oauthReqInfo.responseType,
    resource:            oauthReqInfo.resource,
  };
  await env.OAUTH_KV.put(`pending_auth:${stateKey}`, JSON.stringify(serializable), {
    expirationTtl: 300,
  });

  const params = new URLSearchParams({
    client_id: env.GOOGLE_CLIENT_ID,
    redirect_uri: new URL(request.url).origin + "/google/callback",
    response_type: "code",
    scope: "openid email profile",
    state: stateKey,
  });

  return Response.redirect(`https://accounts.google.com/o/oauth2/v2/auth?${params}`, 302);
}

async function handleGoogleCallback(request: Request, env: AuthEnv): Promise<Response> {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const stateKey = url.searchParams.get("state");

  if (!code || !stateKey) {
    return errorPage("Missing code or state from Google callback.");
  }

  // Retrieve the original oauthReqInfo from KV using the state UUID.
  const stored = await env.OAUTH_KV.get(`pending_auth:${stateKey}`);
  if (!stored) {
    return errorPage("Auth state expired or invalid. Please try connecting again.");
  }
  await env.OAUTH_KV.delete(`pending_auth:${stateKey}`);

  let oauthReqInfo: any;
  try {
    oauthReqInfo = JSON.parse(stored);
  } catch {
    return errorPage("Corrupted auth state. Please try connecting again.");
  }

  // Exchange code for tokens
  const tokenRes = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code,
      client_id: env.GOOGLE_CLIENT_ID,
      client_secret: env.GOOGLE_CLIENT_SECRET,
      redirect_uri: url.origin + "/google/callback",
      grant_type: "authorization_code",
    }),
  });

  if (!tokenRes.ok) {
    return errorPage("Failed to exchange code with Google.");
  }

  const tokensRaw: unknown = await tokenRes.json();
  const tokensParsed = GoogleTokenSchema.safeParse(tokensRaw);
  if (!tokensParsed.success) {
    return errorPage("Unexpected response from Google token endpoint. Please try again.");
  }
  const tokens = tokensParsed.data;

  // Fetch user identity
  const userRes = await fetch("https://www.googleapis.com/oauth2/v2/userinfo", {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  });

  if (!userRes.ok) {
    return errorPage("Failed to fetch user identity from Google.");
  }

  const userInfoRaw: unknown = await userRes.json();
  const userInfoParsed = GoogleUserInfoSchema.safeParse(userInfoRaw);
  if (!userInfoParsed.success) {
    return errorPage("Unexpected user identity response from Google. Please try again.");
  }
  const userInfo = userInfoParsed.data;

  const props: UserProps = {
    email: userInfo.email,
    name: userInfo.name ?? userInfo.email,
    picture: userInfo.picture,
    sub: userInfo.id,
  };

  // completeAuthorization expects `request` to be the parsed AuthRequest
  // (oauthReqInfo), NOT the HTTP Request object. The library destructures
  // clientId and redirectUri directly from options.request.
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
  <title>Mission Built · Sign-in error</title>
  <style>${brandCss()}</style>
</head>
<body>
  <div class="mb-container">
    <p class="mb-stencil"><span class="mb-stencil-bars">${STENCIL}</span> Sign-in error</p>
    <h1 class="mb-hero">Something didn't connect<span class="mb-hero-period">.</span></h1>
    <p class="mb-tagline">${escapeHtml(message)}</p>
    <p class="mb-p" style="margin-top: 2rem;"><a class="mb-link" href="/">← Back</a></p>
    <div class="mb-footer">
      <p class="mb-footer-line">Real strength is lifting others.</p>
    </div>
  </div>
</body>
</html>`;

  return new Response(html, { status: 400, headers: { "Content-Type": "text/html; charset=utf-8" } });
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
