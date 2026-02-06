import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';

export default function VscodeAuth() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [authStatus, setAuthStatus] = useState<'loading' | 'ready' | 'completing' | 'completed' | 'error'>('loading');

  useEffect(() => {
    // Get session_id from URL parameters
    const { session_id } = router.query;
    if (session_id && typeof session_id === 'string') {
      setSessionId(session_id);
      setAuthStatus('ready');
    } else if (router.isReady) {
      setAuthStatus('error');
    }
  }, [router.query, router.isReady]);

  // Handle VSCode authentication completion
  const handleCompleteAuth = async () => {
    if (!sessionId) return;

    setAuthStatus('completing');

    try {
      // Complete the authentication flow using our proxy API route to avoid CORS
      const response = await fetch('/api/complete-vscode-auth', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: sessionId
        })
      });

      if (response.ok) {
        setAuthStatus('completed');
        // Auto-close this tab after a delay
        setTimeout(() => {
          window.close();
        }, 3000);
      } else {
        console.error('Authentication failed:', await response.text());
        setAuthStatus('error');
      }
    } catch (error) {
      console.error('VSCode authentication error:', error);
      setAuthStatus('error');
    }
  };

  if (authStatus === 'loading') {
    return (
      <div className="flex items-center justify-center min-h-screen w-full bg-cs-mint">
        <div className="text-center bg-white p-8 rounded-lg shadow-xl max-w-md">
          <h2 className="text-2xl font-bold mb-4">Loading...</h2>
          <p className="text-gray-600">Preparing VSCode authentication...</p>
        </div>
      </div>
    );
  }

  if (authStatus === 'ready') {
    return (
      <div className="flex items-center justify-center min-h-screen w-full bg-cs-mint">
        <div className="text-center bg-white p-8 rounded-lg shadow-xl max-w-md">
          <h2 className="text-2xl font-bold mb-4">CS 15 Tutor VSCode Authentication</h2>
          <p className="mb-6 text-gray-600">
            Click the button below to complete authentication for the CS 15 Tutor VSCode extension.
          </p>
          <button
            onClick={handleCompleteAuth}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            Complete Authentication
          </button>
          <p className="mt-4 text-sm text-gray-500">
            This will authenticate your VSCode extension and you can close this tab afterwards.
          </p>
        </div>
      </div>
    );
  }

  if (authStatus === 'completing') {
    return (
      <div className="flex items-center justify-center min-h-screen w-full bg-cs-mint">
        <div className="text-center bg-white p-8 rounded-lg shadow-xl max-w-md">
          <h2 className="text-2xl font-bold mb-4">Completing Authentication...</h2>
          <div className="flex justify-center mb-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
          <p className="text-gray-600">Please wait while we complete your authentication...</p>
        </div>
      </div>
    );
  }

  if (authStatus === 'completed') {
    return (
      <div className="flex items-center justify-center min-h-screen w-full bg-cs-mint">
        <div className="text-center bg-white p-8 rounded-lg shadow-xl max-w-md">
          <h2 className="text-2xl font-bold mb-4 text-green-600">✅ Authentication Complete!</h2>
          <p className="mb-4 text-gray-600">
            Your VSCode extension has been successfully authenticated.
          </p>
          <p className="text-sm text-gray-500">
            You can now close this tab and use the CS 15 Tutor in VSCode.
          </p>
        </div>
      </div>
    );
  }

  // Error state
  return (
    <div className="flex items-center justify-center min-h-screen w-full bg-cs-mint">
      <div className="text-center bg-white p-8 rounded-lg shadow-xl max-w-md">
        <h2 className="text-2xl font-bold mb-4 text-red-600">❌ Authentication Error</h2>
        <p className="mb-6 text-gray-600">
          There was an error with the authentication process. Please try again.
        </p>
        <button
          onClick={() => window.close()}
          className="bg-red-600 text-white px-6 py-3 rounded-lg hover:bg-red-700 transition-colors font-medium"
        >
          Close Tab
        </button>
      </div>
    </div>
  );
} 