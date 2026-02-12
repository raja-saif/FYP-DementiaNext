import NextAuth from 'next-auth'
import GoogleProvider from 'next-auth/providers/google'

// Check if Google OAuth credentials are properly configured
const isGoogleConfigured = process.env.GOOGLE_CLIENT_ID && 
  process.env.GOOGLE_CLIENT_SECRET && 
  process.env.GOOGLE_CLIENT_ID !== 'your-google-client-id' &&
  process.env.GOOGLE_CLIENT_SECRET !== 'your-google-client-secret'

const providers = []

// Only add Google provider if properly configured
if (isGoogleConfigured) {
  providers.push(
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    })
  )
}

const handler = NextAuth({
  providers,
  callbacks: {
    async signIn({ user, account, profile }) {
      if (account?.provider === 'google') {
        // You can add custom logic here to determine user role
        // For now, we'll default to patient role
        (user as any).role = 'patient'
      }
      return true
    },
    async jwt({ token, user }) {
      if (user) {
        (token as any).role = (user as any).role
      }
      return token
    },
    async session({ session, token }) {
      if (token && session.user) {
        (session.user as any).role = (token as any).role;
        (session.user as any).id = token.sub
      }
      return session
    },
  },
  pages: {
    signIn: '/login',
    error: '/login?error=OAuthSignin',
  },
  debug: process.env.NODE_ENV === 'development',
})

export { handler as GET, handler as POST }
