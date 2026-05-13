import * as vscode from 'vscode';
import { ServerStatus } from '../api/types';

export class StatusBarManager {
    private statusBarItem: vscode.StatusBarItem;

    constructor() {
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this.statusBarItem.command = 'slm-docgen.showLogs';
        this.statusBarItem.show();
        this.update(ServerStatus.Stopped);
    }

    update(status: ServerStatus): void {
        switch (status) {
            case ServerStatus.Stopped:
                this.statusBarItem.text = '$(circle-slash) SLM DocGen: Stopped';
                this.statusBarItem.tooltip = 'Click to show logs';
                this.statusBarItem.backgroundColor = undefined;
                break;

            case ServerStatus.Starting:
                this.statusBarItem.text = '$(sync~spin) SLM DocGen: Starting...';
                this.statusBarItem.tooltip = 'Server is starting';
                this.statusBarItem.backgroundColor = undefined;
                break;

            case ServerStatus.LoadingModel:
                this.statusBarItem.text = '$(sync~spin) SLM DocGen: Loading Model...';
                this.statusBarItem.tooltip = 'Loading AI model, this may take a few minutes';
                this.statusBarItem.backgroundColor = undefined;
                break;

            case ServerStatus.Ready:
                this.statusBarItem.text = '$(check) SLM DocGen: Ready';
                this.statusBarItem.tooltip = 'Ready to generate documentation';
                this.statusBarItem.backgroundColor = undefined;
                break;

            case ServerStatus.Generating:
                this.statusBarItem.text = '$(sync~spin) SLM DocGen: Generating...';
                this.statusBarItem.tooltip = 'Generating documentation';
                this.statusBarItem.backgroundColor = undefined;
                break;

            case ServerStatus.Error:
                this.statusBarItem.text = '$(error) SLM DocGen: Error';
                this.statusBarItem.tooltip = 'Server error - click to view logs';
                this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
                break;
        }
    }

    dispose(): void {
        this.statusBarItem.dispose();
    }
}
