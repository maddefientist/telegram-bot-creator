import { NextResponse } from 'next/server';

export const runtime = 'edge';

export async function GET() {
  const apiUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL;

  let apiStatus = 'unknown';
  let apiHealthy = false;

  if (apiUrl) {
    try {
      const response = await fetch(`${apiUrl}/health`, {
        next: { revalidate: 0 },
      });

      if (response.ok) {
        const data = await response.json();
        apiStatus = data.status || 'healthy';
        apiHealthy = true;
      } else {
        apiStatus = `error: ${response.status}`;
      }
    } catch (error) {
      apiStatus = `unreachable: ${error instanceof Error ? error.message : 'unknown'}`;
    }
  } else {
    apiStatus = 'not configured';
  }

  return NextResponse.json({
    status: apiHealthy ? 'healthy' : 'degraded',
    timestamp: new Date().toISOString(),
    service: 'web',
    version: '1.0.0',
    checks: {
      api: apiStatus,
    },
  }, {
    status: apiHealthy ? 200 : 503,
  });
}
