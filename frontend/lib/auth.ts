/**
 * NextAuth configuration.
 *
 * Flow:
 *   1. CredentialsProvider.authorize() → POST /api/auth/login on the backend.
 *   2. Backend returns { access_token, user }.
 *   3. jwt() callback stores access_token in the NextAuth JWT cookie.
 *   4. session() callback exposes it as session.accessToken.
 *   5. Frontend passes session.accessToken as "Authorization: Bearer <token>".
 *   6. Backend decodes with JWT_SECRET (security.py).
 */
import type { NextAuthOptions } from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

interface BackendTokenResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    name: string | null;
    role: string;
    plan: string;
  };
}

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'credentials',
      credentials: {
        email:    { label: 'Email',    type: 'email'    },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        try {
          const res = await fetch(`${BASE_URL}/api/auth/login`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
              email:    credentials.email,
              password: credentials.password,
            }),
          });

          if (!res.ok) return null;

          const data = (await res.json()) as BackendTokenResponse;

          return {
            id:          data.user.id,
            email:       data.user.email,
            name:        data.user.name ?? undefined,
            accessToken: data.access_token,
          };
        } catch {
          return null;
        }
      },
    }),
  ],

  callbacks: {
    async jwt({ token, user }) {
      // `user` is only populated on the first sign-in
      if (user && 'accessToken' in user) {
        token.accessToken = user.accessToken as string;
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken;
      return session;
    },
  },

  pages: {
    signIn: '/login',
    error:  '/login',
  },

  session: {
    strategy: 'jwt',
    maxAge:   7 * 24 * 60 * 60,  // 7 days — matches backend token expiry
  },

  secret: process.env.NEXTAUTH_SECRET,
};
