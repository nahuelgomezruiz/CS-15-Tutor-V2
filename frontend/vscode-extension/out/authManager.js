"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.AuthManager = void 0;
const vscode = __importStar(require("vscode"));
const node_fetch_1 = __importDefault(require("node-fetch"));
const ssh2_1 = require("ssh2");
class AuthManager {
    constructor(context, apiBaseUrl = 'https://cs-15-tutor.onrender.com') {
        this.context = context;
        this.apiBaseUrl = apiBaseUrl;
    }
    /**
     * Check if user is currently authenticated
     */
    isAuthenticated() {
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
    getAuthToken() {
        const token = this.getStoredToken();
        return token ? token.token : null;
    }
    /**
     * Get the current user's UTLN
     */
    getUtln() {
        const token = this.getStoredToken();
        return token ? token.utln : null;
    }
    /**
     * Helper to check SSH credentials
     */
    async checkSshCredentials(username, password, host) {
        return new Promise((resolve) => {
            const conn = new ssh2_1.Client();
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
    async authenticate() {
        try {
            // Prompt for username
            const username = await vscode.window.showInputBox({
                prompt: 'Enter your EECS username',
                placeHolder: 'e.g., vhenao01',
                ignoreFocusOut: true,
                validateInput: (value) => {
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
                    const authToken = {
                        token: authResult.token,
                        utln: authResult.username,
                        expiresAt
                    };
                    this.storeToken(authToken);
                    vscode.window.showInformationMessage(`Authentication successful! Welcome, ${authResult.username}`);
                    return true;
                }
                else {
                    vscode.window.showErrorMessage(authResult.error || 'Authentication failed');
                    return false;
                }
            }
            else {
                vscode.window.showErrorMessage('Authentication failed. Please check your credentials.');
                return false;
            }
        }
        catch (error) {
            console.error('Authentication error:', error);
            vscode.window.showErrorMessage(`Authentication failed: ${error}`);
            return false;
        }
    }
    /**
     * Clear stored authentication
     */
    clearAuthentication() {
        this.context.globalState.update(AuthManager.TOKEN_KEY, undefined);
        this.context.globalState.update(AuthManager.UTLN_KEY, undefined);
        this.context.globalState.update(AuthManager.EXPIRES_KEY, undefined);
    }
    /**
     * Get stored authentication token
     */
    getStoredToken() {
        const token = this.context.globalState.get(AuthManager.TOKEN_KEY);
        const utln = this.context.globalState.get(AuthManager.UTLN_KEY);
        const expiresAt = this.context.globalState.get(AuthManager.EXPIRES_KEY);
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
    storeToken(authToken) {
        this.context.globalState.update(AuthManager.TOKEN_KEY, authToken.token);
        this.context.globalState.update(AuthManager.UTLN_KEY, authToken.utln);
        this.context.globalState.update(AuthManager.EXPIRES_KEY, authToken.expiresAt.toISOString());
    }
    /**
     * Authenticate user with username only against backend
     */
    async authenticateWithUsername(username) {
        try {
            // Use the same endpoint but with development mode headers to bypass LDAP
            const response = await (0, node_fetch_1.default)(`${this.apiBaseUrl}/vscode-direct-auth`, {
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
        }
        catch (error) {
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
    async authenticateWithCredentials(username, password) {
        try {
            const response = await (0, node_fetch_1.default)(`${this.apiBaseUrl}/vscode-direct-auth`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            return await response.json();
        }
        catch (error) {
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
    async getLoginUrl() {
        try {
            const response = await (0, node_fetch_1.default)(`${this.apiBaseUrl}/vscode-auth`);
            const data = await response.json();
            if (data.login_url)
                return data.login_url;
            if (data.session_id)
                return `${this.apiBaseUrl}/vscode-auth?session_id=${data.session_id}`;
            return null;
        }
        catch (error) {
            console.error('Login URL fetch error:', error);
            return null;
        }
    }
    /**
     * Extract session ID from login URL
     */
    extractSessionId(url) {
        try {
            const urlObj = new URL(url);
            return urlObj.searchParams.get('session_id');
        }
        catch (error) {
            return null;
        }
    }
    /**
     * Poll for authentication completion
     */
    async pollForAuthentication(sessionId, progress, cancellationToken) {
        const maxAttempts = 60; // 5 minutes (5 second intervals)
        let attempts = 0;
        while (attempts < maxAttempts && !cancellationToken.isCancellationRequested) {
            try {
                const status = await this.checkAuthStatus(sessionId);
                if (status.status === 'completed' && status.token && status.utln) {
                    // Authentication successful
                    const expiresAt = new Date();
                    expiresAt.setHours(expiresAt.getHours() + 24); // 24 hour expiry
                    const authToken = {
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
            }
            catch (error) {
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
    async checkAuthStatus(sessionId) {
        try {
            const response = await (0, node_fetch_1.default)(`${this.apiBaseUrl}/vscode-auth-status?session_id=${encodeURIComponent(sessionId)}`);
            return await response.json();
        }
        catch (error) {
            console.error('Error checking auth status:', error);
            throw new Error('Failed to check auth status');
        }
    }
    /**
     * Show authentication status in status bar
     */
    updateStatusBar(statusBarItem) {
        if (this.isAuthenticated()) {
            statusBarItem.text = `CS 15`;
            statusBarItem.tooltip = `CS 15 Tutor - Click to see user options`;
            statusBarItem.command = 'cs15-tutor.showUserMenu';
        }
        else {
            statusBarItem.text = `$(sign-in) CS15: Sign In`;
            statusBarItem.tooltip = 'Click to sign in to CS 15 Tutor';
            statusBarItem.command = 'cs15-tutor.signIn';
        }
        statusBarItem.show();
    }
    /**
     * Show user menu with username and sign out option
     */
    async showUserMenu() {
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
            const result = await vscode.window.showInformationMessage('Are you sure you want to sign out of CS 15 Tutor?', 'Sign Out', 'Cancel');
            if (result === 'Sign Out') {
                await this.signOut();
            }
        }
    }
    /**
     * Sign out the current user
     */
    async signOut() {
        try {
            this.clearAuthentication();
            vscode.window.showInformationMessage('Successfully signed out of CS 15 Tutor');
        }
        catch (error) {
            console.error('Error during sign out:', error);
            vscode.window.showErrorMessage('Error signing out');
        }
    }
}
exports.AuthManager = AuthManager;
AuthManager.TOKEN_KEY = 'cs15-tutor.authToken';
AuthManager.UTLN_KEY = 'cs15-tutor.utln';
AuthManager.EXPIRES_KEY = 'cs15-tutor.tokenExpires';
//# sourceMappingURL=authManager.js.map