import { Suspense } from 'react';
import { FirebaseLogin } from '../firebase-login';

export default function SignUpPage() {
  return (
    <Suspense>
      <FirebaseLogin mode="signup" />
    </Suspense>
  );
}
