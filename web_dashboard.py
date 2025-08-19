#!/usr/bin/env python3
"""Web Dashboard for PostOp PDF Collector with UI controls."""

from fastapi import FastAPI, BackgroundTasks, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import uvicorn

from agent_interface import AgentInterface
from postop_collector.storage.metadata_db import MetadataDB
from postop_collector.config.settings import Settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from postop_collector.storage.database import PDFDocument

app = FastAPI(title="PostOp PDF Collector Dashboard")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
collection_state = {
    "is_running": False,
    "current_run": None,
    "history": [],
    "progress": {}
}

# WebSocket connections for real-time updates
active_connections: List[WebSocket] = []


class CollectionManager:
    """Manages collection runs and tracks history."""
    
    def __init__(self):
        # Load environment variables
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        # Set API keys in environment for agent
        config = {
            "google_api_key": os.getenv("GOOGLE_API_KEY"),
            "google_search_engine_id": os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        }
        
        self.agent = AgentInterface(config)
        self.history_file = Path("data/collection_history.json")
        self.load_history()
    
    def load_history(self):
        """Load collection history from file."""
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                collection_state["history"] = json.load(f)
    
    def save_history(self):
        """Save collection history to file."""
        with open(self.history_file, 'w') as f:
            json.dump(collection_state["history"], f, indent=2, default=str)
    
    async def run_collection(self, search_queries: List[str], max_pdfs: int = 20):
        """Run a collection and track progress."""
        collection_state["is_running"] = True
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        run_data = {
            "run_id": run_id,
            "started_at": datetime.now().isoformat(),
            "search_queries": search_queries,
            "max_pdfs": max_pdfs,
            "status": "running",
            "pdfs_collected": 0,
            "urls_discovered": 0
        }
        
        collection_state["current_run"] = run_data
        
        # Broadcast start
        await broadcast_update({
            "type": "collection_started",
            "data": run_data
        })
        
        try:
            # Run collection
            result = await self.agent.collect_pdfs(
                search_queries=search_queries,
                max_pdfs=max_pdfs,
                quality_threshold=0.6
            )
            
            # Update run data
            run_data.update({
                "completed_at": datetime.now().isoformat(),
                "status": "completed",
                "pdfs_collected": result["pdfs_collected"],
                "urls_discovered": result["urls_discovered"],
                "success_rate": result["success_rate"],
                "average_confidence": result["average_confidence"],
                "by_procedure": result.get("by_procedure", {}),
                "by_source": result.get("by_source", {})
            })
            
        except Exception as e:
            run_data.update({
                "completed_at": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e)
            })
        
        # Add to history
        collection_state["history"].insert(0, run_data)
        collection_state["history"] = collection_state["history"][:50]  # Keep last 50 runs
        self.save_history()
        
        # Clear current run
        collection_state["is_running"] = False
        collection_state["current_run"] = None
        
        # Broadcast completion
        await broadcast_update({
            "type": "collection_completed",
            "data": run_data
        })
        
        return run_data


# Initialize manager
manager = CollectionManager()


async def broadcast_update(message: dict):
    """Broadcast update to all connected WebSocket clients."""
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except:
            active_connections.remove(connection)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard HTML."""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>PostOp PDF Collector Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2d3748;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #718096;
            font-size: 1.1em;
        }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .card h2 {
            color: #2d3748;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .stat-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        .control-panel {
            background: #f7fafc;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            color: #4a5568;
            margin-bottom: 5px;
            font-weight: 500;
        }
        input, select, textarea {
            width: 100%;
            padding: 10px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 1em;
        }
        textarea {
            resize: vertical;
            min-height: 100px;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .btn-stop {
            background: linear-gradient(135deg, #f56565 0%, #ed8936 100%);
        }
        .history-item {
            background: #f7fafc;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .history-item.running {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            color: white;
        }
        .status-badge {
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .status-completed { background: #48bb78; color: white; }
        .status-running { background: #4299e1; color: white; }
        .status-failed { background: #f56565; color: white; }
        .progress-bar {
            background: #e2e8f0;
            height: 30px;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
        }
        .progress-fill {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            height: 100%;
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
        }
        .live-log {
            background: #1a202c;
            color: #68d391;
            padding: 15px;
            border-radius: 8px;
            font-family: monospace;
            height: 200px;
            overflow-y: auto;
            margin-top: 15px;
        }
        .procedure-list {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 10px;
        }
        .procedure-tag {
            background: #edf2f7;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.9em;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .pulsing {
            animation: pulse 2s infinite;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏥 PostOp PDF Collector Dashboard</h1>
            <div class="subtitle">Automated collection and analysis of post-operative care instructions</div>
        </div>

        <div class="grid">
            <!-- Control Panel -->
            <div class="card">
                <h2>🎮 Collection Control</h2>
                <div class="control-panel">
                    <div class="form-group">
                        <label>Select Procedures to Search</label>
                        <select id="procedureCategory" onchange="updateProcedureList()">
                            <option value="">-- Select Category --</option>
                            <option value="orthopedic">Orthopedic Surgery</option>
                            <option value="cardiac">Cardiac Surgery</option>
                            <option value="general_surgery">General Surgery</option>
                            <option value="neurological">Neurosurgery</option>
                            <option value="urological">Urology</option>
                            <option value="gynecological">Gynecological Surgery</option>
                            <option value="ent">ENT Surgery</option>
                            <option value="ophthalmic">Ophthalmology</option>
                            <option value="plastic_surgery">Plastic Surgery</option>
                            <option value="dental">Oral Surgery</option>
                            <option value="vascular">Vascular Surgery</option>
                            <option value="gastrointestinal">GI Surgery</option>
                            <option value="thoracic">Thoracic Surgery</option>
                            <option value="pediatric">Pediatric Surgery</option>
                        </select>
                    </div>
                    <div class="form-group" id="procedureListGroup" style="display: none;">
                        <label>Available Procedures (click to add)</label>
                        <div id="availableProcedures" style="max-height: 150px; overflow-y: auto; border: 2px solid #e2e8f0; border-radius: 8px; padding: 10px;">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Selected Procedures</label>
                        <div id="selectedProcedures" style="min-height: 60px; border: 2px solid #667eea; border-radius: 8px; padding: 10px; background: #f7f3ff;">
                            <span style="color: #999;">No procedures selected</span>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="useCustomQueries" onchange="toggleQueryMode()">
                            Use Custom Search Queries
                        </label>
                        <textarea id="queries" placeholder="knee replacement post op care pdf
hip surgery recovery instructions pdf" style="display: none; margin-top: 10px;"></textarea>
                    </div>
                    <div class="form-group">
                        <label>Maximum PDFs</label>
                        <input type="number" id="maxPdfs" value="20" min="1" max="100">
                    </div>
                    <div class="form-group">
                        <label>Collection Mode</label>
                        <select id="mode">
                            <option value="targeted">Targeted (Specific Procedures)</option>
                            <option value="general">General Collection</option>
                            <option value="high_quality">High Quality Only (≥80%)</option>
                        </select>
                    </div>
                    <button id="startBtn" class="btn" onclick="startCollection()">
                        🚀 Start Collection
                    </button>
                    <button id="stopBtn" class="btn btn-stop" onclick="stopCollection()" style="display: none; margin-left: 10px;">
                        ⏹ Stop Collection
                    </button>
                    <button class="btn" onclick="selectCommonProcedures()" style="margin-left: 10px; background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);">
                        ⭐ Select Common Procedures
                    </button>
                </div>
                <div id="progressSection" style="display: none;">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressBar" style="width: 0%">0%</div>
                    </div>
                    <div class="live-log" id="liveLog"></div>
                </div>
            </div>

            <!-- Current Statistics -->
            <div class="card">
                <h2>📊 Collection Statistics</h2>
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="stat-value" id="totalPdfs">0</div>
                        <div class="stat-label">Total PDFs</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" id="avgConfidence">0%</div>
                        <div class="stat-label">Avg Confidence</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" id="categories">0</div>
                        <div class="stat-label">Categories</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" id="highQuality">0</div>
                        <div class="stat-label">High Quality</div>
                    </div>
                </div>
                <div style="margin-top: 20px;">
                    <h3 style="margin-bottom: 10px;">Procedures Covered</h3>
                    <div class="procedure-list" id="procedureList"></div>
                </div>
            </div>
        </div>

        <!-- Collection History -->
        <div class="card">
            <h2>📜 Collection History</h2>
            <div id="historyList"></div>
        </div>
    </div>

    <script>
        let ws = null;
        let isRunning = false;
        let selectedProcedures = [];
        
        // Procedure database
        const procedureDatabase = {
            orthopedic: [
                "Total Knee Replacement", "Total Hip Replacement", "ACL Reconstruction",
                "Rotator Cuff Repair", "Spinal Fusion", "Carpal Tunnel Release",
                "Meniscus Repair", "Shoulder Arthroscopy", "Ankle Fracture Repair"
            ],
            cardiac: [
                "Coronary Artery Bypass", "Heart Valve Replacement", "Pacemaker Implantation",
                "Angioplasty and Stenting", "Atrial Fibrillation Ablation", "Heart Transplant"
            ],
            general_surgery: [
                "Appendectomy", "Gallbladder Removal", "Hernia Repair",
                "Colonoscopy", "Hemorrhoidectomy", "Thyroidectomy", "Mastectomy"
            ],
            neurological: [
                "Craniotomy", "Brain Tumor Removal", "Spinal Cord Surgery",
                "Deep Brain Stimulation", "Epilepsy Surgery", "Lumbar Puncture"
            ],
            urological: [
                "Prostatectomy", "TURP", "Kidney Stone Removal",
                "Cystoscopy", "Vasectomy", "Bladder Surgery"
            ],
            gynecological: [
                "Hysterectomy", "C-Section", "Ovarian Cyst Removal",
                "Endometrial Ablation", "Myomectomy", "Tubal Ligation"
            ],
            ent: [
                "Tonsillectomy", "Adenoidectomy", "Septoplasty",
                "Sinus Surgery", "Tympanoplasty", "Cochlear Implant"
            ],
            ophthalmic: [
                "Cataract Surgery", "LASIK", "Glaucoma Surgery",
                "Retinal Detachment Repair", "Corneal Transplant", "Vitrectomy"
            ],
            plastic_surgery: [
                "Rhinoplasty", "Breast Augmentation", "Liposuction",
                "Tummy Tuck", "Facelift", "Blepharoplasty"
            ],
            dental: [
                "Wisdom Teeth Extraction", "Dental Implants", "Root Canal",
                "Tooth Extraction", "Jaw Surgery", "Gum Surgery"
            ],
            vascular: [
                "Carotid Endarterectomy", "Aneurysm Repair", "Varicose Vein Surgery",
                "Bypass Surgery", "Thrombectomy", "Angioplasty"
            ],
            gastrointestinal: [
                "Colonoscopy", "Endoscopy", "Liver Resection",
                "Pancreatic Surgery", "Esophageal Surgery", "Stomach Surgery"
            ],
            thoracic: [
                "Lobectomy", "Lung Biopsy", "Thoracotomy",
                "VATS Surgery", "Mediastinoscopy", "Chest Tube Insertion"
            ],
            pediatric: [
                "Appendectomy (Pediatric)", "Hernia Repair (Pediatric)", "Orchiopexy",
                "Pyloric Stenosis Repair", "Tonsillectomy (Pediatric)", "Circumcision"
            ]
        };
        
        const commonProcedures = [
            "Total Knee Replacement", "Total Hip Replacement", "Cataract Surgery",
            "Gallbladder Removal", "Hernia Repair", "Appendectomy",
            "C-Section", "Hysterectomy", "Tonsillectomy", "Coronary Artery Bypass"
        ];

        function updateProcedureList() {
            const category = document.getElementById('procedureCategory').value;
            const listGroup = document.getElementById('procedureListGroup');
            const availableDiv = document.getElementById('availableProcedures');
            
            if (category && procedureDatabase[category]) {
                listGroup.style.display = 'block';
                availableDiv.innerHTML = '';
                
                procedureDatabase[category].forEach(procedure => {
                    const btn = document.createElement('button');
                    btn.style.cssText = 'margin: 3px; padding: 5px 10px; background: #e2e8f0; border: none; border-radius: 5px; cursor: pointer;';
                    btn.textContent = procedure;
                    btn.onclick = () => addProcedure(procedure);
                    availableDiv.appendChild(btn);
                });
            } else {
                listGroup.style.display = 'none';
            }
        }
        
        function addProcedure(procedure) {
            if (!selectedProcedures.includes(procedure)) {
                selectedProcedures.push(procedure);
                updateSelectedProcedures();
            }
        }
        
        function removeProcedure(procedure) {
            selectedProcedures = selectedProcedures.filter(p => p !== procedure);
            updateSelectedProcedures();
        }
        
        function updateSelectedProcedures() {
            const selectedDiv = document.getElementById('selectedProcedures');
            if (selectedProcedures.length === 0) {
                selectedDiv.innerHTML = '<span style="color: #999;">No procedures selected</span>';
            } else {
                selectedDiv.innerHTML = '';
                selectedProcedures.forEach(procedure => {
                    const tag = document.createElement('span');
                    tag.style.cssText = 'display: inline-block; margin: 3px; padding: 5px 10px; background: #667eea; color: white; border-radius: 15px; cursor: pointer;';
                    tag.innerHTML = `${procedure} <span style="margin-left: 5px;" onclick="removeProcedure('${procedure}')">✕</span>`;
                    selectedDiv.appendChild(tag);
                });
            }
        }
        
        function selectCommonProcedures() {
            selectedProcedures = [...commonProcedures];
            updateSelectedProcedures();
        }
        
        function toggleQueryMode() {
            const useCustom = document.getElementById('useCustomQueries').checked;
            document.getElementById('queries').style.display = useCustom ? 'block' : 'none';
            document.getElementById('procedureCategory').disabled = useCustom;
            document.getElementById('procedureListGroup').style.display = useCustom ? 'none' : 
                (document.getElementById('procedureCategory').value ? 'block' : 'none');
        }
        
        function generateQueriesFromProcedures() {
            const queries = [];
            selectedProcedures.forEach(procedure => {
                queries.push(`"${procedure}" post operative care instructions pdf`);
                queries.push(`"${procedure}" recovery guidelines pdf`);
            });
            return queries;
        }

        // Initialize WebSocket connection
        function connectWebSocket() {
            ws = new WebSocket('ws://localhost:8001/ws');
            
            ws.onmessage = function(event) {
                const message = JSON.parse(event.data);
                handleWebSocketMessage(message);
            };
            
            ws.onclose = function() {
                setTimeout(connectWebSocket, 3000); // Reconnect after 3 seconds
            };
        }

        function handleWebSocketMessage(message) {
            if (message.type === 'collection_started') {
                isRunning = true;
                updateUI();
                addToLog('Collection started: ' + message.data.run_id);
            } else if (message.type === 'collection_completed') {
                isRunning = false;
                updateUI();
                loadHistory();
                loadStats();
                addToLog('Collection completed: ' + message.data.pdfs_collected + ' PDFs collected');
            } else if (message.type === 'progress_update') {
                updateProgress(message.data);
            }
        }

        function updateProgress(data) {
            const progressBar = document.getElementById('progressBar');
            const percent = Math.round((data.current / data.total) * 100);
            progressBar.style.width = percent + '%';
            progressBar.textContent = percent + '%';
        }

        function addToLog(message) {
            const log = document.getElementById('liveLog');
            const timestamp = new Date().toLocaleTimeString();
            log.innerHTML += `[${timestamp}] ${message}\n`;
            log.scrollTop = log.scrollHeight;
        }

        async function startCollection() {
            let queries = [];
            const useCustom = document.getElementById('useCustomQueries').checked;
            
            if (useCustom) {
                queries = document.getElementById('queries').value.split('\n').filter(q => q.trim());
            } else {
                if (selectedProcedures.length === 0) {
                    alert('Please select at least one procedure or use custom queries');
                    return;
                }
                queries = generateQueriesFromProcedures();
            }
            
            const maxPdfs = parseInt(document.getElementById('maxPdfs').value);
            
            if (queries.length === 0) {
                alert('Please select procedures or enter search queries');
                return;
            }
            
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').style.display = 'inline-block';
            document.getElementById('progressSection').style.display = 'block';
            
            const response = await fetch('/api/start-collection', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    search_queries: queries,
                    max_pdfs: maxPdfs
                })
            });
            
            const result = await response.json();
            addToLog('Collection task started');
        }

        async function stopCollection() {
            const response = await fetch('/api/stop-collection', {
                method: 'POST'
            });
            
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').style.display = 'none';
            addToLog('Collection stopped');
        }

        async function loadStats() {
            const response = await fetch('/api/stats');
            const stats = await response.json();
            
            document.getElementById('totalPdfs').textContent = stats.total_pdfs;
            document.getElementById('avgConfidence').textContent = Math.round(stats.average_confidence * 100) + '%';
            document.getElementById('categories').textContent = stats.categories_count;
            document.getElementById('highQuality').textContent = stats.high_quality_count;
            
            // Update procedure list
            const procedureList = document.getElementById('procedureList');
            procedureList.innerHTML = '';
            for (const [proc, count] of Object.entries(stats.procedures)) {
                const tag = document.createElement('div');
                tag.className = 'procedure-tag';
                tag.textContent = `${proc} (${count})`;
                procedureList.appendChild(tag);
            }
        }

        async function loadHistory() {
            const response = await fetch('/api/history');
            const history = await response.json();
            
            const historyList = document.getElementById('historyList');
            historyList.innerHTML = '';
            
            history.forEach(run => {
                const item = document.createElement('div');
                item.className = `history-item ${run.status}`;
                
                const info = document.createElement('div');
                info.innerHTML = `
                    <strong>Run ${run.run_id}</strong><br>
                    <small>${new Date(run.started_at).toLocaleString()}</small><br>
                    <small>${run.pdfs_collected || 0} PDFs collected | ${Math.round((run.average_confidence || 0) * 100)}% avg confidence</small>
                `;
                
                const badge = document.createElement('span');
                badge.className = `status-badge status-${run.status}`;
                badge.textContent = run.status.toUpperCase();
                
                item.appendChild(info);
                item.appendChild(badge);
                historyList.appendChild(item);
            });
        }

        function updateUI() {
            document.getElementById('startBtn').disabled = isRunning;
            document.getElementById('stopBtn').style.display = isRunning ? 'inline-block' : 'none';
            document.getElementById('progressSection').style.display = isRunning ? 'block' : 'none';
        }

        // Initialize on load
        window.onload = function() {
            connectWebSocket();
            loadStats();
            loadHistory();
            
            // Refresh stats every 10 seconds
            setInterval(loadStats, 10000);
        };
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        active_connections.remove(websocket)


@app.post("/api/start-collection")
async def start_collection(background_tasks: BackgroundTasks, request: dict):
    """Start a new collection run."""
    if collection_state["is_running"]:
        return JSONResponse({"error": "Collection already running"}, status_code=400)
    
    search_queries = request.get("search_queries", [])
    max_pdfs = request.get("max_pdfs", 20)
    
    background_tasks.add_task(
        manager.run_collection,
        search_queries,
        max_pdfs
    )
    
    return {"status": "started", "message": "Collection started in background"}


@app.post("/api/stop-collection")
async def stop_collection():
    """Stop the current collection."""
    collection_state["is_running"] = False
    return {"status": "stopped"}


@app.get("/api/stats")
async def get_stats():
    """Get current collection statistics."""
    engine = create_engine('sqlite:///./data/agent_collector.db')
    with Session(engine) as session:
        pdfs = session.query(PDFDocument).all()
    
    if not pdfs:
        return {
            "total_pdfs": 0,
            "average_confidence": 0,
            "categories_count": 0,
            "high_quality_count": 0,
            "procedures": {}
        }
    
    procedures = {}
    for pdf in pdfs:
        proc = pdf.procedure_type
        procedures[proc] = procedures.get(proc, 0) + 1
    
    return {
        "total_pdfs": len(pdfs),
        "average_confidence": sum(p.confidence_score for p in pdfs) / len(pdfs),
        "categories_count": len(set(p.procedure_type for p in pdfs)),
        "high_quality_count": sum(1 for p in pdfs if p.confidence_score >= 0.8),
        "procedures": procedures
    }


@app.get("/api/history")
async def get_history():
    """Get collection history."""
    return collection_state["history"][:20]  # Return last 20 runs


@app.get("/api/status")
async def get_status():
    """Get current collection status."""
    return {
        "is_running": collection_state["is_running"],
        "current_run": collection_state["current_run"]
    }


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 Starting PostOp PDF Collector Dashboard")
    print("="*60)
    print("\n📍 Dashboard URL: http://localhost:8001")
    print("📍 API Docs: http://localhost:8001/docs")
    print("\nPress Ctrl+C to stop the server\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)