'use server';

import { z } from 'zod';
import { redirect } from 'next/navigation';
import { validatedAction } from '@/lib/auth/middleware';

// Note: With Firebase Auth, most of the authentication logic is handled client-side
// These server actions are now simplified and mainly handle redirects

const signInSchema = z.object({
  email: z.string().email().min(3).max(255),
  password: z.string().min(8).max(100)
});

export const signIn = validatedAction(signInSchema, async (data, formData) => {
  // Firebase authentication is handled client-side
  // This action is kept for form validation and potential server-side operations
  return {
    success: true,
    email: data.email,
  };
});

const signUpSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  email: z.string().email(),
  password: z.string().min(8),
  inviteId: z.string().optional()
});

export const signUp = validatedAction(signUpSchema, async (data, formData) => {
  // Firebase authentication is handled client-side
  // This action is kept for form validation and potential server-side operations
  return {
    success: true,
    email: data.email,
    name: data.name,
  };
});

// Sign out is now handled entirely client-side through Firebase
export async function signOut() {
  // This function is kept for compatibility but the actual sign out
  // is handled by Firebase client SDK
  redirect('/sign-in');
}

const updatePasswordSchema = z.object({
  currentPassword: z.string().min(8).max(100),
  newPassword: z.string().min(8).max(100),
  confirmPassword: z.string().min(8).max(100)
});

export const updatePassword = validatedAction(
  updatePasswordSchema,
  async (data) => {
    const { currentPassword, newPassword, confirmPassword } = data;

    if (newPassword !== confirmPassword) {
      return {
        error: 'The passwords did not match.',
        currentPassword,
        newPassword,
        confirmPassword
      };
    }

    // Password update will be handled through Firebase Auth
    return {
      error: 'Password update should be handled through Firebase Auth.',
      currentPassword,
      newPassword,
      confirmPassword
    };
  }
);

const updateAccountSchema = z.object({
  name: z.string().min(1).max(100),
  email: z.string().email()
});

export const updateAccount = validatedAction(
  updateAccountSchema,
  async (data) => {
    // Account updates will be handled through Firebase Auth and the backend API
    return {
      error: 'Account updates should be handled through Firebase Auth and the backend API.',
      name: data.name,
      email: data.email
    };
  }
);

const deleteAccountSchema = z.object({
  confirmation: z.string().refine((val) => val === 'DELETE', {
    message: 'Please type DELETE to confirm'
  })
});

export const deleteAccount = validatedAction(
  deleteAccountSchema,
  async (data) => {
    // Account deletion will be handled through Firebase Auth and the backend API
    return {
      error: 'Account deletion should be handled through Firebase Auth and the backend API.'
    };
  }
);