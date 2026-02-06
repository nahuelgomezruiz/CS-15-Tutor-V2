import * as vscode from 'vscode';
import { ChatViewProvider } from './chatViewProvider';
import { AuthManager } from './authManager';

let authManager: AuthManager;
let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext) {
    console.log('CS15 Tutor extension is now active!');

    // API base URL - change this if your backend is hosted elsewhere
    const apiBaseUrl = 'https://cs-15-tutor.onrender.com';

    // Initialize authentication manager
    authManager = new AuthManager(context, apiBaseUrl);

    // Create status bar item
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    context.subscriptions.push(statusBarItem);

    // Update status bar
    authManager.updateStatusBar(statusBarItem);

    // Create and register the webview provider
    const provider = new ChatViewProvider(context.extensionUri, authManager, apiBaseUrl);

    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            'cs15-tutor.chatView',
            provider,
            {
                webviewOptions: {
                    retainContextWhenHidden: true
                }
            }
        )
    );

    // Register the command to open the chat
    context.subscriptions.push(
        vscode.commands.registerCommand('cs15-tutor.openChat', () => {
            vscode.commands.executeCommand('workbench.view.explorer');
        })
    );

    // Register sign in command
    context.subscriptions.push(
        vscode.commands.registerCommand('cs15-tutor.signIn', async () => {
            const success = await authManager.authenticate();
            if (success) {
                authManager.updateStatusBar(statusBarItem);
                // Refresh the chat view to show authenticated state
                provider.refresh();
            }
        })
    );

    // Register show user menu command
    context.subscriptions.push(
        vscode.commands.registerCommand('cs15-tutor.showUserMenu', async () => {
            await authManager.showUserMenu();
            authManager.updateStatusBar(statusBarItem);
            // Refresh the chat view in case authentication status changed
            provider.refresh();
        })
    );

    // Register sign out command
    context.subscriptions.push(
        vscode.commands.registerCommand('cs15-tutor.signOut', async () => {
            const result = await vscode.window.showInformationMessage(
                'Are you sure you want to sign out of CS 15 Tutor?',
                'Sign Out',
                'Cancel'
            );
            
            if (result === 'Sign Out') {
                await authManager.signOut();
                authManager.updateStatusBar(statusBarItem);
                // Refresh the chat view to show sign-in prompt
                provider.refresh();
            }
        })
    );

    // Register refresh command
    context.subscriptions.push(
        vscode.commands.registerCommand('cs15-tutor.refresh', () => {
            provider.refresh();
        })
    );

    // Show welcome message if first time
    if (!context.globalState.get('cs15-tutor.welcomed')) {
        vscode.window.showInformationMessage(
            'Welcome to CS 15 Tutor! Please sign in with your Tufts credentials to get started.',
            'Sign In'
        ).then(selection => {
            if (selection === 'Sign In') {
                vscode.commands.executeCommand('cs15-tutor.signIn');
            }
        });
        context.globalState.update('cs15-tutor.welcomed', true);
    }
}

export function deactivate() {
    if (statusBarItem) {
        statusBarItem.dispose();
    }
} 