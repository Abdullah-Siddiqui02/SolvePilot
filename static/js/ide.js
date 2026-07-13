let editor;
let globalProblems = {}; // Store descriptions
let solvedProblemIds = new Set();
let codeHasRun = false;

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

    // AI Mentor Pane Toggle & Content Populate Logic
    const dummySolutions = {
        python: `def twoSum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []`,
        cpp: `#include <vector>
#include <unordered_map>

class Solution {
public:
    std::vector<int> twoSum(std::vector<int>& nums, int target) {
        std::unordered_map<int, int> seen;
        for (int i = 0; i < nums.size(); ++i) {
            int complement = target - nums[i];
            if (seen.find(complement) != seen.end()) {
                return {seen[complement], i};
            }
            seen[nums[i]] = i;
        }
        return {};
    }
};`,
        java: `import java.util.HashMap;
import java.util.Map;

class Solution {
    public int[] twoSum(int[] nums, int target) {
        Map<Integer, Integer> seen = new HashMap<>();
        for (int i = 0; i < nums.length; i++) {
            int complement = target - nums[i];
            if (seen.containsKey(complement)) {
                return new int[] { seen.get(complement), i };
            }
            seen.put(nums[i], i);
        }
        return new int[] {};
    }
}`,
        javascript: `function twoSum(nums, target) {
    const seen = new Map();
    for (let i = 0; i < nums.length; i++) {
        const complement = target - nums[i];
        if (seen.has(complement)) {
            return [seen.get(complement), i];
        }
        seen.set(nums[i], i);
    }
    return [];
}`
    };

    const mentorPane = document.getElementById('mentor-pane');
    const mentorPlaceholder = document.getElementById('mentor-placeholder');
    const mentorFeedback = document.getElementById('mentor-feedback-content');
    const optCodeBlock = document.getElementById('opt-code-block');
    const optCodeLang = document.getElementById('opt-code-lang');

    // Toggle Mentor Panel Function
    const toggleMentorPane = (show = true) => {
        if (show) {
            mentorPane.style.display = 'flex';
        } else {
            mentorPane.style.display = 'none';
        }
        if (window.editor) {
            window.editor.layout();
        }
    };

    // Ask Mentor Button Handler
    const btnAskMentor = document.getElementById('btn-ask-mentor');
    if (btnAskMentor) {
        btnAskMentor.addEventListener('click', () => {
            toggleMentorPane(true);

            if (codeHasRun) {
                // Show feedback content, hide placeholder
                mentorPlaceholder.style.display = 'none';
                mentorFeedback.style.display = 'block';

                // Populate code snippet based on selected language
                const selectedLang = document.getElementById('language-select').value;
                const formattedLang = selectedLang === 'cpp' ? 'cpp' : (selectedLang === 'javascript' ? 'javascript' : selectedLang);
                optCodeLang.innerText = formattedLang;
                optCodeBlock.innerText = dummySolutions[formattedLang] || dummySolutions['python'];
                
                // Reset Hint card revealed state
                const hintCard = document.getElementById('mentor-hint-card');
                if (hintCard) {
                    hintCard.classList.remove('revealed');
                }

                // Staggered card animation reset by re-applying active animations
                const cards = mentorFeedback.querySelectorAll('.mentor-card');
                cards.forEach(card => {
                    const originalDelay = card.style.animationDelay;
                    card.style.animation = 'none';
                    card.offsetHeight; // Trigger reflow to restart animation
                    card.style.animation = '';
                    card.style.animationDelay = originalDelay;
                });
            } else {
                // Show placeholder content, hide feedback
                mentorPlaceholder.style.display = 'flex';
                mentorFeedback.style.display = 'none';
            }
        });
    }

    // Close Mentor Button Handler
    const btnCloseMentor = document.getElementById('close-mentor');
    if (btnCloseMentor) {
        btnCloseMentor.addEventListener('click', () => {
            toggleMentorPane(false);
        });
    }

    // Hint Reveal Card Click Handler
    const hintCard = document.getElementById('mentor-hint-card');
    if (hintCard) {
        hintCard.addEventListener('click', function() {
            this.classList.add('revealed');
        });
    }

    // Copy Code Button Click Handler
    const btnCopyOptCode = document.getElementById('btn-copy-opt-code');
    if (btnCopyOptCode) {
        btnCopyOptCode.addEventListener('click', (e) => {
            e.stopPropagation(); // prevent card container events
            const codeText = optCodeBlock.innerText;
            navigator.clipboard.writeText(codeText).then(() => {
                const originalText = btnCopyOptCode.innerHTML;
                btnCopyOptCode.innerHTML = '✅ Copied!';
                setTimeout(() => {
                    btnCopyOptCode.innerHTML = originalText;
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy code: ', err);
            });
        });
    }

    // Synced Output/Stdin Tabs and Custom Input Checkbox
    window.switchOutputTab = function(tabName) {
        ensureConsoleExpanded();
        document.querySelectorAll('.output-tab-btn').forEach(btn => btn.classList.remove('active'));
        const consolePane = document.getElementById('console-pane');
        const inputPane = document.getElementById('input-pane');
        const checkCustomInput = document.getElementById('check-custom-input');

        if (tabName === 'output') {
            document.getElementById('tab-btn-output').classList.add('active');
            if (consolePane) consolePane.style.display = 'block';
            if (inputPane) inputPane.style.display = 'none';
        } else {
            document.getElementById('tab-btn-stdin').classList.add('active');
            if (consolePane) consolePane.style.display = 'none';
            if (inputPane) inputPane.style.display = 'block';
            if (checkCustomInput) checkCustomInput.checked = true;
        }
    };

    const checkCustomInput = document.getElementById('check-custom-input');
    if (checkCustomInput) {
        checkCustomInput.addEventListener('change', function() {
            if (this.checked) {
                switchOutputTab('stdin');
            } else {
                switchOutputTab('output');
            }
        });
    }

    // Reset Code Logic
    const btnReset = document.getElementById('btn-reset');
    if (btnReset) {
        btnReset.addEventListener('click', function() {
            if (confirm("Are you sure you want to reset the editor to the default template? This will discard your current code.")) {
                const langSelect = document.getElementById('language-select');
                langSelect.dispatchEvent(new Event('change'));
            }
        });
    }

    // Problem Pane Tabs Logic
    window.switchProblemTab = function(tabName) {
        const descTab = document.getElementById('tab-btn-desc');
        const listTab = document.getElementById('tab-btn-list');
        const descPanel = document.getElementById('problem-desc-panel');
        const listPanel = document.getElementById('problem-list-panel');

        if (tabName === 'desc') {
            if (descTab) descTab.classList.add('active');
            if (listTab) listTab.classList.remove('active');
            if (descPanel) descPanel.style.display = 'block';
            if (listPanel) listPanel.style.display = 'none';
        } else {
            if (descTab) descTab.classList.remove('active');
            if (listTab) listTab.classList.add('active');
            if (descPanel) descPanel.style.display = 'none';
            if (listPanel) listPanel.style.display = 'block';
        }
    };

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

// Interactive execution state variables
let currentInputs = [];
let terminalHistory = "";
let previousStdout = "";
let isInteractiveMode = false;

// Ensure output console is expanded
function ensureConsoleExpanded() {
    const outputPane = document.querySelector('.output-pane');
    if (outputPane && outputPane.classList.contains('collapsed')) {
        outputPane.classList.remove('collapsed');
    }
}

// Append inline STDIN input prompt at the bottom of console results
function appendInlineStdinPrompt(consolePane) {
    if (!consolePane) return;
    if (isInteractiveMode) return; // Skip if in interactive session
    
    // Check if inline prompt already exists in consolePane
    const existingPrompt = consolePane.querySelector('.console-input-prompt');
    if (existingPrompt) {
        existingPrompt.remove();
    }

    const promptDiv = document.createElement('div');
    promptDiv.className = 'console-input-prompt mt-3 p-2 d-flex align-items-end gap-2';
    promptDiv.style.borderTop = '1px solid var(--surface-border)';
    promptDiv.style.background = 'rgba(15, 23, 42, 0.3)';
    promptDiv.style.borderRadius = '8px';

    const customStdinVal = document.getElementById('custom-stdin')?.value || '';

    promptDiv.innerHTML = `
        <span style="font-size: 0.8rem; color: var(--text-secondary); padding-bottom: 6px; white-space: nowrap;">⌨ STDIN:</span>
        <textarea id="console-inline-stdin" placeholder="Type input for next run (Enter to run, Shift+Enter for newline)..." style="flex: 1; background: transparent; border: none; color: #fff; font-size: 0.85rem; outline: none; resize: none; height: 32px; line-height: 1.4;" rows="1">${customStdinVal}</textarea>
        <button id="btn-console-run" class="btn btn-sm btn-primary" style="font-size: 0.75rem; padding: 4px 10px; height: 30px; white-space: nowrap;">Run Code</button>
    `;

    consolePane.appendChild(promptDiv);
    consolePane.scrollTop = consolePane.scrollHeight;

    const textarea = document.getElementById('console-inline-stdin');
    const runBtn = document.getElementById('btn-console-run');

    const triggerReRun = () => {
        const val = textarea.value;
        const customStdin = document.getElementById('custom-stdin');
        const checkCustomInput = document.getElementById('check-custom-input');
        
        if (customStdin) customStdin.value = val;
        if (checkCustomInput) checkCustomInput.checked = true;

        document.getElementById('btn-run').click();
    };

    if (textarea) {
        textarea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                triggerReRun();
            }
        });
        
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight > 120 ? 120 : this.scrollHeight) + 'px';
            consolePane.scrollTop = consolePane.scrollHeight;
        });
    }

    if (runBtn) {
        runBtn.addEventListener('click', triggerReRun);
    }
}

// Render interactive terminal interface
function renderInteractiveTerminal(consolePane, history, code, language) {
    consolePane.innerHTML = `
        <div class="status-info" style="color: var(--primary); font-weight: 600; margin-bottom: 8px;">Status: Waiting for Input...</div>
        <div class="terminal-mock font-monospace p-3" style="background: rgba(9, 13, 22, 0.9); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; font-size: 0.88rem; line-height: 1.6; color: #f8fafc; overflow-y: auto; max-height: 240px; white-space: pre-wrap; word-wrap: break-word; font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;">
<span id="terminal-history-text">${history.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</span>
<div class="terminal-input-line d-flex align-items-center" style="margin: 0; padding: 0;">
<input type="text" id="terminal-active-input" style="flex: 1; background: transparent; border: none; color: #38bdf8; outline: none; font-family: inherit; font-size: inherit; padding: 0; margin: 0;" autofocus autocomplete="off">
</div></div>
        <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 6px;">Press Enter to submit input to program.</div>
    `;

    const inputField = document.getElementById('terminal-active-input');
    if (inputField) {
        inputField.focus();
        
        inputField.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const val = inputField.value;
                inputField.disabled = true;
                
                terminalHistory += val + '\n';
                currentInputs.push(val);

                executeCodeStep(code, language);
            }
        });

        const terminalMock = consolePane.querySelector('.terminal-mock');
        if (terminalMock) {
            terminalMock.addEventListener('click', () => {
                inputField.focus();
            });
        }
    }
}

// Interactive execution step-by-step executor
async function executeCodeStep(code, language) {
    const consolePane = document.getElementById('console-pane');
    const stdin = currentInputs.join('\n');

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
                    <div style="color: #FFC107; margin-top: 8px;">${data.error}</div>`;
            } else {
                consolePane.innerHTML = `<div class="status-error">${data.error}</div>`;
            }
            isInteractiveMode = false;
            return;
        }

        const isEOFError = data.stderr && (
            data.stderr.includes("EOFError") || 
            data.stderr.includes("NoSuchElementException") || 
            data.stderr.includes("EOF when reading a line")
        );

        const stdoutVal = data.output || "";
        let newStdout = "";
        if (stdoutVal.startsWith(previousStdout)) {
            newStdout = stdoutVal.substring(previousStdout.length);
        } else {
            newStdout = stdoutVal;
        }
        previousStdout = stdoutVal;

        terminalHistory += newStdout;

        if (isEOFError) {
            isInteractiveMode = true;
            renderInteractiveTerminal(consolePane, terminalHistory, code, language);
        } else {
            isInteractiveMode = false;
            let outputHtml = `<div class="${data.status === 'Success' ? 'status-success' : 'status-error'}">Status: ${data.status}</div>`;
            outputHtml += `<pre class="terminal-output mt-2 p-3" style="background: rgba(9, 13, 22, 0.9); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace; white-space: pre-wrap; word-wrap: break-word; color: #cbd5e1; line-height: 1.6; max-height: 240px; overflow-y: auto;">${terminalHistory.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>`;
            
            if (data.stderr && !isEOFError) {
                outputHtml += `<pre class="status-error mt-2" style="white-space: pre-wrap; word-wrap: break-word; background-color: rgba(239, 68, 68, 0.04); border: 1px dashed rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 12px 16px; font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 0.85rem; border-radius: 8px;">${data.stderr.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>`;
            }

            consolePane.innerHTML = outputHtml;
        }

    } catch (err) {
        consolePane.innerHTML = `<div class="status-error">Execution failed: ${err.message}</div>`;
        isInteractiveMode = false;
    } finally {
        appendInlineStdinPrompt(consolePane);
    }
}

// Toggle console panel collapse state
document.addEventListener('DOMContentLoaded', () => {
    const btnToggleConsole = document.getElementById('btn-toggle-console');
    const outputPane = document.querySelector('.output-pane');
    if (btnToggleConsole && outputPane) {
        btnToggleConsole.addEventListener('click', () => {
            outputPane.classList.toggle('collapsed');
        });
    }
});


document.getElementById('btn-run').addEventListener('click', async function () {
    codeHasRun = true;
    ensureConsoleExpanded();
    const code = editor.getValue();
    const language = document.getElementById('language-select').value;
    const consolePane = document.getElementById('console-pane');
    const checkCustomInput = document.getElementById('check-custom-input');
    const customStdin = document.getElementById('custom-stdin');

    currentInputs = [];
    terminalHistory = "";
    previousStdout = "";
    isInteractiveMode = false;

    if (checkCustomInput && checkCustomInput.checked && customStdin && customStdin.value.trim()) {
        currentInputs = customStdin.value.split('\n');
    }

    consolePane.innerHTML = '<div style="color: #aaa;">Running code...</div>';
    
    executeCodeStep(code, language);
});

document.getElementById('btn-submit').addEventListener('click', async function () {
    codeHasRun = true;
    ensureConsoleExpanded();
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
            consolePane.innerHTML = `<div class="status-error" style="color: #fb923c !important; background: rgba(251, 146, 60, 0.08); border: 1px solid rgba(251, 146, 60, 0.2); display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 8px; font-weight: 600;">⏳ Server Busy</div>
                <div style="color: #fb923c; margin-top: 8px; font-weight: 600; font-size: 0.95rem;">${data.message}</div>
                <div style="color: var(--text-secondary); margin-top: 6px; font-size: 0.85rem; line-height: 1.5;">This is not a problem with your code. The execution server is overloaded — just try again.</div>`;
            return;
        }

        let outputHtml = `<div class="${data.status === 'Accepted' ? 'status-success' : 'status-error'}">Submission Status: ${data.status}</div>`;
        outputHtml += `<div style="margin-top: 8px; font-weight: 600; color: ${data.status === 'Accepted' ? '#10b981' : '#f87171'}; font-size: 0.95rem;">${data.message}</div>`;

        if (data.output) {
            outputHtml += `<pre style="margin-top: 12px; white-space: pre-wrap; background: rgba(9, 13, 22, 0.6); border: 1px solid rgba(255, 255, 255, 0.06); padding: 14px; border-radius: 10px; color: #cbd5e1; font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 0.88rem; line-height: 1.6;">${data.output}</pre>`;
        }
        if (data.stderr) {
            outputHtml += `<pre class="status-error" style="margin-top: 12px; white-space: pre-wrap; background-color: rgba(239, 68, 68, 0.04); border: 1px dashed rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 12px 16px; font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 0.85rem; border-radius: 8px;">${data.stderr}</pre>`;
        }

        consolePane.innerHTML = outputHtml;

        if (data.status === 'Accepted') {
            loadMyCollection(); // Refresh lists to show green checkmark
        }

    } catch (err) {
        consolePane.innerHTML = `<div class="status-error">Submission failed: ${err.message}</div>`;
    } finally {
        appendInlineStdinPrompt(consolePane);
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
    
    // Hide empty state and show details container
    const emptyState = document.getElementById('active-problem-empty');
    if (emptyState) emptyState.style.display = 'none';
    const detailsPane = document.getElementById('active-problem-details');
    if (detailsPane) detailsPane.style.display = 'block';
    
    // If description is missing, fetch full details
    if (!p || !p.description) {
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

    // Render tags
    const tagsContainer = document.getElementById('detail-tags');
    if (tagsContainer) {
        tagsContainer.innerHTML = '';
        if (p.tags) {
            const tagsList = p.tags.split(',');
            tagsList.forEach(t => {
                if (t.trim()) {
                    const span = document.createElement('span');
                    span.className = 'tag-pill';
                    span.innerText = t.trim();
                    tagsContainer.appendChild(span);
                }
            });
        }
    }

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

    // Switch to description tab when details are shown
    if (typeof switchProblemTab === 'function') {
        switchProblemTab('desc');
    }
}

// Initial load
window.addEventListener('DOMContentLoaded', () => {
    loadMyCollection().then(() => {
        if (typeof ACTIVE_PROBLEM_ID !== 'undefined' && ACTIVE_PROBLEM_ID) {
            showProblemDetails(ACTIVE_PROBLEM_ID);
        } else {
            if (typeof switchProblemTab === 'function') {
                switchProblemTab('list');
            }
        }
    });

    // Initialize resizer dragging behavior
    const resizer = document.getElementById('console-resizer');
    const outputPane = document.querySelector('.output-pane');
    const editorPane = document.querySelector('.editor-pane');

    if (resizer && outputPane && editorPane) {
        // Shared drag start logic
        const startDrag = () => {
            resizer.classList.add('dragging');
            outputPane.classList.add('no-transition');

            // If output pane is collapsed, temporarily uncollapse it so it starts resizing from its header height
            if (outputPane.classList.contains('collapsed')) {
                outputPane.classList.remove('collapsed');
                outputPane.style.height = '44px';
                outputPane.style.flex = '0 0 44px';
            }
        };

        // Shared move calculation logic
        const dragMove = (clientY, startY, startHeight, totalHeight) => {
            const deltaY = clientY - startY;
            let newHeight = startHeight - deltaY;

            const minHeight = 44; // Tab header height
            const maxHeight = totalHeight - 150; // At least 150px space for editor

            if (newHeight < minHeight) newHeight = minHeight;
            if (newHeight > maxHeight) newHeight = maxHeight;

            outputPane.style.height = `${newHeight}px`;
            outputPane.style.flex = `0 0 ${newHeight}px`;

            // Let Monaco layout trigger if automaticLayout doesn't catch it instantly
            if (window.editor) {
                window.editor.layout();
            }
        };

        // Shared drag end logic
        const endDrag = () => {
            resizer.classList.remove('dragging');
            outputPane.classList.remove('no-transition');

            // If user dragged it to minimum height, snap it to collapsed state
            if (outputPane.offsetHeight <= 46) {
                outputPane.classList.add('collapsed');
                outputPane.style.height = '';
                outputPane.style.flex = '';
            }
        };

        // Mouse Events
        resizer.addEventListener('mousedown', (e) => {
            e.preventDefault();
            startDrag();

            const startY = e.clientY;
            const startHeight = outputPane.offsetHeight;
            const totalHeight = editorPane.offsetHeight;

            const onMouseMove = (moveEvent) => {
                dragMove(moveEvent.clientY, startY, startHeight, totalHeight);
            };

            const onMouseUp = () => {
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
                endDrag();
            };

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });

        // Touch Events
        resizer.addEventListener('touchstart', (e) => {
            startDrag();

            const startY = e.touches[0].clientY;
            const startHeight = outputPane.offsetHeight;
            const totalHeight = editorPane.offsetHeight;

            const onTouchMove = (moveEvent) => {
                dragMove(moveEvent.touches[0].clientY, startY, startHeight, totalHeight);
            };

            const onTouchEnd = () => {
                document.removeEventListener('touchmove', onTouchMove);
                document.removeEventListener('touchend', onTouchEnd);
                endDrag();
            };

            document.addEventListener('touchmove', onTouchMove);
            document.addEventListener('touchend', onTouchEnd);
        });
    }
});
