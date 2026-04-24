let editor;
let globalProblems = {}; // Store descriptions
let solvedProblemIds = new Set();

require(['vs/editor/editor.main'], function () {
    editor = monaco.editor.create(document.getElementById('editor'), {
        value: '# Write your code here...\n\nprint("Hello, InterviewIQ!")\n',
        language: 'python',
        theme: 'vs-dark',
        automaticLayout: true,
        fontSize: 14
    });

    if (ACTIVE_PROBLEM_TITLE) {
        document.getElementById('active-problem-display').style.display = 'block';
        document.getElementById('current-problem-title').innerText = ACTIVE_PROBLEM_TITLE;

        const header = `// Solving: ${ACTIVE_PROBLEM_TITLE}\n// ======================================\n\n`;
        editor.setValue(header + editor.getValue());
    }

    document.getElementById('language-select').addEventListener('change', function (e) {
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

    document.getElementById('snippet-select').addEventListener('change', function(e) {
        const val = e.target.value;
        if (!val) return;

        const snippets = {
            'bfs': `def bfs(graph, start):\n    visited = set([start])\n    queue = collections.deque([start])\n    while queue:\n        node = queue.popleft()\n        for neighbor in graph[node]:\n            if neighbor not in visited:\n                visited.add(neighbor)\n                queue.append(neighbor)`,
            'dfs': `def dfs(graph, node, visited=None):\n    if visited is None: visited = set()\n    visited.add(node)\n    for neighbor in graph[node]:\n        if neighbor not in visited:\n            dfs(graph, neighbor, visited)`,
            'binsearch': `def binary_search(arr, target):\n    low, high = 0, len(arr) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == target: return mid\n        elif arr[mid] < target: low = mid + 1\n        else: high = mid - 1\n    return -1`,
            'dijkstra': `import heapq\ndef dijkstra(graph, start):\n    distances = {node: float('inf') for node in graph}\n    distances[start] = 0\n    pq = [(0, start)]\n    while pq:\n        dist, u = heapq.heappop(pq)\n        if dist > distances[u]: continue\n        for v, weight in graph[u].items():\n            if distances[u] + weight < distances[v]:\n                distances[v] = distances[u] + weight\n                heapq.heappush(pq, (distances[v], v))`
        };

        const currentText = editor.getValue();
        editor.setValue(currentText + "\n\n" + (snippets[val] || ""));
        e.target.value = ""; // Reset
    });
});

document.getElementById('btn-run').addEventListener('click', async function () {
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

document.getElementById('btn-submit').addEventListener('click', async function () {
    const code = editor.getValue();
    const language = document.getElementById('language-select').value;
    const consolePane = document.getElementById('console-pane');
    
    // Get the current active problem ID from global scope or details pane
    const activeProblemId = window.currentProblemId;
    if (!activeProblemId) {
        alert("Please select a problem from the list first!");
        return;
    }

    consolePane.innerHTML = '<div style="color: #7c4dff;">Submitting solution...</div>';

    try {
        const response = await fetch('/api/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                problem_id: activeProblemId, 
                code: code, 
                language: language 
            })
        });

        const data = await response.json();

        if (data.error) {
            consolePane.innerHTML = `<div class="status-error">Submission Error: ${data.error}</div>`;
            return;
        }

        let outputHtml = `<div class="${data.status === 'Accepted' ? 'status-success' : 'status-error'}">Submission Status: ${data.status}</div>`;
        outputHtml += `<div style="margin-top: 5px; font-weight: bold; color: ${data.status === 'Accepted' ? '#4CAF50' : '#f44336'}">${data.message}</div>`;

        if (data.output) {
            outputHtml += `<pre style="margin-top: 10px; white-space: pre-wrap; background: rgba(0,0,0,0.2); padding: 10px; border-radius: 4px;">${data.output}</pre>`;
        }
        if (data.stderr) {
            outputHtml += `<pre class="status-error" style="margin-top: 10px; white-space: pre-wrap;">${data.stderr}</pre>`;
        }

        consolePane.innerHTML = outputHtml;

        if (data.status === 'Accepted') {
            loadMyCollection(); // Refresh lists to show green checkmark
        }

    } catch (err) {
        consolePane.innerHTML = `<div class="status-error">Submission failed: ${err.message}</div>`;
    }
});

async function loadProblems() {
    const problemList = document.getElementById('problem-list');
    try {
        const response = await fetch('/api/problems');
        const data = await response.json();

        if (data.problems && data.problems.length > 0) {
            problemList.innerHTML = '';
            data.problems.forEach(p => {
                // Metadata cached, but description is now fetched on-demand
                globalProblems[p.id] = p; 
                const isSolved = solvedProblemIds.has(p.id);
                const card = document.createElement('div');
                card.className = 'problem-card d-flex justify-content-between align-items-center';
                card.onclick = () => showProblemDetails(p.id);
                card.innerHTML = `
                    <div style="flex: 1;">
                        <div style="font-weight: bold;">
                            ${p.title} ${isSolved ? '<span style="color: #4CAF50; margin-left: 5px;">✅</span>' : ''}
                        </div>
                        <div style="font-size: 0.85em; margin-top: 5px;">
                            <span class="difficulty-${p.difficulty}">${p.difficulty}</span> | 
                            <span style="color: #888;">${p.platform}</span>
                        </div>
                    </div>
                    <button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); addToCollection(${p.id})">+</button>
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

async function addToCollection(problemId) {
    try {
        const response = await fetch('/api/collection/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ problem_id: problemId })
        });
        const data = await response.json();
        alert(data.message || data.error);
        if (!data.error) {
            loadMyCollection();
        }
    } catch (err) {
        alert('Failed to add: ' + err.message);
    }
}

async function loadMyCollection() {
    const collectionList = document.getElementById('my-questions-list');
    try {
        const response = await fetch('/api/collection');
        const data = await response.json();

        if (data.problems && data.problems.length > 0) {
            collectionList.innerHTML = '';
            data.problems.forEach(p => {
                if (p.status === 'solved') solvedProblemIds.add(p.id);
                const isSolved = p.status === 'solved';
                const card = document.createElement('div');
                card.className = 'problem-card d-flex justify-content-between align-items-center';
                card.style.borderLeft = isSolved ? '4px solid #4CAF50' : '4px solid #555';
                card.onclick = () => showProblemDetails(p.id);
                card.innerHTML = `
                    <div style="flex: 1;">
                        <div style="font-weight: bold;">${p.title} ${isSolved ? '✅' : ''}</div>
                        <div style="font-size: 0.85em; margin-top: 5px;">
                            <span class="difficulty-${p.difficulty}">${p.difficulty}</span> | 
                            <span style="color: #888;">${p.platform}</span>
                        </div>
                    </div>
                    ${isSolved ? '<span class="status-success" style="font-size: 0.8rem;">SOLVED</span>' : '<span style="color: #666; font-size: 0.8rem;">PENDING</span>'}
                `;
                collectionList.appendChild(card);
            });
            // Re-render global list to show ticks if needed
            loadProblems(); 
        } else {
            collectionList.innerHTML = '<p>Your collection is empty.</p>';
        }
    } catch (err) {
        collectionList.innerHTML = `<p class="status-error">Failed to load collection: ${err.message}</p>`;
    }
}

async function toggleStatus(problemId, currentStatus) {
    try {
        const response = await fetch('/api/collection/toggle-status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ problem_id: problemId, status: currentStatus })
        });
        const data = await response.json();
        if (!data.error) {
            loadMyCollection();
        } else {
            alert(data.error);
        }
    } catch (err) {
        alert('Failed to update status: ' + err.message);
    }
}
document.getElementById('btn-sync').addEventListener('click', async function () {
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

async function loadMyQuestions() {
    const questionList = document.getElementById('my-questions-list');
    // We are replacing this with loadMyCollection for the "Add Question" feature.
    // If the user still wants their manual questions, we might need another section.
    // But per instructions, "Dashboard shows progress = solved / total" where total is added questions.
}

async function showProblemDetails(problemId) {
    window.currentProblemId = problemId; // Store for submission
    let p = globalProblems[problemId];
    
    // If description is missing, fetch full details
    if (!p || !p.description) {
        const detailsPane = document.getElementById('active-problem-details');
        detailsPane.style.display = 'block';
        document.getElementById('detail-title').innerText = "Loading details...";
        document.getElementById('detail-description').innerText = "";

        try {
            const response = await fetch(`/api/problems/${problemId}`);
            const data = await response.json();
            if (data.error) throw new Error(data.error);
            p = data;
            globalProblems[problemId] = p; // Cache full details
        } catch (err) {
            document.getElementById('detail-title').innerText = "Error loading details";
            document.getElementById('detail-description').innerText = err.message;
            return;
        }
    }

    document.getElementById('active-problem-details').style.display = 'block';
    document.getElementById('detail-title').innerText = p.title;
    document.getElementById('detail-meta').innerHTML = `
        <span class="difficulty-${p.difficulty}">${p.difficulty}</span> | 
        <span>${p.platform}</span> | 
        <a href="${p.url}" target="_blank" style="color: #4daaf1;">External Link</a>
    `;
    document.getElementById('detail-description').innerText = p.description || "No description available.";

    // Also update editor header
    document.getElementById('active-problem-display').style.display = 'block';
    document.getElementById('current-problem-title').innerText = p.title;
}

// Initial load
window.addEventListener('DOMContentLoaded', () => {
    loadMyCollection(); // This will trigger loadProblems after fetching solved IDs
});
