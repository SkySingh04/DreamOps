'use server';

// Auth removed - these are stub actions since authentication is handled by Authentik
// User management should be done through Authentik, not through the application

export async function updateAccount(prevState: any, formData: FormData) {
  return {
    error: 'Account management is handled through Authentik. Please contact your administrator.'
  };
}

export async function updatePassword(prevState: any, formData: FormData) {
  return {
    error: 'Password management is handled through Authentik. Please use the Authentik portal to change your password.'
  };
}

export async function deleteAccount(prevState: any, formData: FormData) {
  return {
    error: 'Account deletion is handled through Authentik. Please contact your administrator.'
  };
}
