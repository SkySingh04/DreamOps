import { Suspense } from 'react';
import { FirebaseLogin } from '../firebase-login';

export default function SignInPage() {
  return (
    <Suspense>
      <FirebaseLogin mode="signin" />
    </Suspense>
  );
}