// Setup Monaco Editor
let editor;

require(['vs/editor/editor.main'], function () {
    editor = monaco.editor.create(document.getElementById('editor'), {
        value: '# Write your code here...\n\nprint("Hello, InterviewIQ!")\n',
        language: 'python',
        theme: 'vs-dark',
        automaticLayout: true,
        fontSize: 14
    });

    // Handle language change
    document.getElementById('language-select').addEventListener('change', function(e) {
        let lang = e.target.value;
        let monacoLang = lang;
        let defaultCode = "";
        
        if (lang === 'cpp') {
            monacoLang = 'cpp';
            defaultCode = "#include <iostream>\nusing namespace std;\n\nint main() {\n    cout << \"Hello, InterviewIQ!\" << endl;\n    return 0;\n}";
        } else if (lang === 'java') {
            monacoLang = 'java';
            defaultCode = "public class Main {\n    public static void main(String[] args) {\n        System.out.println(\"Hello, InterviewIQ!\");\n    }\n}";
        } else if (lang === 'javascript') {
            monacoLang = 'javascript';
            defaultCode = "console.log('Hello, InterviewIQ!');";
        } else {
            monacoLang = 'python';
            defaultCode = "print('Hello, InterviewIQ!')";
        }

        monaco.editor.setModelLanguage(editor.getModel(), monacoLang);
        editor.setValue(defaultCode);
    });
});

// Run Code Functionality
document.getElementById('btn-run').addEventListener('click', async function() {
    const code = editor.getValue();
    const language = document.getElementById('language-select').value;
    const consolePane = document.getElementById('console-pane');
    
    consolePane.innerHTML = '<div style="color: #aaa;">Running code...</div>';
    
    try {
        const response = await fetch('/api/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ code: code, language: language })
        });
        
        const data = await response.json();
        
        if (data.error) {
            consolePane.innerHTML = `<div class="status-error">System Error: ${data.error}</div>`;
            if (data.details) {
                consolePane.innerHTML += `<div class="status-error">${data.details}</div>`;
            }
            return;
        }
        
        let outputHtml = `<div class="${data.status === 'Success' ? 'status-success' : 'status-error'}">Status: ${data.status}</div>`;
        
        if (data.output) {
            outputHtml += `<pre style="margin-top: 10px; white-space: pre-wrap; word-wrap: break-word;">${data.output.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>`;
        }
        if (data.stderr) {
            outputHtml += `<pre class="status-error" style="margin-top: 10px; white-space: pre-wrap; word-wrap: break-word;">${data.stderr.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>`;
        }
        
        consolePane.innerHTML = outputHtml;
        
    } catch (err) {
        consolePane.innerHTML = `<div class="status-error">Request failed: ${err.message}</div>`;
    }
});

// Load Problems
async function loadProblems() {
    const problemList = document.getElementById('problem-list');
    try {
        const response = await fetch('/api/problems');
        const data = await response.json();
        
        if (data.problems && data.problems.length > 0) {
            problemList.innerHTML = '';
            data.problems.forEach(p => {
                const card = document.createElement('div');
                card.className = 'problem-card';
                card.innerHTML = `
                    <div style="font-weight: bold;">${p.title}</div>
                    <div style="font-size: 0.9em; margin-top: 5px;">
                        <span class="difficulty-${p.difficulty}">${p.difficulty}</span> | 
                        <a href="${p.url}" target="_blank" style="color: #4daaf1; text-decoration: none;">View on ${p.platform}</a>
                    </div>
                `;
                problemList.appendChild(card);
            });
        } else {
            problemList.innerHTML = '<p>No problems found. Click "Sync Daily Problems" to fetch them.</p>';
        }
    } catch (err) {
        problemList.innerHTML = `<p class="status-error">Failed to load problems: ${err.message}</p>`;
    }
}

// Sync Problems
document.getElementById('btn-sync').addEventListener('click', async function() {
    const btn = this;
    const originalText = btn.innerText;
    btn.innerText = 'Syncing...';
    btn.disabled = true;
    
    try {
        const response = await fetch('/api/problems/sync', { method: 'POST' });
        const data = await response.json();
        
        if (data.error) {
            alert('Error syncing: ' + data.error);
        } else {
            alert(data.message + `\nEasy: ${data.stats.easy}, Medium: ${data.stats.medium}, Hard: ${data.stats.hard}`);
            loadProblems();
        }
    } catch (err) {
        alert('Sync failed: ' + err.message);
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
});

// Initial load
window.addEventListener('DOMContentLoaded', loadProblems);
