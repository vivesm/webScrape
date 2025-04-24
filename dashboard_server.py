#!/usr/bin/env python3
"""
WebScrape Dashboard Server

This module provides a web dashboard for monitoring and controlling WebScrape operations.
It uses Flask to create a simple web server that provides both the dashboard UI
and an API for controlling scraping operations.

Usage:
    python dashboard_server.py [--port PORT] [--host HOST]
"""

import os
import sys
import json
import time
import argparse
import logging
import asyncio
import threading
import subprocess
import queue
import psutil
import signal
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory
from functools import wraps
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("dashboard.log")
    ]
)

# Create Flask app
app = Flask(__name__)

# Database for tracking downloaded links
class LinkDatabase:
    def __init__(self, db_file="downloads.db"):
        self.db_file = db_file
        self._init_db()
    
    def _init_db(self):
        """Initialize the database if it doesn't exist."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Create table for downloaded URLs
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                domain TEXT,
                path TEXT,
                hash TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                file_path TEXT,
                size INTEGER DEFAULT 0
            )
            ''')
            
            # Create index for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_domain ON downloads(domain)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON downloads(url)')
            
            conn.commit()
            conn.close()
            logging.info(f"Database initialized: {self.db_file}")
        except Exception as e:
            logging.error(f"Error initializing database: {e}")
    
    def add_url(self, url, file_path="", size=0):
        """Add a URL to the database of downloaded links."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            path = parsed.path
            url_hash = hashlib.md5(url.encode()).hexdigest()
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT OR REPLACE INTO downloads (url, domain, path, hash, timestamp, file_path, size) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (url, domain, path, url_hash, datetime.now().isoformat(), file_path, size)
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Error adding URL to database: {e}")
            return False
    
    def get_all_urls(self):
        """Get all downloaded URLs, grouped by domain."""
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT domain, COUNT(*) as count FROM downloads GROUP BY domain ORDER BY count DESC")
            domains = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute("SELECT * FROM downloads ORDER BY timestamp DESC")
            all_urls = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            # Group by domain
            grouped = {}
            for domain in domains:
                domain_name = domain['domain']
                grouped[domain_name] = {
                    'count': domain['count'],
                    'urls': [url for url in all_urls if url['domain'] == domain_name]
                }
            
            return grouped
        except Exception as e:
            logging.error(f"Error getting URLs from database: {e}")
            return {}
    
    def is_url_downloaded(self, url):
        """Check if a URL has already been downloaded."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM downloads WHERE url = ?", (url,))
            result = cursor.fetchone()
            
            conn.close()
            return result is not None
        except Exception as e:
            logging.error(f"Error checking URL in database: {e}")
            return False
    
    def delete_url(self, url):
        """Delete a URL from the database."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM downloads WHERE url = ?", (url,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Error deleting URL from database: {e}")
            return False
    
    def delete_domain(self, domain):
        """Delete all URLs for a domain from the database."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM downloads WHERE domain = ?", (domain,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Error deleting domain from database: {e}")
            return False
    
    def flush_database(self):
        """Delete all URLs from the database."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM downloads")
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Error flushing database: {e}")
            return False

# Global data store
class JobState:
    def __init__(self):
        self.current_job = None
        self.jobs = []
        self.logs = []
        self.events = queue.Queue()  # For server-sent events
        self.process = None
        self.start_time = None
        self.metrics = {
            "urls_processed": 0,
            "files_saved": 0,
            "progress": 0,
            "cpu": 0,  # Current CPU usage
            "memory": 0,  # Current memory usage
            "active_browsers": 0
        }
        self.processed_files = []  # Track all processed files across sessions
        self._load_processed_files()  # Load from disk if available
    
    def _load_processed_files(self):
        """Load processed files from disk."""
        try:
            processed_files_path = "processed_files.json"
            if os.path.exists(processed_files_path):
                with open(processed_files_path, 'r') as f:
                    self.processed_files = json.load(f)
                logging.info(f"Loaded {len(self.processed_files)} processed files from disk")
        except Exception as e:
            logging.error(f"Error loading processed files: {e}")
            self.processed_files = []
    
    def _save_processed_files(self):
        """Save processed files to disk."""
        try:
            processed_files_path = "processed_files.json"
            with open(processed_files_path, 'w') as f:
                json.dump(self.processed_files, f)
            logging.info(f"Saved {len(self.processed_files)} processed files to disk")
        except Exception as e:
            logging.error(f"Error saving processed files: {e}")
    
    def add_processed_file(self, file_info):
        """Add a processed file to the history and save to disk."""
        self.processed_files.append(file_info)
        # Keep only the most recent 100 files
        if len(self.processed_files) > 100:
            self.processed_files = self.processed_files[-100:]
        self._save_processed_files()

job_state = JobState()
link_db = LinkDatabase()

# Decorator to handle async functions
def async_action(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(f(*args, **kwargs))
        loop.close()
        return result
    return decorated

# Dashboard UI route
@app.route('/')
def index():
    return render_template('index.html')

# Serve static files
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

# API routes
@app.route('/api/status')
def status():
    """Get current scraper status and metrics."""
    # Calculate elapsed time
    elapsed_time = "00:00:00"
    time_remaining = "--:--:--"
    if job_state.start_time:
        elapsed = time.time() - job_state.start_time
        elapsed_time = str(timedelta(seconds=int(elapsed)))
        
        # Estimate time remaining if we have progress info
        if job_state.metrics["progress"] > 0:
            remaining = (elapsed / job_state.metrics["progress"]) * (100 - job_state.metrics["progress"])
            time_remaining = str(timedelta(seconds=int(remaining)))
    
    # Get system resource usage
    cpu_percent = 0
    memory_info = {"used": 0, "total": 0}
    
    if job_state.process:
        try:
            process = psutil.Process(job_state.process.pid)
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_info_raw = process.memory_info()
            memory_info["used"] = memory_info_raw.rss / (1024 * 1024)  # Convert to MB
        except:
            pass
    
    return jsonify({
        "status": "active" if job_state.current_job else "idle",
        "current_job": job_state.current_job,
        "metrics": job_state.metrics,
        "elapsed_time": elapsed_time,
        "time_remaining": time_remaining,
        "system": {
            "cpu": cpu_percent,
            "memory": memory_info
        }
    })

@app.route('/api/logs')
def logs():
    """Get recent logs."""
    # Convert any non-serializable types to strings
    safe_logs = []
    for log in job_state.logs[-100:]:  # Return last 100 logs
        if isinstance(log, dict):
            safe_log = {k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v 
                      for k, v in log.items()}
            safe_logs.append(safe_log)
        else:
            safe_logs.append(str(log))
            
    return jsonify(safe_logs)

@app.route('/api/jobs')
def jobs():
    """Get list of recent jobs."""
    return jsonify(job_state.jobs[-10:])  # Return last 10 jobs

@app.route('/api/processed_files')
def processed_files():
    """Get list of processed files."""
    return jsonify(job_state.processed_files)

@app.route('/api/output_files')
def get_output_files():
    """Get all files in the output directory."""
    output_dir = os.path.join(os.getcwd(), "output")
    files = []
    
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            file_path = os.path.join(output_dir, filename)
            if os.path.isfile(file_path):
                # Get file type
                file_type = "unknown"
                if filename.endswith(".pdf"):
                    file_type = "pdf"
                elif filename.endswith(".text") or filename.endswith(".txt"):
                    file_type = "text"
                
                # Get other file information
                stat_info = os.stat(file_path)
                size = stat_info.st_size
                last_modified = datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                
                files.append({
                    "filename": filename,
                    "file_path": file_path,
                    "file_type": file_type,
                    "size": size,
                    "size_formatted": f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB",
                    "last_modified": last_modified
                })
    
    # Sort by last modified time, newest first
    files.sort(key=lambda x: x["last_modified"], reverse=True)
    return jsonify(files)

@app.route('/api/start', methods=['POST'])
@async_action
async def start_job():
    """Start a new scraping job."""
    if job_state.current_job:
        return jsonify({"error": "A job is already running"}), 400
    
    # Get parameters from request
    data = request.json
    base_url = data.get('base_url')
    if not base_url:
        return jsonify({"error": "base_url is required"}), 400
        
    # Check if URL has already been downloaded before
    # If it has, we'll allow it in test mode, but not in regular mode
    is_already_downloaded = link_db.is_url_downloaded(base_url)
    test_mode = data.get('test') == 'on' or data.get('test') == True
    
    if is_already_downloaded and not test_mode:
        add_log(f"URL {base_url} has already been downloaded before. Cannot proceed. Please delete the URL from history first or use test mode.", "ERROR")
        return jsonify({"error": "URL has already been downloaded. Please delete the URL from history first or use test mode."}), 400
    elif is_already_downloaded and test_mode:
        add_log(f"URL {base_url} has already been downloaded before, but allowing in test mode.", "WARNING")
    
    # Prepare command
    output_format = data.get('output_format', 'pdf')
    max_depth = int(data.get('max_depth', 1))
    concurrency = int(data.get('concurrency', 2))
    same_domain_only = data.get('same_domain_only', 'true') == 'true'
    enable_rag = data.get('enable_rag') == 'on'
    enable_streaming = data.get('enable_streaming') == 'on'
    test_mode = data.get('test') == True
    
    try:
        stream_buffer = int(data.get('stream_buffer', 1024))  # Default to 1MB
    except (ValueError, TypeError):
        stream_buffer = 1024  # Default if conversion fails
        
    try:
        test_count = int(data.get('test_count', 2))  # Default to 2 pages for test mode
    except (ValueError, TypeError):
        test_count = 2  # Default if conversion fails
    
    cmd = [
        sys.executable,
        'main.py',
        '--base_url', base_url,
        '--output_format', output_format,
        '--max_depth', str(max_depth),
        '--concurrency', str(concurrency)
    ]
    
    if same_domain_only:
        cmd.append('--same_domain_only')
    
    if enable_rag:
        cmd.append('--rag')
        
    if enable_streaming:
        cmd.append('--streaming')
        if stream_buffer:
            cmd.extend(['--stream_buffer', str(stream_buffer)])
            
    if test_mode:
        cmd.append('--test')
        cmd.extend(['--test_count', str(test_count)])
        
    # Add language filter if specified
    language = data.get('language')
    if language:
        cmd.extend(['--language', language])
    
    # Create job record
    job_id = f"job_{int(time.time())}"
    job = {
        "id": job_id,
        "url": base_url,
        "start_time": datetime.now().isoformat(),
        "status": "running",
        "files": 0,
        "current_files": [],
        "parameters": {
            "output_format": output_format,
            "max_depth": max_depth,
            "concurrency": concurrency,
            "same_domain_only": same_domain_only,
            "enable_rag": enable_rag,
            "streaming": enable_streaming,
            "stream_buffer": stream_buffer if enable_streaming else None,
            "test_mode": test_mode,
            "test_count": test_count if test_mode else None,
            "language": language if language else None
        }
    }
    
    # Also save the base_url to localStorage through an event
    # This will be picked up by the client to remember the last URL
    job_state.events.put({"type": "save_url", "url": base_url})
    
    job_state.current_job = job
    job_state.jobs.append(job)
    job_state.start_time = time.time()
    job_state.metrics = {
        "urls_processed": 0,
        "files_saved": 0,
        "progress": 0,
        "cpu": 0,
        "memory": 0,
        "active_browsers": 0,
        "current_files": []  # Track files being processed currently
    }
    
    # Start the process
    try:
        # Create process and capture output
        job_state.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Start log monitoring thread
        threading.Thread(target=monitor_output, args=(job_state.process, job_id), daemon=True).start()
        
        # Start metrics monitoring thread
        threading.Thread(target=monitor_metrics, args=(job_state.process, job_id), daemon=True).start()
        
        return jsonify({"status": "started", "job_id": job_id})
    
    except Exception as e:
        job_state.current_job["status"] = "error"
        job_state.current_job = None
        return jsonify({"error": str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_job():
    """Stop the current scraping job."""
    if not job_state.current_job:
        return jsonify({"error": "No job is currently running"}), 400
    
    if job_state.process:
        try:
            job_state.process.terminate()
            job_state.process = None
        except:
            pass
    
    job_state.current_job["status"] = "stopped"
    job_state.current_job["end_time"] = datetime.now().isoformat()
    job_state.current_job = None
    
    # Clear current files
    job_state.metrics["current_files"] = []
    job_state.events.put({"type": "file_progress", "data": []})
    
    return jsonify({"status": "stopped"})

@app.route('/api/force_stop', methods=['POST'])
def force_stop_job():
    """Force stop the current job and all Chrome processes."""
    if job_state.process:
        try:
            # First try normal termination
            job_state.process.terminate()
        except:
            pass
        
        try:
            # Then force kill the process
            job_state.process.kill()
        except:
            pass
        
        # Also kill any Chrome processes (often used by Pyppeteer)
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.call(["pkill", "-f", "chrome"])
            elif sys.platform == "win32":  # Windows
                subprocess.call(["taskkill", "/f", "/im", "chrome.exe"])
            else:  # Linux
                subprocess.call(["pkill", "-f", "chrome"])
        except Exception as e:
            logging.error(f"Error killing Chrome processes: {e}")
    
    if job_state.current_job:
        job_state.current_job["status"] = "force_stopped"
        job_state.current_job["end_time"] = datetime.now().isoformat()
        job_state.current_job = None
    
    # Clear current files
    job_state.metrics["current_files"] = []
    job_state.events.put({"type": "file_progress", "data": []})
    
    job_state.process = None
    
    add_log("Job was force stopped - all browser processes terminated", "WARNING")
    return jsonify({"status": "force_stopped"})

@app.route('/api/events')
def events():
    """Server-sent events endpoint for real-time updates."""
    def generate():
        while True:
            # Wait for a new event with a timeout
            try:
                event = job_state.events.get(timeout=1)
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                # Send a ping event if nothing happened
                yield "data: {\"type\": \"ping\"}\n\n"
            
    return app.response_class(generate(), mimetype='text/event-stream')

# Download tracking API endpoints
@app.route('/api/downloads')
def get_downloads():
    """Get all downloaded URLs grouped by domain."""
    return jsonify(link_db.get_all_urls())

@app.route('/api/downloads/check', methods=['POST'])
def check_download():
    """Check if a URL has already been downloaded."""
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    result = link_db.is_url_downloaded(url)
    return jsonify({"downloaded": result})

@app.route('/api/downloads/add', methods=['POST'])
def add_download():
    """Add a URL to the downloaded database."""
    data = request.json
    url = data.get('url')
    file_path = data.get('file_path', '')
    size = data.get('size', 0)
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    success = link_db.add_url(url, file_path, size)
    return jsonify({"success": success})

@app.route('/api/downloads/delete', methods=['POST'])
def delete_download():
    """Delete a URL from the downloaded database."""
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    success = link_db.delete_url(url)
    return jsonify({"success": success})

@app.route('/api/downloads/delete_domain', methods=['POST'])
def delete_domain():
    """Delete all URLs for a domain from the downloaded database."""
    data = request.json
    domain = data.get('domain')
    
    if not domain:
        return jsonify({"error": "Domain is required"}), 400
    
    success = link_db.delete_domain(domain)
    return jsonify({"success": success})

@app.route('/api/downloads/flush', methods=['POST'])
def flush_downloads():
    """Delete all URLs from the downloaded database."""
    success = link_db.flush_database()
    return jsonify({"success": success})

@app.route('/api/quit', methods=['POST'])
def quit_application():
    """Quit the application."""
    # Stop the current job if it's running
    if job_state.process:
        try:
            job_state.process.terminate()
        except:
            pass
    
    # Schedule a delayed shutdown to allow this request to complete
    def shutdown_server():
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGTERM)
    
    threading.Thread(target=shutdown_server, daemon=True).start()
    return jsonify({"success": True, "message": "Application shutting down..."})

@app.route('/api/open_output', methods=['POST'])
def open_output_directory():
    """Open the output directory in the system file explorer."""
    output_dir = os.path.join(os.getcwd(), "output")
    
    # Create the directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Open the directory using the appropriate command for the platform
    try:
        if sys.platform == "darwin":  # macOS
            subprocess.call(["open", output_dir])
        elif sys.platform == "win32":  # Windows
            os.startfile(output_dir)
        else:  # Linux or other Unix-like
            subprocess.call(["xdg-open", output_dir])
        
        return jsonify({"success": True, "message": f"Opened output directory: {output_dir}"})
    except Exception as e:
        logging.error(f"Error opening output directory: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def add_log(message, level="INFO", job_id=None):
    """Add a log entry."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "level": level,
        "job_id": job_id
    }
    job_state.logs.append(log_entry)
    job_state.events.put({"type": "log", "data": log_entry})
    logging.info(f"[{level}] {message}")

def monitor_output(process, job_id):
    """Monitor the output of the scraping process."""
    for line in iter(process.stdout.readline, ''):
        line = line.strip()
        if line:
            add_log(line, "INFO", job_id)
            
            # Check if the line contains a URL and file path (like when saving)
            if "Processing" in line and "->" in line:
                # Format: Processing https://example.com -> /path/to/output.pdf
                parts = line.split("Processing ", 1)
                if len(parts) > 1:
                    url_parts = parts[1].split(" -> ", 1)
                    if len(url_parts) > 1:
                        url = url_parts[0].strip()
                        file_path = url_parts[1].strip()
                        
                        # Check if this URL has already been downloaded
                        is_already_downloaded = link_db.is_url_downloaded(url)
                        test_mode = job_state.current_job and job_state.current_job["parameters"].get("test_mode", False)
                        
                        if is_already_downloaded and not test_mode:
                            add_log(f"URL {url} has already been downloaded previously. Skipping.", "WARNING", job_id)
                            continue
                        elif is_already_downloaded and test_mode:
                            add_log(f"URL {url} has already been downloaded, but processing anyway in test mode.", "INFO", job_id)
                        
                        # Track that we're processing this URL
                        job_state.metrics["urls_processed"] += 1
                        job_state.events.put({"type": "metric", "name": "urls_processed", "value": job_state.metrics["urls_processed"]})
                        
                        # Add to current files being processed
                        file_info = {
                            "url": url,
                            "file_path": file_path,
                            "status": "processing",
                            "timestamp": datetime.now().isoformat()
                        }
                        job_state.metrics["current_files"].append(file_info)
                        # Limit the number of tracked files to avoid excessive memory usage
                        if len(job_state.metrics["current_files"]) > 10:
                            job_state.metrics["current_files"] = job_state.metrics["current_files"][-10:]
                        job_state.events.put({"type": "file_progress", "data": job_state.metrics["current_files"]})
            
            # Check if file was saved
            if "Saved" in line and ("PDF" in line or "text" in line):
                # Format: Saved text: /path/to/output.text
                parts = line.split("Saved ", 1)
                if len(parts) > 1:
                    file_parts = parts[1].split(": ", 1)
                    if len(file_parts) > 1:
                        file_type = file_parts[0].strip()
                        file_path = file_parts[1].strip()
                        
                        # Clean up file path if it contains bytes information
                        if "(" in file_path:
                            file_path = file_path.split("(")[0].strip()
                        
                        # Extract the URL from previous log if available
                        url = ""
                        # Look through recent logs to find the URL for this file
                        for log_entry in reversed(job_state.logs[-20:]):
                            if isinstance(log_entry, dict) and "message" in log_entry:
                                log_msg = log_entry["message"]
                                if "Processing" in log_msg and "->" in log_msg:
                                    url_parts = log_msg.split("Processing ", 1)[1].split(" -> ", 1)
                                    if len(url_parts) > 1:
                                        log_file_path = url_parts[1].strip()
                                        # Check if this is the correct file (path might vary slightly)
                                        if os.path.basename(file_path) in os.path.basename(log_file_path):
                                            url = url_parts[0].strip()
                                            break
                        
                        # Record file save
                        job_state.metrics["files_saved"] += 1
                        job_state.events.put({"type": "metric", "name": "files_saved", "value": job_state.metrics["files_saved"]})
                        
                        # Add to downloaded URLs database
                        if url:
                            size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                            link_db.add_url(url, file_path, size)
                            
                            # Update file status to completed
                            for file_info in job_state.metrics["current_files"]:
                                if file_info["url"] == url and file_info["status"] == "processing":
                                    file_info["status"] = "completed"
                                    file_info["size"] = size
                                    # Add some additional info
                                    file_info["completion_time"] = datetime.now().isoformat()
                                    file_info["filename"] = os.path.basename(file_path)
                                    
                                    # Add to persistent processed files history
                                    job_state.add_processed_file(file_info)
                                    
                                    # Update UI
                                    job_state.events.put({"type": "file_progress", "data": job_state.metrics["current_files"]})
                                    job_state.events.put({"type": "processed_files", "data": job_state.processed_files})
            
            if "WebScrape Complete" in line or "Scraping completed" in line or "RAG processing completed" in line:
                # Job completed normally
                if job_state.current_job:
                    add_log("Job completed successfully", "INFO")
                    job_state.current_job["status"] = "completed"
                    job_state.current_job["end_time"] = datetime.now().isoformat()
                    job_state.current_job = None
                    
                    # Clear current files
                    job_state.metrics["current_files"] = []
                    job_state.events.put({"type": "file_progress", "data": []})
                    job_state.events.put({"type": "job_completed", "data": {"status": "completed"}})
    
    # Process finished
    if process.poll() is not None:
        # Check if job was terminated or completed with error
        if job_state.current_job:
            if process.returncode != 0:
                job_state.current_job["status"] = "error"
                add_log(f"Job ended with error (code {process.returncode})", "ERROR")
            else:
                job_state.current_job["status"] = "completed"
                add_log("Job process complete", "INFO")
            
            job_state.current_job["end_time"] = datetime.now().isoformat()
            job_state.current_job = None
            
            # Clear current files
            job_state.metrics["current_files"] = []
            job_state.events.put({"type": "file_progress", "data": []})
            job_state.events.put({"type": "job_completed", "data": {"status": "completed"}})

def monitor_metrics(process, job_id):
    """Monitor system metrics."""
    while process.poll() is None:
        try:
            # Get process info
            ps_process = psutil.Process(process.pid)
            
            # Get CPU and memory usage
            cpu_percent = ps_process.cpu_percent(interval=0.1)
            memory_usage = ps_process.memory_info().rss / (1024 * 1024)  # MB
            
            job_state.metrics["cpu"] = cpu_percent
            job_state.metrics["memory"] = memory_usage
            
            # Estimate progress
            if job_state.current_job:
                parameters = job_state.current_job["parameters"]
                if "max_depth" in parameters and parameters["max_depth"] > 0:
                    # Very rough progress estimate
                    elapsed = time.time() - job_state.start_time
                    if elapsed > 10:  # After 10 seconds, start estimating
                        # Assuming scraping has a typical pattern with diminishing returns
                        progress = min(90, (elapsed / (elapsed + 60)) * 100)
                        job_state.metrics["progress"] = progress
            
            # Update active browsers - this is a placeholder, actually counting would require
            # examining running processes more carefully
            job_state.metrics["active_browsers"] = min(
                job_state.current_job["parameters"]["concurrency"] if job_state.current_job else 0,
                max(1, job_state.metrics["urls_processed"] // 10)
            )
            
            # Sleep before next update
            time.sleep(2)
            
        except Exception as e:
            add_log(f"Error monitoring metrics: {e}", "ERROR", job_id)
            time.sleep(5)

def parse_args():
    parser = argparse.ArgumentParser(description="WebScrape Dashboard Server")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    # Ensure directories exist
    os.makedirs("static", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    
    # Start server
    add_log(f"Starting dashboard server on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=True, threaded=True)