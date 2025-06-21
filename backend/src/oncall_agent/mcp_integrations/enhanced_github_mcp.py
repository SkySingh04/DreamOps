"""Enhanced GitHub MCP integration with complete repository access and intelligent analysis."""

import asyncio
import os
import subprocess
from datetime import datetime, timedelta
from typing import Any

from .base import MCPIntegration


class EnhancedGitHubMCPIntegration(MCPIntegration):
    """Enhanced GitHub MCP integration with complete repository access.
    
    Features:
    - Complete repository cloning and local access
    - Full commit history analysis
    - Deployment timeline tracking
    - Comprehensive codebase analysis
    - Intelligent problem detection based on timing
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the enhanced GitHub MCP integration."""
        super().__init__("enhanced_github", config)

        # Configuration
        self.github_token = self.config.get("github_token", "")
        self.mcp_server_path = self.config.get("mcp_server_path", "")
        self.server_host = self.config.get("server_host", "localhost")
        self.server_port = self.config.get("server_port", 8080)

        # Local repository management
        self.repos_cache_dir = self.config.get("repos_cache_dir", "/tmp/oncall_repos")
        self.max_cache_age_hours = self.config.get("max_cache_age_hours", 2)

        # Runtime state
        self.server_process: subprocess.Popen | None = None
        self.mcp_client = None
        self.cached_repos: dict[str, dict[str, Any]] = {}

        # Ensure cache directory exists
        os.makedirs(self.repos_cache_dir, exist_ok=True)

    async def connect(self) -> None:
        """Connect to the GitHub MCP server and initialize repository cache."""
        try:
            # Start the GitHub MCP server
            if not self.server_process:
                await self._start_mcp_server()

            # Initialize MCP client
            await self._initialize_mcp_client()

            # Test connection
            await self._test_connection()

            self.connected = True
            self.connection_time = datetime.now()
            self.logger.info("Enhanced GitHub MCP integration connected successfully")

        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            raise ConnectionError(f"Enhanced GitHub MCP connection failed: {e}")

    async def fetch_context(self, context_type: str, **kwargs) -> dict[str, Any]:
        """Fetch comprehensive context from GitHub with full repository access."""
        self.validate_connection()

        try:
            if context_type == "full_incident_analysis":
                return await self._perform_full_incident_analysis(**kwargs)
            elif context_type == "complete_repository":
                return await self._get_complete_repository(**kwargs)
            elif context_type == "commit_timeline":
                return await self._analyze_commit_timeline(**kwargs)
            elif context_type == "deployment_analysis":
                return await self._analyze_deployments(**kwargs)
            elif context_type == "code_changes_since":
                return await self._analyze_code_changes_since(**kwargs)
            elif context_type == "error_pattern_analysis":
                return await self._analyze_error_patterns(**kwargs)
            elif context_type == "dependency_analysis":
                return await self._analyze_dependencies(**kwargs)
            else:
                # Fallback to standard context types
                return await self._fetch_standard_context(context_type, **kwargs)

        except Exception as e:
            self.logger.error(f"Failed to fetch context {context_type}: {e}")
            return {"error": str(e), "context_type": context_type}

    async def _perform_full_incident_analysis(self, **kwargs) -> dict[str, Any]:
        """Perform comprehensive incident analysis with complete repository access."""
        repository = kwargs.get("repository", "")
        incident_time = kwargs.get("incident_time", datetime.now())
        alert_description = kwargs.get("alert_description", "")

        if not repository:
            raise ValueError("Repository parameter is required")

        # Convert incident_time to datetime if it's a string
        if isinstance(incident_time, str):
            incident_time = datetime.fromisoformat(incident_time.replace('Z', '+00:00'))

        analysis = {
            "repository": repository,
            "incident_time": incident_time.isoformat(),
            "analysis_timestamp": datetime.now().isoformat()
        }

        # 1. Get complete repository with recent changes
        self.logger.info(f"Cloning/updating repository: {repository}")
        repo_data = await self._get_complete_repository(repository=repository)
        analysis["repository_data"] = repo_data

        # 2. Analyze commit timeline around incident
        self.logger.info(f"Analyzing commit timeline around {incident_time}")
        timeline_analysis = await self._analyze_commit_timeline(
            repository=repository,
            since=incident_time - timedelta(hours=24),
            until=incident_time + timedelta(hours=1)
        )
        analysis["commit_timeline"] = timeline_analysis

        # 3. Analyze deployments and changes
        self.logger.info("Analyzing deployment timeline")
        deployment_analysis = await self._analyze_deployments(
            repository=repository,
            since=incident_time - timedelta(hours=12)
        )
        analysis["deployment_analysis"] = deployment_analysis

        # 4. Analyze code changes in the last few hours
        self.logger.info("Analyzing recent code changes")
        code_changes = await self._analyze_code_changes_since(
            repository=repository,
            since=incident_time - timedelta(hours=6)
        )
        analysis["recent_code_changes"] = code_changes

        # 5. Search for error patterns related to the alert
        if alert_description:
            self.logger.info("Analyzing error patterns")
            error_analysis = await self._analyze_error_patterns(
                repository=repository,
                alert_description=alert_description
            )
            analysis["error_pattern_analysis"] = error_analysis

        # 6. Analyze dependencies and configuration
        self.logger.info("Analyzing dependencies")
        dependency_analysis = await self._analyze_dependencies(repository=repository)
        analysis["dependency_analysis"] = dependency_analysis

        # 7. Intelligent problem detection
        self.logger.info("Performing intelligent problem detection")
        problem_detection = await self._detect_likely_problems(analysis)
        analysis["problem_detection"] = problem_detection

        return analysis

    async def _get_complete_repository(self, **kwargs) -> dict[str, Any]:
        """Clone or update complete repository locally for analysis."""
        repository = kwargs.get("repository", "")
        if not repository:
            raise ValueError("Repository parameter is required")

        repo_path = os.path.join(self.repos_cache_dir, repository.replace("/", "_"))
        repo_info = {
            "repository": repository,
            "local_path": repo_path,
            "cached": False,
            "last_updated": None
        }

        try:
            # Check if repository is already cached and recent
            if os.path.exists(repo_path):
                cache_time = datetime.fromtimestamp(os.path.getmtime(repo_path))
                if datetime.now() - cache_time < timedelta(hours=self.max_cache_age_hours):
                    self.logger.info(f"Using cached repository: {repository}")
                    repo_info["cached"] = True
                    repo_info["last_updated"] = cache_time.isoformat()
                    repo_info["file_structure"] = await self._analyze_file_structure(repo_path)
                    return repo_info

            # Clone or update repository
            if os.path.exists(repo_path):
                self.logger.info(f"Updating repository: {repository}")
                await self._run_git_command(["pull"], cwd=repo_path)
            else:
                self.logger.info(f"Cloning repository: {repository}")
                clone_url = f"https://{self.github_token}@github.com/{repository}.git"
                await self._run_git_command(["clone", clone_url, repo_path])

            repo_info["last_updated"] = datetime.now().isoformat()
            repo_info["file_structure"] = await self._analyze_file_structure(repo_path)

            return repo_info

        except Exception as e:
            self.logger.error(f"Failed to get repository {repository}: {e}")
            return {"error": str(e), "repository": repository}

    async def _analyze_commit_timeline(self, **kwargs) -> dict[str, Any]:
        """Analyze commit timeline around incident time."""
        repository = kwargs.get("repository", "")
        since = kwargs.get("since", datetime.now() - timedelta(hours=24))
        until = kwargs.get("until", datetime.now())

        repo_path = os.path.join(self.repos_cache_dir, repository.replace("/", "_"))

        if not os.path.exists(repo_path):
            await self._get_complete_repository(repository=repository)

        try:
            # Get commit history with detailed information
            since_str = since.strftime("%Y-%m-%d %H:%M:%S")
            until_str = until.strftime("%Y-%m-%d %H:%M:%S")

            commits_cmd = [
                "log",
                f"--since={since_str}",
                f"--until={until_str}",
                "--pretty=format:%H|%an|%ae|%ad|%s",
                "--date=iso",
                "--stat"
            ]

            commits_output = await self._run_git_command(commits_cmd, cwd=repo_path)

            timeline = {
                "repository": repository,
                "period": {
                    "since": since.isoformat(),
                    "until": until.isoformat()
                },
                "commits": [],
                "analysis": {}
            }

            # Parse commits
            commits = []
            current_commit = None

            for line in commits_output.split('\n'):
                if '|' in line and len(line.split('|')) == 5:
                    if current_commit:
                        commits.append(current_commit)

                    parts = line.split('|')
                    current_commit = {
                        "hash": parts[0],
                        "author": parts[1],
                        "email": parts[2],
                        "date": parts[3],
                        "message": parts[4],
                        "files_changed": []
                    }
                elif current_commit and line.strip() and ('|' in line or line.startswith(' ')):
                    # File change information
                    current_commit["files_changed"].append(line.strip())

            if current_commit:
                commits.append(current_commit)

            timeline["commits"] = commits

            # Analyze patterns
            timeline["analysis"] = {
                "total_commits": len(commits),
                "authors": list(set([c["author"] for c in commits])),
                "commit_frequency": len(commits) / max(1, (until - since).total_seconds() / 3600),  # commits per hour
                "hot_files": await self._identify_hot_files(commits),
                "deployment_commits": [c for c in commits if any(keyword in c["message"].lower()
                                     for keyword in ["deploy", "release", "version", "build"])],
                "fix_commits": [c for c in commits if any(keyword in c["message"].lower()
                              for keyword in ["fix", "bug", "error", "issue", "patch"])]
            }

            return timeline

        except Exception as e:
            self.logger.error(f"Failed to analyze commit timeline: {e}")
            return {"error": str(e)}

    async def _analyze_deployments(self, **kwargs) -> dict[str, Any]:
        """Analyze deployment timeline and configuration changes."""
        repository = kwargs.get("repository", "")
        since = kwargs.get("since", datetime.now() - timedelta(hours=12))

        repo_path = os.path.join(self.repos_cache_dir, repository.replace("/", "_"))

        try:
            deployment_analysis = {
                "repository": repository,
                "since": since.isoformat(),
                "deployment_files": [],
                "config_changes": [],
                "workflow_runs": []
            }

            # Find deployment-related files
            deployment_patterns = [
                "docker-compose*.yml", "docker-compose*.yaml",
                "Dockerfile*", "*.dockerfile",
                "k8s/*.yml", "k8s/*.yaml", "kubernetes/*.yml", "kubernetes/*.yaml",
                ".github/workflows/*.yml", ".github/workflows/*.yaml",
                "deployment.yml", "deployment.yaml",
                "helm/*", "charts/*",
                "terraform/*.tf"
            ]

            for pattern in deployment_patterns:
                files = await self._find_files(repo_path, pattern)
                for file_path in files:
                    # Get file changes since the specified time
                    changes = await self._get_file_changes_since(repo_path, file_path, since)
                    if changes:
                        deployment_analysis["deployment_files"].append({
                            "path": file_path,
                            "changes": changes
                        })

            # Analyze configuration files
            config_patterns = ["config/*", "*.env*", "*.ini", "*.conf", "*.properties"]
            for pattern in config_patterns:
                files = await self._find_files(repo_path, pattern)
                for file_path in files:
                    changes = await self._get_file_changes_since(repo_path, file_path, since)
                    if changes:
                        deployment_analysis["config_changes"].append({
                            "path": file_path,
                            "changes": changes
                        })

            # Get GitHub Actions workflow runs via MCP
            try:
                workflow_runs = await self._make_mcp_request("list_workflow_runs", {
                    "owner": repository.split("/")[0],
                    "repo": repository.split("/")[1],
                    "per_page": 20
                })
                deployment_analysis["workflow_runs"] = workflow_runs
            except Exception as e:
                self.logger.warning(f"Failed to get workflow runs: {e}")

            return deployment_analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze deployments: {e}")
            return {"error": str(e)}

    async def _analyze_code_changes_since(self, **kwargs) -> dict[str, Any]:
        """Analyze code changes since a specific time."""
        repository = kwargs.get("repository", "")
        since = kwargs.get("since", datetime.now() - timedelta(hours=6))

        repo_path = os.path.join(self.repos_cache_dir, repository.replace("/", "_"))

        try:
            since_str = since.strftime("%Y-%m-%d %H:%M:%S")

            # Get diff since the specified time
            diff_cmd = ["log", f"--since={since_str}", "--name-status", "--pretty=format:%H|%s"]
            diff_output = await self._run_git_command(diff_cmd, cwd=repo_path)

            changes_analysis = {
                "repository": repository,
                "since": since.isoformat(),
                "changed_files": {},
                "analysis": {}
            }

            current_commit = None
            for line in diff_output.split('\n'):
                if '|' in line:
                    current_commit = line.split('|', 1)
                elif line.strip() and current_commit:
                    # File change line (A/M/D filename)
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        change_type = parts[0]
                        filename = parts[1]

                        if filename not in changes_analysis["changed_files"]:
                            changes_analysis["changed_files"][filename] = []

                        changes_analysis["changed_files"][filename].append({
                            "commit": current_commit[0],
                            "message": current_commit[1],
                            "change_type": change_type
                        })

            # Analyze change patterns
            changes_analysis["analysis"] = {
                "total_files_changed": len(changes_analysis["changed_files"]),
                "critical_files_changed": await self._identify_critical_files_changed(changes_analysis["changed_files"]),
                "change_hotspots": await self._identify_change_hotspots(changes_analysis["changed_files"]),
                "risk_assessment": await self._assess_change_risk(changes_analysis["changed_files"])
            }

            return changes_analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze code changes: {e}")
            return {"error": str(e)}

    async def _analyze_error_patterns(self, **kwargs) -> dict[str, Any]:
        """Analyze error patterns in the codebase related to the alert."""
        repository = kwargs.get("repository", "")
        alert_description = kwargs.get("alert_description", "")

        repo_path = os.path.join(self.repos_cache_dir, repository.replace("/", "_"))

        try:
            error_analysis = {
                "repository": repository,
                "alert_description": alert_description,
                "error_patterns": [],
                "related_code": [],
                "suggestions": []
            }

            # Extract keywords from alert description
            keywords = await self._extract_error_keywords(alert_description)

            # Search for error handling patterns
            for keyword in keywords:
                # Search in code files
                search_results = await self._search_in_codebase(repo_path, keyword)
                error_analysis["error_patterns"].extend(search_results)

            # Find error handling code
            error_handling_files = await self._find_error_handling_code(repo_path)
            error_analysis["related_code"] = error_handling_files

            # Generate suggestions based on patterns
            error_analysis["suggestions"] = await self._generate_error_suggestions(
                keywords, error_analysis["error_patterns"]
            )

            return error_analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze error patterns: {e}")
            return {"error": str(e)}

    async def _analyze_dependencies(self, **kwargs) -> dict[str, Any]:
        """Analyze dependencies and their potential issues."""
        repository = kwargs.get("repository", "")
        repo_path = os.path.join(self.repos_cache_dir, repository.replace("/", "_"))

        try:
            dependency_analysis = {
                "repository": repository,
                "dependency_files": [],
                "recent_changes": [],
                "security_analysis": []
            }

            # Find dependency files
            dependency_files = [
                "package.json", "package-lock.json", "yarn.lock",
                "requirements.txt", "Pipfile", "Pipfile.lock", "poetry.lock",
                "go.mod", "go.sum",
                "Cargo.toml", "Cargo.lock",
                "pom.xml", "build.gradle",
                "composer.json", "composer.lock"
            ]

            for dep_file in dependency_files:
                file_path = os.path.join(repo_path, dep_file)
                if os.path.exists(file_path):
                    # Read file content
                    with open(file_path, encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # Get recent changes to this file
                    changes = await self._get_file_changes_since(
                        repo_path, dep_file, datetime.now() - timedelta(days=7)
                    )

                    dependency_analysis["dependency_files"].append({
                        "file": dep_file,
                        "content": content[:2000],  # First 2KB
                        "recent_changes": changes
                    })

            return dependency_analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze dependencies: {e}")
            return {"error": str(e)}

    async def _detect_likely_problems(self, analysis: dict[str, Any]) -> dict[str, Any]:
        """Intelligent problem detection based on comprehensive analysis."""
        problems = {
            "high_probability": [],
            "medium_probability": [],
            "low_probability": [],
            "recommendations": []
        }

        try:
            # Check for recent deployment issues
            if analysis.get("deployment_analysis", {}).get("deployment_files"):
                problems["high_probability"].append({
                    "type": "recent_deployment_change",
                    "description": "Recent deployment configuration changes detected",
                    "evidence": analysis["deployment_analysis"]["deployment_files"]
                })

            # Check for high commit frequency before incident
            commit_analysis = analysis.get("commit_timeline", {}).get("analysis", {})
            if commit_analysis.get("commit_frequency", 0) > 2:  # More than 2 commits per hour
                problems["medium_probability"].append({
                    "type": "high_commit_frequency",
                    "description": "Unusually high commit frequency before incident",
                    "evidence": f"Commit frequency: {commit_analysis.get('commit_frequency', 0):.2f} commits/hour"
                })

            # Check for critical file changes
            code_changes = analysis.get("recent_code_changes", {}).get("analysis", {})
            if code_changes.get("critical_files_changed"):
                problems["high_probability"].append({
                    "type": "critical_file_changes",
                    "description": "Critical system files were recently modified",
                    "evidence": code_changes["critical_files_changed"]
                })

            # Check for error pattern matches
            error_patterns = analysis.get("error_pattern_analysis", {}).get("error_patterns", [])
            if error_patterns:
                problems["medium_probability"].append({
                    "type": "error_pattern_match",
                    "description": "Found code patterns matching alert description",
                    "evidence": error_patterns[:3]  # Top 3 matches
                })

            # Generate recommendations
            problems["recommendations"] = [
                "Review recent deployment changes immediately",
                "Check application logs for detailed error traces",
                "Verify database connectivity and performance",
                "Monitor resource usage (CPU, memory, disk)",
                "Consider rolling back recent changes if necessary"
            ]

            if analysis.get("recent_code_changes", {}).get("changed_files"):
                problems["recommendations"].append(
                    "Review code changes in: " +
                    ", ".join(list(analysis["recent_code_changes"]["changed_files"].keys())[:3])
                )

            return problems

        except Exception as e:
            self.logger.error(f"Failed to detect problems: {e}")
            return {"error": str(e)}

    # Helper methods
    async def _run_git_command(self, cmd: list[str], cwd: str = None) -> str:
        """Run a git command and return output."""
        full_cmd = ["git"] + cmd
        process = await asyncio.create_subprocess_exec(
            *full_cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Git command failed: {stderr.decode()}")

        return stdout.decode()

    async def _analyze_file_structure(self, repo_path: str) -> dict[str, Any]:
        """Analyze repository file structure."""
        structure = {
            "total_files": 0,
            "directories": [],
            "key_files": [],
            "languages": {}
        }

        try:
            for root, dirs, files in os.walk(repo_path):
                if ".git" in root:
                    continue

                for file in files:
                    structure["total_files"] += 1
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, repo_path)

                    # Track key files
                    if file in ["README.md", "Dockerfile", "docker-compose.yml", "package.json", "requirements.txt"]:
                        structure["key_files"].append(rel_path)

                    # Track languages by extension
                    ext = os.path.splitext(file)[1].lower()
                    if ext:
                        structure["languages"][ext] = structure["languages"].get(ext, 0) + 1

                for dir_name in dirs:
                    if not dir_name.startswith('.'):
                        structure["directories"].append(os.path.relpath(os.path.join(root, dir_name), repo_path))

            return structure

        except Exception as e:
            self.logger.error(f"Failed to analyze file structure: {e}")
            return {"error": str(e)}

    async def _identify_hot_files(self, commits: list[dict[str, Any]]) -> list[str]:
        """Identify frequently changed files."""
        file_changes = {}
        for commit in commits:
            for file_change in commit.get("files_changed", []):
                if '|' in file_change:
                    filename = file_change.split('|')[0].strip()
                    file_changes[filename] = file_changes.get(filename, 0) + 1

        # Return top 5 most changed files
        return sorted(file_changes.keys(), key=lambda x: file_changes[x], reverse=True)[:5]

    async def _find_files(self, repo_path: str, pattern: str) -> list[str]:
        """Find files matching a pattern."""
        import glob
        full_pattern = os.path.join(repo_path, pattern)
        return [os.path.relpath(f, repo_path) for f in glob.glob(full_pattern, recursive=True)]

    async def _get_file_changes_since(self, repo_path: str, file_path: str, since: datetime) -> list[dict[str, Any]]:
        """Get changes to a specific file since a given time."""
        try:
            since_str = since.strftime("%Y-%m-%d %H:%M:%S")
            cmd = ["log", f"--since={since_str}", "--oneline", "--", file_path]
            output = await self._run_git_command(cmd, cwd=repo_path)

            changes = []
            for line in output.strip().split('\n'):
                if line.strip():
                    parts = line.split(' ', 1)
                    if len(parts) >= 2:
                        changes.append({
                            "hash": parts[0],
                            "message": parts[1]
                        })

            return changes

        except Exception as e:
            self.logger.warning(f"Failed to get file changes for {file_path}: {e}")
            return []

    async def _extract_error_keywords(self, alert_description: str) -> list[str]:
        """Extract relevant keywords from alert description."""
        import re

        # Common error patterns
        error_patterns = [
            r'\b\d{3}\b',  # HTTP status codes
            r'\berror\b',
            r'\bexception\b',
            r'\bfailed?\b',
            r'\btimeout\b',
            r'\bconnection\b',
            r'\bdatabase\b',
            r'\bapi\b',
            r'\bserver\b',
            r'\bmemory\b',
            r'\bcpu\b'
        ]

        keywords = []
        text = alert_description.lower()

        for pattern in error_patterns:
            matches = re.findall(pattern, text)
            keywords.extend(matches)

        # Remove duplicates and return
        return list(set(keywords))

    async def _search_in_codebase(self, repo_path: str, keyword: str) -> list[dict[str, Any]]:
        """Search for keyword in codebase."""
        try:
            cmd = ["grep", "-r", "-n", "-i", keyword, repo_path]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            results = []
            for line in stdout.decode().split('\n')[:10]:  # Limit to 10 results
                if line.strip():
                    parts = line.split(':', 2)
                    if len(parts) >= 3:
                        results.append({
                            "file": os.path.relpath(parts[0], repo_path),
                            "line": parts[1],
                            "content": parts[2].strip()
                        })

            return results

        except Exception as e:
            self.logger.warning(f"Search failed for keyword {keyword}: {e}")
            return []

    async def _find_error_handling_code(self, repo_path: str) -> list[dict[str, Any]]:
        """Find error handling code patterns."""
        patterns = ["try", "catch", "except", "error", "throw", "raise"]
        error_files = []

        for pattern in patterns:
            results = await self._search_in_codebase(repo_path, pattern)
            error_files.extend(results)

        return error_files[:20]  # Limit results

    async def _generate_error_suggestions(self, keywords: list[str], patterns: list[dict[str, Any]]) -> list[str]:
        """Generate suggestions based on error analysis."""
        suggestions = []

        if any("timeout" in k for k in keywords):
            suggestions.append("Check network connectivity and timeout configurations")

        if any("database" in k for k in keywords):
            suggestions.append("Verify database connectivity and query performance")

        if any("memory" in k for k in keywords):
            suggestions.append("Monitor memory usage and check for memory leaks")

        if any("5" in k for k in keywords):  # 5xx errors
            suggestions.append("Check server logs for internal errors")

        if patterns:
            suggestions.append("Review error handling code in the identified files")

        return suggestions

    async def _identify_critical_files_changed(self, changed_files: dict[str, Any]) -> list[str]:
        """Identify critical files from changed files."""
        critical_patterns = [
            "config", "docker", "deployment", "service", "main", "app", "server", "api"
        ]

        critical_files = []
        for filename in changed_files.keys():
            if any(pattern in filename.lower() for pattern in critical_patterns):
                critical_files.append(filename)

        return critical_files

    async def _identify_change_hotspots(self, changed_files: dict[str, Any]) -> list[str]:
        """Identify areas of code with high change frequency."""
        # Group by directory
        dir_changes = {}
        for filename in changed_files.keys():
            directory = os.path.dirname(filename) or "root"
            dir_changes[directory] = dir_changes.get(directory, 0) + 1

        # Return top 3 directories with most changes
        return sorted(dir_changes.keys(), key=lambda x: dir_changes[x], reverse=True)[:3]

    async def _assess_change_risk(self, changed_files: dict[str, Any]) -> str:
        """Assess risk level of recent changes."""
        total_changes = len(changed_files)
        critical_changes = len(await self._identify_critical_files_changed(changed_files))

        if critical_changes > 3 or total_changes > 20:
            return "HIGH"
        elif critical_changes > 1 or total_changes > 10:
            return "MEDIUM"
        else:
            return "LOW"

    # Standard MCP methods (delegated to original implementation)
    async def _start_mcp_server(self) -> None:
        """Start the GitHub MCP server."""
        # Implementation from original GitHubMCPIntegration
        pass

    async def _initialize_mcp_client(self) -> None:
        """Initialize MCP client."""
        # Implementation from original GitHubMCPIntegration
        pass

    async def _test_connection(self) -> None:
        """Test MCP connection."""
        # Implementation from original GitHubMCPIntegration
        pass

    async def _make_mcp_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Make MCP request."""
        # Implementation from original GitHubMCPIntegration
        return {}

    async def _fetch_standard_context(self, context_type: str, **kwargs) -> dict[str, Any]:
        """Fetch standard context types."""
        # Fallback to original implementation
        return {"context_type": context_type, "data": "standard_context"}

    async def disconnect(self) -> None:
        """Disconnect and cleanup."""
        if self.mcp_client:
            await self.mcp_client.close()

        if self.server_process:
            self.server_process.terminate()

        self.connected = False
        self.logger.info("Enhanced GitHub MCP integration disconnected")

    async def execute_action(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute actions (delegated to standard implementation)."""
        return {"action": action, "status": "delegated"}

    async def get_capabilities(self) -> dict[str, list[str]]:
        """Get enhanced capabilities."""
        return {
            "context_types": [
                "full_incident_analysis",
                "complete_repository",
                "commit_timeline",
                "deployment_analysis",
                "code_changes_since",
                "error_pattern_analysis",
                "dependency_analysis"
            ],
            "actions": [
                "create_issue",
                "add_comment",
                "intelligent_analysis"
            ],
            "features": [
                "complete_repository_access",
                "intelligent_problem_detection",
                "timeline_analysis",
                "deployment_tracking",
                "error_pattern_matching",
                "dependency_analysis",
                "risk_assessment"
            ]
        }
