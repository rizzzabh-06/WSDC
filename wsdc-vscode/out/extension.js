import * as vscode from 'vscode';
import { exec } from 'child_process';
import * as path from 'path';
import { GoogleGenAI } from '@google/genai';
// Store diagnostics globally per-extension activation
const diagnosticCollection = vscode.languages.createDiagnosticCollection('wsdc');
export function activate(context) {
    console.log('WSDC Security Extension activated!');
    // Command to manually trigger analysis
    const analyzeCommand = vscode.commands.registerCommand('wsdc.analyze', () => {
        const editor = vscode.window.activeTextEditor;
        if (editor && editor.document.languageId === 'solidity') {
            runSlither(editor.document);
        }
        else {
            vscode.window.showInformationMessage('Open a Solidity (.sol) file to run WSDC Analysis.');
        }
    });
    // Command to explain a specific finding
    const explainCommand = vscode.commands.registerCommand('wsdc.explainFinding', async (diagnostic, document) => {
        await explainFindingWithAI(diagnostic, document);
    });
    // Register Quick Fix provider
    const codeActionProvider = vscode.languages.registerCodeActionsProvider('solidity', new WsdcCodeActionProvider(), {
        providedCodeActionKinds: WsdcCodeActionProvider.providedCodeActionKinds
    });
    // Run on save
    const saveListener = vscode.workspace.onDidSaveTextDocument((document) => {
        if (document.languageId === 'solidity') {
            runSlither(document);
        }
    });
    context.subscriptions.push(analyzeCommand, explainCommand, codeActionProvider, saveListener, diagnosticCollection);
}
function runSlither(document) {
    const filePath = document.uri.fsPath;
    const workspaceFolder = vscode.workspace.getWorkspaceFolder(document.uri)?.uri.fsPath || path.dirname(filePath);
    // Get custom Slither path from settings
    const config = vscode.workspace.getConfiguration('wsdc');
    const slitherPath = config.get('slitherPath') || 'slither';
    vscode.window.withProgress({
        location: vscode.ProgressLocation.Window,
        title: "WSDC: Analyzing Contract...",
        cancellable: false
    }, async () => {
        return new Promise((resolve, reject) => {
            // Run slither on the workspace, outputting JSON
            // We analyze the whole directory because Slither often needs the full repo context
            const cmd = `${slitherPath} ${workspaceFolder} --json -`;
            exec(cmd, { maxBuffer: 1024 * 1024 * 5 }, (error, stdout, stderr) => {
                // Slither returns non-zero if it finds issues, which is expected.
                // Output is in stdout.
                if (!stdout) {
                    if (stderr && stderr.includes('command not found')) {
                        vscode.window.showErrorMessage('Slither not found. Please install it (pip3 install slither-analyzer) or set the path in WSDC settings.');
                    }
                    console.error("Slither stderr:", stderr);
                    resolve();
                    return;
                }
                try {
                    const parsed = JSON.parse(stdout);
                    if (parsed.success && parsed.results && parsed.results.detectors) {
                        mapSlitherToDiagnostics(document, parsed.results.detectors);
                    }
                }
                catch (e) {
                    console.error("Failed to parse Slither output:", e);
                    // It might output plain text if there's a compilation error
                    vscode.window.showErrorMessage('WSDC: Failed to parse Slither check. Ensure the contract compiles.');
                }
                resolve();
            });
        });
    });
}
function mapSlitherToDiagnostics(document, detectors) {
    // We want to group diagnostics by file URI so we can update the whole workspace
    const diagnosticsMap = new Map();
    for (const d of detectors) {
        // Find the first element that maps to a source line (usually the vulnerability root)
        const element = d.elements && d.elements.length > 0 ? d.elements[0] : null;
        if (!element || !element.source_mapping)
            continue;
        const mapping = element.source_mapping;
        const findingFilePath = mapping.filename_absolute || mapping.filename_relative;
        if (!findingFilePath)
            continue;
        // Slither uses 1-indexed lines; VS Code uses 0-indexed lists
        // If there's no matching exact line, just default to line 0
        const startLine = (mapping.lines && mapping.lines.length > 0) ? mapping.lines[0] - 1 : 0;
        let endLine = startLine;
        if (mapping.lines && mapping.lines.length > 1) {
            endLine = mapping.lines[mapping.lines.length - 1] - 1;
        }
        const range = new vscode.Range(startLine, 0, endLine, 1000);
        const severity = getVscodeSeverity(d.impact);
        const diagnostic = new vscode.Diagnostic(range, d.description, severity);
        diagnostic.source = 'WSDC (Slither)';
        diagnostic.code = d.check;
        if (!diagnosticsMap.has(findingFilePath)) {
            diagnosticsMap.set(findingFilePath, []);
        }
        diagnosticsMap.get(findingFilePath)?.push(diagnostic);
    }
    // Clear existing
    diagnosticCollection.clear();
    // Map the string paths back to VS Code URIs
    for (const [filePath, diagnostics] of diagnosticsMap.entries()) {
        const fileUri = vscode.Uri.file(filePath);
        diagnosticCollection.set(fileUri, diagnostics);
    }
}
function getVscodeSeverity(slitherImpact) {
    const check = slitherImpact.toLowerCase();
    if (check === 'high' || check === 'critical') {
        return vscode.DiagnosticSeverity.Error;
    }
    else if (check === 'medium') {
        return vscode.DiagnosticSeverity.Warning;
    }
    else {
        return vscode.DiagnosticSeverity.Information;
    }
}
export class WsdcCodeActionProvider {
    static providedCodeActionKinds = [
        vscode.CodeActionKind.QuickFix
    ];
    provideCodeActions(document, range, context) {
        // Find WSDC diagnostics at this range
        const wsdcDiagnostics = context.diagnostics.filter(d => d.source === 'WSDC (Slither)');
        if (wsdcDiagnostics.length === 0) {
            return;
        }
        const actions = [];
        for (const diagnostic of wsdcDiagnostics) {
            // Provide an "Ask AI" action for each finding
            const action = new vscode.CodeAction(`💡 Ask WSDC AI to explain: ${diagnostic.message}`, vscode.CodeActionKind.QuickFix);
            action.command = {
                command: 'wsdc.explainFinding',
                title: 'Explain Finding',
                arguments: [diagnostic, document]
            };
            action.diagnostics = [diagnostic];
            action.isPreferred = true;
            actions.push(action);
        }
        return actions;
    }
}
async function explainFindingWithAI(diagnostic, document) {
    const config = vscode.workspace.getConfiguration('wsdc');
    const apiKey = config.get('geminiApiKey');
    if (!apiKey) {
        vscode.window.showErrorMessage("WSDC: Gemini API Key not set in settings.");
        return;
    }
    // Capture the code around the vulnerability
    const startLine = Math.max(0, diagnostic.range.start.line - 2);
    const endLine = Math.min(document.lineCount - 1, diagnostic.range.end.line + 5);
    const codeSnippet = document.getText(new vscode.Range(startLine, 0, endLine, 1000));
    const prompt = `
You are WSDC, an expert Web3 Security Co-Pilot. Explain this Slither vulnerability concisely:
Check: ${diagnostic.code}
Message: ${diagnostic.message}

Code Snippet:
\`\`\`solidity
${codeSnippet}
\`\`\`

Provide an Exploit Scenario and exactly 1 code fix suggestion. Format as markdown.
    `;
    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: "WSDC: Asking Gemini...",
        cancellable: false
    }, async () => {
        try {
            const ai = new GoogleGenAI({ apiKey: apiKey });
            const response = await ai.models.generateContent({
                model: 'gemini-2.5-flash',
                contents: prompt,
            });
            // Create a webview panel to show the answer
            const panel = vscode.window.createWebviewPanel('wsdcExplanation', 'WSDC Vulnerability Analysis', vscode.ViewColumn.Beside, { enableScripts: true });
            // Simple Markdown rendering hook
            const content = response.text || "No response generated.";
            // We use simple HTML wrapper because a full markdown parser is heavy, but VS Code allows us to render it natively via MarkdownString
            // For now, displaying as plaintext/simple html in webview
            panel.webview.html = `
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <style>
                    body { font-family: var(--vscode-editor-font-family); padding: 20px; line-height: 1.6; }
                    pre { background: var(--vscode-textCodeBlock-background); padding: 10px; border-radius: 5px; overflow-x: auto;}
                </style>
            </head>
            <body>
                <h2>WSDC Analysis</h2>
                <pre style="white-space: pre-wrap; font-family: inherit;">${content}</pre>
            </body>
            </html>
            `;
        }
        catch (e) {
            vscode.window.showErrorMessage(`WSDC AI Error: ${e.message}`);
        }
    });
}
export function deactivate() { }
//# sourceMappingURL=extension.js.map