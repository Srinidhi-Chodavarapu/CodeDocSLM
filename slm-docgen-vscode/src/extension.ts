import * as vscode from 'vscode';
import { ServerManager } from './server/ServerManager';
import { StatusBarManager } from './ui/StatusBar';
import { ServerConfig, ServerStatus } from './api/types';

let serverManager: ServerManager | null = null;
let statusBarManager: StatusBarManager | null = null;
let outputChannel: vscode.OutputChannel | null = null;

export async function activate(context: vscode.ExtensionContext) {
    console.log('SLM DocGen extension is now active');

    // Create output channel
    outputChannel = vscode.window.createOutputChannel('SLM DocGen');
    context.subscriptions.push(outputChannel);

    // Create status bar
    statusBarManager = new StatusBarManager();
    context.subscriptions.push(statusBarManager);

    // Get configuration
    const config = getServerConfig();

    // Create server manager
    serverManager = new ServerManager(config, outputChannel);
    context.subscriptions.push(serverManager);

    // Listen to status changes
    serverManager.onStatusChange((status) => {
        statusBarManager?.update(status);
        
        if (status === ServerStatus.Ready) {
            vscode.window.showInformationMessage('SLM DocGen: Server ready to generate documentation');
        } else if (status === ServerStatus.Error) {
            vscode.window.showErrorMessage('SLM DocGen: Server error. Check output for details.');
        }
    });

    // Auto-start server if configured
    if (config.autoStartServer) {
        try {
            await serverManager.start();
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to start server: ${error}`);
            outputChannel.appendLine(`[ERROR] ${error}`);
        }
    }

    // Register commands
    registerCommands(context);

    // Watch for configuration changes
    context.subscriptions.push(
        vscode.workspace.onDidChangeConfiguration((e) => {
            if (e.affectsConfiguration('slm-docgen')) {
                handleConfigChange();
            }
        })
    );
}

function registerCommands(context: vscode.ExtensionContext) {
    // Start server command
    context.subscriptions.push(
        vscode.commands.registerCommand('slm-docgen.startServer', async () => {
            if (!serverManager) {
                return;
            }

            try {
                await serverManager.start();
                vscode.window.showInformationMessage('Starting SLM DocGen server...');
            } catch (error) {
                vscode.window.showErrorMessage(`Failed to start server: ${error}`);
            }
        })
    );

    // Stop server command
    context.subscriptions.push(
        vscode.commands.registerCommand('slm-docgen.stopServer', async () => {
            if (!serverManager) {
                return;
            }

            try {
                await serverManager.stop();
                vscode.window.showInformationMessage('SLM DocGen server stopped');
            } catch (error) {
                vscode.window.showErrorMessage(`Failed to stop server: ${error}`);
            }
        })
    );

    // Show logs command
    context.subscriptions.push(
        vscode.commands.registerCommand('slm-docgen.showLogs', () => {
            outputChannel?.show();
        })
    );

    // Document function command
    context.subscriptions.push(
        vscode.commands.registerCommand('slm-docgen.documentFunction', async () => {
            if (!serverManager?.isReady()) {
                vscode.window.showWarningMessage('Server not ready. Please wait for model to load.');
                return;
            }

            vscode.window.showInformationMessage('Document Function command - implementation coming soon');
            // TODO: Implement in Phase 2
        })
    );

    // Document file command
    context.subscriptions.push(
        vscode.commands.registerCommand('slm-docgen.documentFile', async () => {
            if (!serverManager?.isReady()) {
                vscode.window.showWarningMessage('Server not ready. Please wait for model to load.');
                return;
            }

            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('No active file to document');
                return;
            }

            const document = editor.document;
            const fileName = document.fileName;
            const fileContent = document.getText();

            // Check if file is supported
            const supportedLangs = ['python', 'java', 'javascript', 'typescript'];
            if (!supportedLangs.includes(document.languageId)) {
                vscode.window.showWarningMessage(`Language ${document.languageId} not supported. Supported: Python, Java, JavaScript, TypeScript`);
                return;
            }

            try {
                statusBarManager?.update(ServerStatus.Generating);
                outputChannel?.appendLine(`[INFO] Generating documentation for ${fileName}`);

                const apiClient = serverManager.getApiClient();
                const buffer = Buffer.from(fileContent, 'utf-8');
                const response = await apiClient.generateFile(buffer, fileName);

                // Create .bak backup before modifying
                const path = require('path');
                const dir = path.dirname(fileName);
                const bakDir = path.join(dir, '.slm_docgen_backup');
                const bakUri = vscode.Uri.file(path.join(bakDir, path.basename(fileName) + '.bak'));
                await vscode.workspace.fs.createDirectory(vscode.Uri.file(bakDir));
                await vscode.workspace.fs.writeFile(bakUri, Buffer.from(fileContent, 'utf-8'));
                outputChannel?.appendLine(`[INFO] Backup saved to .slm_docgen_backup/${path.basename(fileName)}.bak`);

                // Replace entire document with documented code
                const edit = new vscode.WorkspaceEdit();
                const fullRange = new vscode.Range(
                    document.positionAt(0),
                    document.positionAt(fileContent.length)
                );
                edit.replace(document.uri, fullRange, response.modified_source);
                await vscode.workspace.applyEdit(edit);
                
                vscode.window.showInformationMessage(`✓ Documentation added to ${response.units_documented} units`);
                outputChannel?.appendLine(`[INFO] Success: ${response.units_documented} units documented in ${response.latency_ms}ms`);

                statusBarManager?.update(ServerStatus.Ready);
            } catch (error) {
                statusBarManager?.update(ServerStatus.Ready);
                vscode.window.showErrorMessage(`Error: ${error}`);
                outputChannel?.appendLine(`[ERROR] ${error}`);
            }
        })
    );

    // Document workspace command
    context.subscriptions.push(
        vscode.commands.registerCommand('slm-docgen.documentWorkspace', async () => {
            if (!serverManager?.isReady()) {
                vscode.window.showWarningMessage('Server not ready. Please wait for model to load.');
                return;
            }

            const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
            if (!workspaceFolder) {
                vscode.window.showWarningMessage('No workspace folder opened');
                return;
            }

            // Ask user for options
            const choice = await vscode.window.showQuickPick(
                [
                    { label: 'Document Workspace', description: 'Generate docs for entire workspace + README', value: 'workspace' },
                    { label: 'Document Directory', description: 'Generate docs for a specific directory + README', value: 'directory' }
                ],
                { placeHolder: 'Choose documentation scope' }
            );

            if (!choice) {
                return;
            }

            let targetPath: string;
            if (choice.value === 'directory') {
                const uri = await vscode.window.showOpenDialog({
                    canSelectFiles: false,
                    canSelectFolders: true,
                    canSelectMany: false,
                    openLabel: 'Select Directory',
                    defaultUri: workspaceFolder.uri
                });

                if (!uri || uri.length === 0) {
                    return;
                }
                targetPath = uri[0].fsPath;
            } else {
                targetPath = workspaceFolder.uri.fsPath;
            }

            try {
                statusBarManager?.update(ServerStatus.Generating);
                outputChannel?.appendLine(`[INFO] Generating documentation for ${targetPath}`);

                // Show progress
                await vscode.window.withProgress({
                    location: vscode.ProgressLocation.Notification,
                    title: 'SLM DocGen',
                    cancellable: false
                }, async (progress) => {
                    progress.report({ message: 'Collecting files...' });

                    // Collect supported source files
                    const files = await collectSourceFiles(targetPath);
                    outputChannel?.appendLine(`[INFO] Found ${files.length} source files`);

                    if (files.length === 0) {
                        vscode.window.showWarningMessage('No supported source files found in the selected path');
                        statusBarManager?.update(ServerStatus.Ready);
                        return;
                    }

                    progress.report({ message: `Creating project archive (${files.length} files)...` });

                    // Create zip archive
                    const archiver = require('archiver');
                    
                    const archive = archiver('zip', { zlib: { level: 9 } });
                    const chunks: Buffer[] = [];

                    archive.on('data', (chunk: Buffer) => chunks.push(chunk));
                    
                    const archivePromise = new Promise<Buffer>((resolve, reject) => {
                        archive.on('end', () => resolve(Buffer.concat(chunks)));
                        archive.on('error', reject);
                    });

                    // Add files to archive with relative paths
                    const path = require('path');
                    for (const file of files) {
                        const relativePath = path.relative(targetPath, file.path);
                        archive.append(file.content, { name: relativePath });
                    }

                    archive.finalize();
                    const zipBuffer = await archivePromise;

                    progress.report({ message: 'Generating documentation with AI model...' });

                    // Call API
                    const apiClient = serverManager!.getApiClient();
                    const response = await apiClient.generateProject(zipBuffer, false) as any;

                    progress.report({ message: 'Writing documented files...' });

                    // Write back modified files (with .bak backups)
                    const bakDir = path.join(targetPath, '.slm_docgen_backup');
                    await vscode.workspace.fs.createDirectory(vscode.Uri.file(bakDir));
                    let filesWritten = 0;
                    for (const [relativePath, content] of Object.entries(response.modified_files)) {
                        const fullPath = path.join(targetPath, relativePath);
                        const uri = vscode.Uri.file(fullPath);

                        // Create .bak backup in backup folder
                        try {
                            const original = await vscode.workspace.fs.readFile(uri);
                            const bakPath = path.join(bakDir, relativePath + '.bak');
                            await vscode.workspace.fs.createDirectory(vscode.Uri.file(path.dirname(bakPath)));
                            await vscode.workspace.fs.writeFile(vscode.Uri.file(bakPath), original);
                        } catch {
                            // File may not exist yet, skip backup
                        }

                        await vscode.workspace.fs.writeFile(uri, Buffer.from(content as string, 'utf-8'));
                        filesWritten++;
                    }

                    // Write README
                    if (response.readme) {
                        const readmePath = path.join(targetPath, 'README_generated.md');
                        const readmeUri = vscode.Uri.file(readmePath);
                        await vscode.workspace.fs.writeFile(readmeUri, Buffer.from(response.readme, 'utf-8'));
                        
                        outputChannel?.appendLine(`[INFO] README saved to README_generated.md`);

                        // Open README in editor
                        const doc = await vscode.workspace.openTextDocument(readmeUri);
                        await vscode.window.showTextDocument(doc, { preview: false });
                    }

                    const stats = response.stats;
                    vscode.window.showInformationMessage(
                        `✓ Documentation complete! ${stats.units_documented} units in ${stats.files_processed} files (${stats.total_latency_ms}ms)`
                    );
                    outputChannel?.appendLine(`[INFO] Success: ${filesWritten} files documented, README generated`);
                    outputChannel?.appendLine(`[INFO] Stats: ${JSON.stringify(stats, null, 2)}`);
                });

                statusBarManager?.update(ServerStatus.Ready);
            } catch (error) {
                statusBarManager?.update(ServerStatus.Ready);
                vscode.window.showErrorMessage(`Error documenting workspace: ${error}`);
                outputChannel?.appendLine(`[ERROR] ${error}`);
            }
        })
    );

    // Document directory command (right-click on folder in explorer)
    context.subscriptions.push(
        vscode.commands.registerCommand('slm-docgen.documentDirectory', async (uri: vscode.Uri) => {
            if (!serverManager?.isReady()) {
                vscode.window.showWarningMessage('Server not ready. Please wait for model to load.');
                return;
            }

            if (!uri) {
                vscode.window.showWarningMessage('No directory selected');
                return;
            }

            const targetPath = uri.fsPath;

            try {
                statusBarManager?.update(ServerStatus.Generating);
                outputChannel?.appendLine(`[INFO] Generating documentation for directory: ${targetPath}`);

                await vscode.window.withProgress({
                    location: vscode.ProgressLocation.Notification,
                    title: 'SLM DocGen',
                    cancellable: false
                }, async (progress) => {
                    progress.report({ message: 'Collecting files...' });

                    const files = await collectSourceFiles(targetPath);
                    outputChannel?.appendLine(`[INFO] Found ${files.length} source files`);

                    if (files.length === 0) {
                        vscode.window.showWarningMessage('No supported source files found in this directory');
                        statusBarManager?.update(ServerStatus.Ready);
                        return;
                    }

                    progress.report({ message: `Creating project archive (${files.length} files)...` });

                    const archiver = require('archiver');
                    const archive = archiver('zip', { zlib: { level: 9 } });
                    const chunks: Buffer[] = [];

                    archive.on('data', (chunk: Buffer) => chunks.push(chunk));

                    const archivePromise = new Promise<Buffer>((resolve, reject) => {
                        archive.on('end', () => resolve(Buffer.concat(chunks)));
                        archive.on('error', reject);
                    });

                    const path = require('path');
                    for (const file of files) {
                        const relativePath = path.relative(targetPath, file.path);
                        archive.append(file.content, { name: relativePath });
                    }

                    archive.finalize();
                    const zipBuffer = await archivePromise;

                    progress.report({ message: 'Generating documentation with AI model...' });

                    const apiClient = serverManager!.getApiClient();
                    const response = await apiClient.generateProject(zipBuffer, false) as any;

                    progress.report({ message: 'Writing documented files...' });

                    let filesWritten = 0;
                    const bakDir = path.join(targetPath, '.slm_docgen_backup');
                    await vscode.workspace.fs.createDirectory(vscode.Uri.file(bakDir));
                    for (const [relativePath, content] of Object.entries(response.modified_files)) {
                        const fullPath = path.join(targetPath, relativePath);
                        const fileUri = vscode.Uri.file(fullPath);

                        // Create .bak backup in backup folder
                        try {
                            const original = await vscode.workspace.fs.readFile(fileUri);
                            const bakPath = path.join(bakDir, relativePath + '.bak');
                            await vscode.workspace.fs.createDirectory(vscode.Uri.file(path.dirname(bakPath)));
                            await vscode.workspace.fs.writeFile(vscode.Uri.file(bakPath), original);
                        } catch {
                            // File may not exist yet, skip backup
                        }

                        await vscode.workspace.fs.writeFile(fileUri, Buffer.from(content as string, 'utf-8'));
                        filesWritten++;
                    }

                    if (response.readme) {
                        const readmePath = path.join(targetPath, 'README_generated.md');
                        const readmeUri = vscode.Uri.file(readmePath);
                        await vscode.workspace.fs.writeFile(readmeUri, Buffer.from(response.readme, 'utf-8'));
                        outputChannel?.appendLine(`[INFO] README saved to README_generated.md`);

                        const doc = await vscode.workspace.openTextDocument(readmeUri);
                        await vscode.window.showTextDocument(doc, { preview: false });
                    }

                    const stats = response.stats;
                    vscode.window.showInformationMessage(
                        `✓ Documentation complete! ${stats.units_documented} units in ${stats.files_processed} files`
                    );
                    outputChannel?.appendLine(`[INFO] Success: ${filesWritten} files documented, README generated`);
                });

                statusBarManager?.update(ServerStatus.Ready);
            } catch (error) {
                statusBarManager?.update(ServerStatus.Ready);
                vscode.window.showErrorMessage(`Error documenting directory: ${error}`);
                outputChannel?.appendLine(`[ERROR] ${error}`);
            }
        })
    );
}

function getServerConfig(): ServerConfig & { autoStartServer: boolean } {
    const config = vscode.workspace.getConfiguration('slm-docgen');

    return {
        port: config.get<number>('serverPort', 8000),
        pythonPath: config.get<string>('pythonPath', 'python3'),
        adapterPath: config.get<string>('adapterPath', ''),
        enable4bit: config.get<boolean>('enable4bit', true),
        maxFiles: config.get<number>('maxFiles', 50),
        autoStartServer: config.get<boolean>('autoStartServer', true)
    };
}

async function collectSourceFiles(rootPath: string): Promise<Array<{ path: string; content: string }>> {
    const fs = require('fs').promises;
    const path = require('path');
    
    const supportedExtensions = ['.py', '.java', '.js', '.ts', '.jsx', '.tsx'];
    const ignoreDirs = ['node_modules', 'venv', '.venv', 'env', '__pycache__', 'dist', 'build', '.git', 'target'];
    
    const files: Array<{ path: string; content: string }> = [];
    
    async function scanDirectory(dirPath: string) {
        try {
            const entries = await fs.readdir(dirPath, { withFileTypes: true });
            
            for (const entry of entries) {
                const fullPath = path.join(dirPath, entry.name);
                
                if (entry.isDirectory()) {
                    // Skip ignored directories
                    if (!ignoreDirs.includes(entry.name) && !entry.name.startsWith('.')) {
                        await scanDirectory(fullPath);
                    }
                } else if (entry.isFile()) {
                    // Check if file has supported extension
                    const ext = path.extname(entry.name).toLowerCase();
                    if (supportedExtensions.includes(ext)) {
                        try {
                            const content = await fs.readFile(fullPath, 'utf-8');
                            files.push({ path: fullPath, content });
                        } catch (error) {
                            console.error(`Error reading file ${fullPath}:`, error);
                        }
                    }
                }
            }
        } catch (error) {
            console.error(`Error scanning directory ${dirPath}:`, error);
        }
    }
    
    await scanDirectory(rootPath);
    return files;
}

async function handleConfigChange() {
    const response = await vscode.window.showWarningMessage(
        'Server configuration changed. Restart server for changes to take effect.',
        'Restart Now',
        'Later'
    );

    if (response === 'Restart Now' && serverManager) {
        await serverManager.stop();
        const config = getServerConfig();
        serverManager.updateConfig(config);
        await serverManager.start();
    }
}

export function deactivate() {
    if (serverManager) {
        serverManager.stop();
    }
}
