import * as vscode from 'vscode';
import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import { ApiClient } from '../api/ApiClient';
import { ServerStatus, ServerConfig, HealthResponse } from '../api/types';

export class ServerManager {
    private serverProcess: ChildProcess | null = null;
    private apiClient: ApiClient;
    private status: ServerStatus = ServerStatus.Stopped;
    private outputChannel: vscode.OutputChannel;
    private statusChangeEmitter = new vscode.EventEmitter<ServerStatus>();
    public readonly onStatusChange = this.statusChangeEmitter.event;
    
    private healthCheckInterval: NodeJS.Timeout | null = null;
    private config: ServerConfig;

    constructor(config: ServerConfig, outputChannel: vscode.OutputChannel) {
        this.config = config;
        this.outputChannel = outputChannel;
        this.apiClient = new ApiClient(config.port);
    }

    async start(): Promise<void> {
        if (this.serverProcess) {
            this.outputChannel.appendLine('[INFO] Server already running');
            return;
        }

        this.updateStatus(ServerStatus.Starting);

        // Try connecting to an already-running server first
        try {
            const health = await this.apiClient.health();
            if (health.status) {
                this.outputChannel.appendLine(`[INFO] Connected to existing server on port ${this.config.port}`);
                if (health.model_loaded) {
                    this.updateStatus(ServerStatus.Ready);
                } else {
                    this.updateStatus(ServerStatus.LoadingModel);
                    this.startHealthChecks();
                }
                return;
            }
        } catch {
            // No server running, proceed to start one
        }

        this.outputChannel.appendLine('[INFO] Starting slm_docgen server...');

        try {
            const slmDocgenPath = await this.findSlmDocgenPath();
            if (!slmDocgenPath) {
                throw new Error('Could not find slm_docgen directory. Please set slm-docgen.slmDocgenPath in settings to the absolute path of your slm_docgen folder.');
            }

            const cliPath = path.join(slmDocgenPath, 'cli.py');
            const adapterPath = this.config.adapterPath || await this.findAdapterPath();

            const args = [
                cliPath,
                'serve',
                '--port', this.config.port.toString(),
                '--adapter-dir', adapterPath
            ];

            if (!this.config.enable4bit) {
                args.push('--no-4bit');
            }

            this.outputChannel.appendLine(`[INFO] Command: ${this.config.pythonPath} ${args.join(' ')}`);

            this.serverProcess = spawn(this.config.pythonPath, args, {
                cwd: slmDocgenPath,
                env: { ...process.env }
            });

            this.serverProcess.stdout?.on('data', (data) => {
                const output = data.toString();
                this.outputChannel.append(output);
                
                if (output.includes('Loading model')) {
                    this.updateStatus(ServerStatus.LoadingModel);
                } else if (output.includes('Uvicorn running') || output.includes('Application startup complete')) {
                    this.startHealthChecks();
                }
            });

            this.serverProcess.stderr?.on('data', (data) => {
                const output = data.toString();
                this.outputChannel.append(`[ERROR] ${output}`);
                
                // Uvicorn outputs to stderr on some systems
                if (output.includes('Loading model')) {
                    this.updateStatus(ServerStatus.LoadingModel);
                } else if (output.includes('Uvicorn running') || output.includes('Application startup complete')) {
                    this.startHealthChecks();
                }
            });

            this.serverProcess.on('exit', (code) => {
                this.outputChannel.appendLine(`[INFO] Server process exited with code ${code}`);
                this.cleanup();
                this.updateStatus(ServerStatus.Stopped);
            });

            this.serverProcess.on('error', (error) => {
                this.outputChannel.appendLine(`[ERROR] Failed to start server: ${error.message}`);
                this.updateStatus(ServerStatus.Error);
                throw error;
            });

        } catch (error) {
            this.updateStatus(ServerStatus.Error);
            throw error;
        }
    }

    async stop(): Promise<void> {
        if (!this.serverProcess) {
            return;
        }

        this.outputChannel.appendLine('[INFO] Stopping server...');
        
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = null;
        }

        this.serverProcess.kill('SIGTERM');
        
        // Give it 5 seconds to gracefully shut down
        await new Promise<void>((resolve) => {
            const timeout = setTimeout(() => {
                if (this.serverProcess) {
                    this.outputChannel.appendLine('[WARN] Force killing server...');
                    this.serverProcess.kill('SIGKILL');
                }
                resolve();
            }, 5000);

            this.serverProcess?.on('exit', () => {
                clearTimeout(timeout);
                resolve();
            });
        });

        this.cleanup();
        this.updateStatus(ServerStatus.Stopped);
    }

    private startHealthChecks(): void {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
        }

        this.healthCheckInterval = setInterval(async () => {
            try {
                const health: HealthResponse = await this.apiClient.health();
                
                if (health.model_loaded && this.status !== ServerStatus.Ready) {
                    this.outputChannel.appendLine('[INFO] Model loaded, server ready');
                    this.updateStatus(ServerStatus.Ready);
                    // Stop checking once ready
                    if (this.healthCheckInterval) {
                        clearInterval(this.healthCheckInterval);
                        this.healthCheckInterval = null;
                    }
                } else if (!health.model_loaded && this.status === ServerStatus.Ready) {
                    this.updateStatus(ServerStatus.LoadingModel);
                }
            } catch (error) {
                // Server not responding yet, keep waiting
                if (this.status === ServerStatus.Ready) {
                    this.outputChannel.appendLine('[WARN] Server health check failed');
                    this.updateStatus(ServerStatus.Starting);
                }
            }
        }, 2000); // Check every 2 seconds
    }

    private cleanup(): void {
        this.serverProcess = null;
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = null;
        }
    }

    private updateStatus(newStatus: ServerStatus): void {
        if (this.status !== newStatus) {
            this.status = newStatus;
            this.statusChangeEmitter.fire(newStatus);
        }
    }

    private async findSlmDocgenPath(): Promise<string | null> {
        // 1. Check explicit setting first
        const configuredPath = vscode.workspace.getConfiguration('slm-docgen').get<string>('slmDocgenPath', '');
        if (configuredPath) {
            try {
                await vscode.workspace.fs.stat(vscode.Uri.file(path.join(configuredPath, 'cli.py')));
                return configuredPath;
            } catch {
                this.outputChannel.appendLine(`[WARN] Configured slmDocgenPath not found: ${configuredPath}`);
            }
        }

        // 2. Search workspace folders and parents
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (workspaceFolders) {
            for (const folder of workspaceFolders) {
                const candidates = [
                    path.join(folder.uri.fsPath, 'slm_docgen'),
                    path.join(folder.uri.fsPath, '..', 'slm_docgen'),
                ];
                for (const candidate of candidates) {
                    try {
                        await vscode.workspace.fs.stat(vscode.Uri.file(path.join(candidate, 'cli.py')));
                        return candidate;
                    } catch {
                        continue;
                    }
                }
            }
        }

        return null;
    }

    private async findAdapterPath(): Promise<string> {
        // 1. Check explicit setting
        const configuredAdapter = this.config.adapterPath;
        if (configuredAdapter) {
            try {
                await vscode.workspace.fs.stat(vscode.Uri.file(configuredAdapter));
                return configuredAdapter;
            } catch {
                this.outputChannel.appendLine(`[WARN] Configured adapterPath not found: ${configuredAdapter}`);
            }
        }

        // 2. Search workspace folders and parents
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (workspaceFolders) {
            for (const folder of workspaceFolders) {
                const candidates = [
                    path.join(folder.uri.fsPath, 'slm_docgen_final', 'slm_docgen_adapters'),
                    path.join(folder.uri.fsPath, '..', 'slm_docgen_final', 'slm_docgen_adapters'),
                ];
                for (const candidate of candidates) {
                    try {
                        await vscode.workspace.fs.stat(vscode.Uri.file(candidate));
                        return candidate;
                    } catch {
                        continue;
                    }
                }
            }
        }

        throw new Error('Could not find model adapters. Please configure slm-docgen.adapterPath in settings.');
    }

    getStatus(): ServerStatus {
        return this.status;
    }

    getApiClient(): ApiClient {
        return this.apiClient;
    }

    isReady(): boolean {
        return this.status === ServerStatus.Ready;
    }

    updateConfig(config: Partial<ServerConfig>): void {
        this.config = { ...this.config, ...config };
        if (config.port) {
            this.apiClient = new ApiClient(config.port);
        }
    }

    dispose(): void {
        this.stop();
        this.statusChangeEmitter.dispose();
    }
}
