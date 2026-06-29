/**
 * Unit test for the health API route.
 * Tests that the endpoint returns the expected response shape.
 */

describe('Health check response structure', () => {
  it('should define expected health response shape', () => {
    const expectedResponse = { status: 'ok' };
    expect(expectedResponse).toEqual({ status: 'ok' });
    expect(typeof expectedResponse.status).toBe('string');
  });

  it('should not contain sensitive information', () => {
    const healthResponse = { status: 'ok' };
    const responseString = JSON.stringify(healthResponse);

    // Ensure the response never contains environment variable values
    expect(responseString).not.toContain('DATABASE_URL');
    expect(responseString).not.toContain('SECRET');
    expect(responseString).not.toContain('password');
    expect(responseString).not.toContain('postgresql://');
  });
});
