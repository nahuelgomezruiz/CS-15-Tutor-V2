import * as vscode from 'vscode';
import * as http from 'http';
import fetch from 'node-fetch';
import { Client } from 'ssh2';


export interface AuthToken {
    token: string;
    utln: string;
    expiresAt: Date;
}

export class AuthManager {
    private static readonly TOKEN_KEY = 'cs15-tutor.authToken';
    private static readonly UTLN_KEY = 'cs15-tutor.utln';
    private static readonly EXPIRES_KEY = 'cs15-tutor.tokenExpires';
    private context: vscode.ExtensionContext;
    private apiBaseUrl: string;

    constructor(context: vscode.ExtensionContext, apiBaseUrl: string = 'https://cs-15-tutor.onrender.com') {
        this.context = context;
        this.apiBaseUrl = apiBaseUrl;
    }

    /**
     * Check if user is currently authenticated
     */
    public isAuthenticated(): boolean {
        const token = this.getStoredToken();
        if (!token) {
            return false;
        }

        // Check if token is expired
        const now = new Date();
        if (now >= token.expiresAt) {
            this.clearAuthentication();
            return false;
        }

        return true;
    }

    /**
     * Get the current authentication token
     */
    public getAuthToken(): string | null {
        const token = this.getStoredToken();
        return token ? token.token : null;
    }

    /**
     * Get the current user's UTLN
     */
    public getUtln(): string | null {
        const token = this.getStoredToken();
        return token ? token.utln : null;
    }

    /**
     * Helper to check SSH credentials
     */
    private async checkSshCredentials(username: string, password: string, host: string): Promise<boolean> {
        return new Promise((resolve) => {
            const conn = new Client();
            conn.on('ready', () => {
                conn.end();
                resolve(true);
            }).on('error', () => {
                resolve(false);
            }).connect({
                host: host,
                port: 22,
                username: username,
                password: password,
                readyTimeout: 5000
            });
        });
    }

    /**
     * Initiate the authentication process (now with SSH check)
     */
    public async authenticate(): Promise<boolean> {
        try {
            // Prompt for username
            const username = await vscode.window.showInputBox({
                prompt: 'Enter your EECS username',
                placeHolder: 'e.g., vhenao01',
                ignoreFocusOut: true,
                validateInput: (value: string) => {
                    if (!value || value.trim().length === 0) {
                        return 'Username is required';
                    }
                    return undefined;
                }
            });
            if (!username) {
                vscode.window.showInformationMessage('Authentication cancelled');
                return false;
            }
            // Prompt for password
            const password = await vscode.window.showInputBox({
                prompt: 'Enter your EECS password',
                password: true,
                ignoreFocusOut: true
            });
            if (!password) {
                vscode.window.showInformationMessage('Authentication cancelled');
                return false;
            }
            const host = 'homework.cs.tufts.edu';
            // Show progress while checking credentials
            const isValid = await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'Authenticating...',
                cancellable: false
            }, () => this.checkSshCredentials(username, password, host));
            if (isValid) {
                // After SSH success, proceed to backend auth (send only username)
                const authResult = await this.authenticateWithUsername(username.trim());
                if (authResult.success && authResult.token) {
                    const expiresAt = new Date();
                    expiresAt.setHours(expiresAt.getHours() + 24);
                    const authToken: AuthToken = {
                        token: authResult.token,
                        utln: authResult.username,
                        expiresAt
                    };
                    this.storeToken(authToken);
                    vscode.window.showInformationMessage(`Authentication successful! Welcome, ${authResult.username}`);
                    return true;
                } else {
                    vscode.window.showErrorMessage(authResult.error || 'Authentication failed');
                    return false;
                }
            } else {
                vscode.window.showErrorMessage('Authentication failed. Please check your credentials.');
                return false;
            }
        } catch (error) {
            console.error('Authentication error:', error);
            vscode.window.showErrorMessage(`Authentication failed: ${error}`);
            return false;
        }
    }

    /**
     * Clear stored authentication
     */
    public clearAuthentication(): void {
        this.context.globalState.update(AuthManager.TOKEN_KEY, undefined);
        this.context.globalState.update(AuthManager.UTLN_KEY, undefined);
        this.context.globalState.update(AuthManager.EXPIRES_KEY, undefined);
    }

    /**
     * Get stored authentication token
     */
    private getStoredToken(): AuthToken | null {
        const token = this.context.globalState.get<string>(AuthManager.TOKEN_KEY);
        const utln = this.context.globalState.get<string>(AuthManager.UTLN_KEY);
        const expiresAt = this.context.globalState.get<string>(AuthManager.EXPIRES_KEY);

        if (!token || !utln || !expiresAt) {
            return null;
        }

        return {
            token,
            utln,
            expiresAt: new Date(expiresAt)
        };
    }

    /**
     * Store authentication token
     */
    private storeToken(authToken: AuthToken): void {
        this.context.globalState.update(AuthManager.TOKEN_KEY, authToken.token);
        this.context.globalState.update(AuthManager.UTLN_KEY, authToken.utln);
        this.context.globalState.update(AuthManager.EXPIRES_KEY, authToken.expiresAt.toISOString());
    }

    /**
     * Authenticate user with username only against backend
     */
    private async authenticateWithUsername(username: string): Promise<any> {
        try {
            // Use the same endpoint but with development mode headers to bypass LDAP
            const response = await fetch(`${this.apiBaseUrl}/vscode-direct-auth`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-Development-Mode': 'true',
                    'X-Remote-User': username
                },
                body: JSON.stringify({ 
                    username, 
                    auth_method: 'username_only' // Indicate this is username-only auth
                })
            });
    
            return await response.json();
        } catch (error: any) {
            console.error('Fetch error:', error);
            return {
                success: false,
                error: `Connection error: ${error.message}`
            };
        }
    }

    /**
     * Authenticate user with credentials against backend
     */
    private async authenticateWithCredentials(username: string, password: string): Promise<any> {
        try {
            const response = await fetch(`${this.apiBaseUrl}/vscode-direct-auth`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
    
            return await response.json();
        } catch (error: any) {
            console.error('Fetch error:', error);
            return {
                success: false,
                error: `Connection error: ${error.message}`
            };
        }
    }

    /**
     * Get login URL from the server
     */
    private async getLoginUrl(): Promise<string | null> {
        try {
            const response = await fetch(`${this.apiBaseUrl}/vscode-auth`);
            const data = await response.json() as { login_url?: string; session_id?: string };
            if (data.login_url) return data.login_url;
            if (data.session_id) return `${this.apiBaseUrl}/vscode-auth?session_id=${data.session_id}`;
            return null;
        } catch (error) {
            console.error('Login URL fetch error:', error);
            return null;
        }
    }
    

    /**
     * Extract session ID from login URL
     */
    private extractSessionId(url: string): string | null {
        try {
            const urlObj = new URL(url);
            return urlObj.searchParams.get('session_id');
        } catch (error) {
            return null;
        }
    }

    /**
     * Poll for authentication completion
     */
    private async pollForAuthentication(
        sessionId: string, 
        progress: vscode.Progress<{ message?: string; increment?: number }>,
        cancellationToken: vscode.CancellationToken
    ): Promise<AuthToken | null> {
        const maxAttempts = 60; // 5 minutes (5 second intervals)
        let attempts = 0;

        while (attempts < maxAttempts && !cancellationToken.isCancellationRequested) {
            try {
                const status = await this.checkAuthStatus(sessionId);
                
                if (status.status === 'completed' && status.token && status.utln) {
                    // Authentication successful
                    const expiresAt = new Date();
                    expiresAt.setHours(expiresAt.getHours() + 24); // 24 hour expiry

                    const authToken: AuthToken = {
                        token: status.token,
                        utln: status.utln,
                        expiresAt
                    };

                    this.storeToken(authToken);
                    return authToken;
                }

                if (status.status === 'error') {
                    throw new Error('Authentication failed on server');
                }

                // Update progress
                progress.report({ 
                    message: `Waiting for authentication... (${Math.ceil((maxAttempts - attempts) * 5 / 60)} min remaining)` 
                });

                // Wait 5 seconds before next poll
                await new Promise(resolve => setTimeout(resolve, 5000));
                attempts++;

            } catch (error) {
                console.error('Error polling for authentication:', error);
                throw error;
            }
        }

        if (cancellationToken.isCancellationRequested) {
            throw new Error('Authentication cancelled by user');
        }

        throw new Error('Authentication timeout');
    }

    /**
     * Check authentication status on server
     */
    private async checkAuthStatus(sessionId: string): Promise<any> {
        try {
            const response = await fetch(`${this.apiBaseUrl}/vscode-auth-status?session_id=${encodeURIComponent(sessionId)}`);
            return await response.json();
        } catch (error) {
            console.error('Error checking auth status:', error);
            throw new Error('Failed to check auth status');
        }
    }

    /**
     * Show authentication status in status bar
     */
    public updateStatusBar(statusBarItem: vscode.StatusBarItem): void {
        if (this.isAuthenticated()) {
            statusBarItem.text = `CS 15`;
            statusBarItem.tooltip = `CS 15 Tutor - Click to see user options`;
            statusBarItem.command = 'cs15-tutor.showUserMenu';
        } else {
            statusBarItem.text = `$(sign-in) CS15: Sign In`;
            statusBarItem.tooltip = 'Click to sign in to CS 15 Tutor';
            statusBarItem.command = 'cs15-tutor.signIn';
        }
        statusBarItem.show();
    }

    /**
     * Show user menu with username and sign out option
     */
    public async showUserMenu(): Promise<void> {
        if (!this.isAuthenticated()) {
            return;
        }

        const utln = this.getUtln();
        const items = [
            {
                label: `$(person) Signed in as: ${utln}`,
                description: 'Your current authentication status'
            },
            {
                label: `$(sign-out) Sign Out`,
                description: 'Sign out of CS 15 Tutor'
            }
        ];

        const selection = await vscode.window.showQuickPick(items, {
            placeHolder: 'CS 15 Tutor User Options',
            canPickMany: false
        });

        if (selection && selection.label.includes('Sign Out')) {
            const result = await vscode.window.showInformationMessage(
                'Are you sure you want to sign out of CS 15 Tutor?',
                'Sign Out',
                'Cancel'
            );
            
            if (result === 'Sign Out') {
                await this.signOut();
            }
        }
    }

    /**
     * Sign out the current user
     */
    public async signOut(): Promise<void> {
        try {
            this.clearAuthentication();
            vscode.window.showInformationMessage('Successfully signed out of CS 15 Tutor');
        } catch (error) {
            console.error('Error during sign out:', error);
            vscode.window.showErrorMessage('Error signing out');
        }
    }
} 