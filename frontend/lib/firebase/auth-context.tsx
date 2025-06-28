'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import {
  User,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  updateProfile,
} from 'firebase/auth';
import { auth } from './config';
import { useRouter } from 'next/navigation';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, name: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    if (!auth) {
      // Firebase not configured, set loading to false and skip auth
      setLoading(false);
      return;
    }

    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      setUser(user);
      setLoading(false);
      
      if (user) {
        // Get the ID token to send to backend
        const token = await user.getIdToken();
        
        // Store token in cookie for server-side requests
        document.cookie = `firebase-token=${token}; path=/; max-age=3600; SameSite=Lax`;
      } else {
        // Clear token cookie
        document.cookie = 'firebase-token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC;';
      }
    });

    return () => unsubscribe();
  }, []);

  const signIn = async (email: string, password: string) => {
    if (!auth) {
      throw new Error('Firebase authentication is not configured');
    }
    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      const token = await userCredential.user.getIdToken();
      
      // Call backend to sync user data
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/firebase-signin`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          uid: userCredential.user.uid,
          email: userCredential.user.email,
          name: userCredential.user.displayName || email.split('@')[0],
        }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        // If user doesn't exist in database, create them
        if (data.message === 'User not found. Please sign up first.') {
          const signupResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/firebase-signup`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({
              uid: userCredential.user.uid,
              email: userCredential.user.email,
              name: userCredential.user.displayName || email.split('@')[0],
            }),
          });
          
          if (signupResponse.ok) {
            router.push('/auth/signup/llm-setup');
            return;
          }
        }
        console.error('Sign in error:', data);
      }
      
      // Redirect based on setup status
      if (!data.is_setup_complete) {
        router.push('/auth/complete-setup');
      } else {
        router.push('/auth/signin/validate');
      }
    } catch (error) {
      console.error('Sign in error:', error);
      throw error;
    }
  };

  const signUp = async (email: string, password: string, name: string) => {
    if (!auth) {
      throw new Error('Firebase authentication is not configured');
    }
    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      
      // Update the user's display name
      await updateProfile(userCredential.user, { displayName: name });
      
      const token = await userCredential.user.getIdToken();
      
      // Call backend to create user record
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/firebase-signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          uid: userCredential.user.uid,
          email: userCredential.user.email,
          name: name,
        }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        console.error('Backend response:', data);
        // If backend fails, still continue since Firebase user was created
        // The backend will create the user record on next sign-in
      }

      // Redirect to LLM setup
      router.push('/auth/signup/llm-setup');
    } catch (error: any) {
      console.error('Sign up error:', error);
      
      // If it's a Firebase error about existing user, try to sign in instead
      if (error.code === 'auth/email-already-in-use') {
        // User exists in Firebase, just sign them in
        try {
          await signIn(email, password);
          return;
        } catch (signInError) {
          console.error('Sign in after failed signup:', signInError);
        }
      }
      
      throw error;
    }
  };

  const signOut = async () => {
    if (!auth) {
      // Just redirect if Firebase is not configured
      router.push('/sign-in');
      return;
    }
    try {
      await firebaseSignOut(auth);
      router.push('/sign-in');
    } catch (error) {
      console.error('Sign out error:', error);
      throw error;
    }
  };

  const refreshToken = async (): Promise<string | null> => {
    if (!auth || !user) {
      return null;
    }
    try {
      return await user.getIdToken(true);
    } catch (error) {
      console.error('Error refreshing token:', error);
      return null;
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signUp, signOut, refreshToken }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}