import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { session_id } = req.body;

  if (!session_id) {
    return res.status(400).json({ error: 'Missing session_id' });
  }

  try {
    // Proxy the request to the backend to avoid CORS issues
    // http://127.0.0.1:5000/vscode-auth 
    const response = await fetch('https://cs-15-tutor.onrender.c/vscode-auth', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Development-Mode': 'true',
        'X-Remote-User': 'dev_user' // Use dev user in development mode
      },
      body: JSON.stringify({
        session_id: session_id
      })
    });

    const data = await response.json();

    if (response.ok) {
      return res.status(200).json(data);
    } else {
      console.error('Backend authentication failed:', data);
      return res.status(response.status).json(data);
    }
  } catch (error) {
    console.error('Proxy authentication error:', error);
    return res.status(500).json({ 
      error: 'Failed to complete authentication',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
} 