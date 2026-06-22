let editor;
let globalProblems = {}; // Store descriptions
let solvedProblemIds = new Set();

require(['vs/editor/editor.main'], function () {
    editor = monaco.editor.create(document.getElementById('editor'), {
        value: '# Write your code here...\n\nprint("Hello, SolvePilot!")\n',
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
            defaultCode = "#include <iostream>\nusing namespace std;\n\nint main() {\n    cout << \"Hello, SolvePilot!\" << endl;\n    return 0;\n}";
        } else if (lang === 'java') {
            monacoLang = 'java';
            defaultCode = "public class Main {\n    public static void main(String[] args) {\n        System.out.println(\"Hello, SolvePilot!\");\n    }\n}";
        } else if (lang === 'javascript') {
            monacoLang = 'javascript';
            defaultCode = "console.log('Hello, SolvePilot!');";
        } else {
            monacoLang = 'python';
            defaultCode = "print('Hello, SolvePilot!')";
        }

        monaco.editor.setModelLanguage(editor.getModel(), monacoLang);
        editor.setValue(defaultCode);
    });

    document.getElementById('snippet-select').addEventListener('change', function(e) {
        const val = e.target.value;
        if (!val) return;

        const lang = document.getElementById('language-select').value;

        const allSnippets = {
            python: {
                'bfs': `def bfs(graph, start):\n    visited = set([start])\n    queue = collections.deque([start])\n    while queue:\n        node = queue.popleft()\n        for neighbor in graph[node]:\n            if neighbor not in visited:\n                visited.add(neighbor)\n                queue.append(neighbor)`,
                'dfs': `def dfs(graph, node, visited=None):\n    if visited is None: visited = set()\n    visited.add(node)\n    for neighbor in graph[node]:\n        if neighbor not in visited:\n            dfs(graph, neighbor, visited)`,
                'binsearch': `def binary_search(arr, target):\n    low, high = 0, len(arr) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == target: return mid\n        elif arr[mid] < target: low = mid + 1\n        else: high = mid - 1\n    return -1`,
                'dijkstra': `import heapq\ndef dijkstra(graph, start):\n    distances = {node: float('inf') for node in graph}\n    distances[start] = 0\n    pq = [(0, start)]\n    while pq:\n        dist, u = heapq.heappop(pq)\n        if dist > distances[u]: continue\n        for v, weight in graph[u].items():\n            if distances[u] + weight < distances[v]:\n                distances[v] = distances[u] + weight\n                heapq.heappush(pq, (distances[v], v))`
            },
            cpp: {
                'bfs': `#include <queue>\n#include <unordered_set>\nvoid bfs(vector<vector<int>>& graph, int start) {\n    unordered_set<int> visited;\n    queue<int> q;\n    visited.insert(start);\n    q.push(start);\n    while (!q.empty()) {\n        int node = q.front(); q.pop();\n        for (int neighbor : graph[node]) {\n            if (visited.find(neighbor) == visited.end()) {\n                visited.insert(neighbor);\n                q.push(neighbor);\n            }\n        }\n    }\n}`,
                'dfs': `#include <unordered_set>\nvoid dfs(vector<vector<int>>& graph, int node, unordered_set<int>& visited) {\n    visited.insert(node);\n    for (int neighbor : graph[node]) {\n        if (visited.find(neighbor) == visited.end()) {\n            dfs(graph, neighbor, visited);\n        }\n    }\n}`,
                'binsearch': `int binarySearch(vector<int>& arr, int target) {\n    int low = 0, high = arr.size() - 1;\n    while (low <= high) {\n        int mid = low + (high - low) / 2;\n        if (arr[mid] == target) return mid;\n        else if (arr[mid] < target) low = mid + 1;\n        else high = mid - 1;\n    }\n    return -1;\n}`,
                'dijkstra': `#include <queue>\n#include <vector>\n#include <climits>\nvoid dijkstra(vector<vector<pair<int,int>>>& graph, int start, vector<int>& dist) {\n    dist.assign(graph.size(), INT_MAX);\n    dist[start] = 0;\n    priority_queue<pair<int,int>, vector<pair<int,int>>, greater<>> pq;\n    pq.push({0, start});\n    while (!pq.empty()) {\n        auto [d, u] = pq.top(); pq.pop();\n        if (d > dist[u]) continue;\n        for (auto [v, w] : graph[u]) {\n            if (dist[u] + w < dist[v]) {\n                dist[v] = dist[u] + w;\n                pq.push({dist[v], v});\n            }\n        }\n    }\n}`
            },
            java: {
                'bfs': `import java.util.*;\nvoid bfs(List<List<Integer>> graph, int start) {\n    Set<Integer> visited = new HashSet<>();\n    Queue<Integer> queue = new LinkedList<>();\n    visited.add(start);\n    queue.add(start);\n    while (!queue.isEmpty()) {\n        int node = queue.poll();\n        for (int neighbor : graph.get(node)) {\n            if (!visited.contains(neighbor)) {\n                visited.add(neighbor);\n                queue.add(neighbor);\n            }\n        }\n    }\n}`,
                'dfs': `import java.util.*;\nvoid dfs(List<List<Integer>> graph, int node, Set<Integer> visited) {\n    visited.add(node);\n    for (int neighbor : graph.get(node)) {\n        if (!visited.contains(neighbor)) {\n            dfs(graph, neighbor, visited);\n        }\n    }\n}`,
                'binsearch': `int binarySearch(int[] arr, int target) {\n    int low = 0, high = arr.length - 1;\n    while (low <= high) {\n        int mid = low + (high - low) / 2;\n        if (arr[mid] == target) return mid;\n        else if (arr[mid] < target) low = mid + 1;\n        else high = mid - 1;\n    }\n    return -1;\n}`,
                'dijkstra': `import java.util.*;\nvoid dijkstra(List<List<int[]>> graph, int start, int[] dist) {\n    Arrays.fill(dist, Integer.MAX_VALUE);\n    dist[start] = 0;\n    PriorityQueue<int[]> pq = new PriorityQueue<>((a, b) -> a[0] - b[0]);\n    pq.offer(new int[]{0, start});\n    while (!pq.isEmpty()) {\n        int[] top = pq.poll();\n        int d = top[0], u = top[1];\n        if (d > dist[u]) continue;\n        for (int[] edge : graph.get(u)) {\n            int v = edge[0], w = edge[1];\n            if (dist[u] + w < dist[v]) {\n                dist[v] = dist[u] + w;\n                pq.offer(new int[]{dist[v], v});\n            }\n        }\n    }\n}`
            },
            javascript: {
                'bfs': `function bfs(graph, start) {\n    const visited = new Set([start]);\n    const queue = [start];\n    while (queue.length > 0) {\n        const node = queue.shift();\n        for (const neighbor of graph[node]) {\n            if (!visited.has(neighbor)) {\n                visited.add(neighbor);\n                queue.push(neighbor);\n            }\n        }\n    }\n}`,
                'dfs': `function dfs(graph, node, visited = new Set()) {\n    visited.add(node);\n    for (const neighbor of graph[node]) {\n        if (!visited.has(neighbor)) {\n            dfs(graph, neighbor, visited);\n        }\n    }\n}`,
                'binsearch': `function binarySearch(arr, target) {\n    let low = 0, high = arr.length - 1;\n    while (low <= high) {\n        const mid = Math.floor((low + high) / 2);\n        if (arr[mid] === target) return mid;\n        else if (arr[mid] < target) low = mid + 1;\n        else high = mid - 1;\n    }\n    return -1;\n}`,
                'dijkstra': `function dijkstra(graph, start) {\n    const dist = {};\n    for (const node in graph) dist[node] = Infinity;\n    dist[start] = 0;\n    const pq = [[0, start]];\n    while (pq.length > 0) {\n        pq.sort((a, b) => a[0] - b[0]);\n        const [d, u] = pq.shift();\n        if (d > dist[u]) continue;\n        for (const [v, w] of Object.entries(graph[u])) {\n            if (dist[u] + w < dist[v]) {\n                dist[v] = dist[u] + w;\n                pq.push([dist[v], v]);\n            }\n        }\n    }\n    return dist;\n}`
            }
        };

        const snippets = allSnippets[lang] || allSnippets['python'];
        const currentText = editor.getValue();
        editor.setValue(currentText + "\n\n" + (snippets[val] || ""));
        e.target.value = ""; // Reset
    });

    // AI Sidebar Toggle
    document.getElementById('btn-ask-ai').addEventListener('click', () => {
        document.getElementById('ai-sidebar').classList.add('active');
    });

    document.getElementById('close-ai').addEventListener('click', () => {
        document.getElementById('ai-sidebar').classList.remove('active');
    });

    // Custom Input Toggle Logic
    const checkCustomInput = document.getElementById('check-custom-input');
    const inputPane = document.getElementById('input-pane');
    if (checkCustomInput && inputPane) {
        checkCustomInput.addEventListener('change', function() {
            inputPane.style.display = this.checked ? 'block' : 'none';
        });
    }

    // Chat Logic
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('btn-send-chat');
    let chatHistory = []; // Track conversation history


    const appendMessage = (text, role) => {
        const container = document.getElementById('chat-messages');
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}`;
        
        // Use a library for markdown if available, else simple replacement
        // For now, let's just use textContent and handle line breaks
        msgDiv.innerText = text;
        container.appendChild(msgDiv);
        container.scrollTop = container.scrollHeight;
    };

    const sendChatMessage = async () => {
        const query = chatInput.value.trim();
        if (!query) return;

        appendMessage(query, 'user');
        chatInput.value = '';
        
        const code = editor.getValue();
        const language = document.getElementById('language-select').value;
        const problemId = window.currentProblemId;

        // Show loading state
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message ai';
        loadingDiv.innerText = 'Thinking...';
        document.getElementById('chat-messages').appendChild(loadingDiv);

        try {
            const response = await fetch('/api/ai/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: query,
                    code: code,
                    language: language,
                    problem_id: problemId,
                    history: chatHistory
                })
            });

            const data = await response.json();
            loadingDiv.remove();

            if (data.error) {
                appendMessage("Sorry, I encountered an error: " + data.error, 'ai');
            } else {
                appendMessage(data.response, 'ai');
                // Store in history
                chatHistory.push({ role: 'user', content: query });
                chatHistory.push({ role: 'assistant', content: data.response });
            }

        } catch (err) {
            loadingDiv.remove();
            appendMessage("Request failed: " + err.message, 'ai');
        }
    };

    sendBtn.addEventListener('click', sendChatMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChatMessage();
    });
});


document.getElementById('btn-run').addEventListener('click', async function () {
    const code = editor.getValue();
    const language = document.getElementById('language-select').value;
    const consolePane = document.getElementById('console-pane');
    const checkCustomInput = document.getElementById('check-custom-input');
    const customStdin = document.getElementById('custom-stdin');

    let stdin = "";
    if (checkCustomInput && checkCustomInput.checked && customStdin) {
        stdin = customStdin.value;
    }

    consolePane.innerHTML = '<div style="color: #aaa;">Running code...</div>';

    try {
        const response = await fetch('/api/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ code: code, language: language, stdin: stdin })
        });

        const data = await response.json();

        if (data.error) {
            const isServerBusy = data.error.includes('temporarily busy') || response.status === 503;
            if (isServerBusy) {
                consolePane.innerHTML = `<div style="color: #FFC107; font-weight: bold;">⏳ Server Busy</div>
                    <div style="color: #FFC107; margin-top: 8px;">${data.error}</div>
                    <div style="color: #888; margin-top: 5px; font-size: 0.9em;">This is not a problem with your code. The execution server is overloaded — just try again.</div>`;
            } else {
                consolePane.innerHTML = `<div class="status-error">${data.error}</div>`;
                if (data.details) {
                    consolePane.innerHTML += `<div class="status-error">${data.details}</div>`;
                }
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

        // Handle server busy status
        if (data.status === 'Server Busy') {
            consolePane.innerHTML = `<div style="color: #FFC107; font-weight: bold;">⏳ Server Busy</div>
                <div style="color: #FFC107; margin-top: 8px;">${data.message}</div>
                <div style="color: #888; margin-top: 5px; font-size: 0.9em;">This is not a problem with your code. The execution server is overloaded — just try again.</div>`;
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

    // Handle Samples
    const samplesContainer = document.getElementById('samples-container');
    const samplesContent = document.getElementById('detail-samples');
    if (p.samples) {
        samplesContainer.style.display = 'block';
        samplesContent.innerHTML = p.samples; // p.samples contains HTML from scraper
    } else {
        samplesContainer.style.display = 'none';
    }

    // Also update editor header
    document.getElementById('active-problem-display').style.display = 'block';
    document.getElementById('current-problem-title').innerText = p.title;

    // Trigger MathJax re-render for the new content
    if (window.MathJax && window.MathJax.typesetPromise) {
        window.MathJax.typesetPromise();
    }
}

// Initial load
window.addEventListener('DOMContentLoaded', () => {
    loadMyCollection(); // This will trigger loadProblems after fetching solved IDs
});
