#!/usr/bin/env python3
"""
kubectl Usage Audit Script

This script searches the entire DreamOps codebase for any usage of kubectl commands
and provides a comprehensive report for migration to MCP server.
"""

import ast
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.oncall_agent.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class KubectlUsage:
    """Represents a kubectl usage instance"""
    file_path: str
    line_number: int
    line_content: str
    usage_type: str  # 'direct', 'subprocess', 'os.system', 'shell_script', 'config_ref'
    kubectl_command: str | None = None
    context: str | None = None

    def to_dict(self) -> dict[str, any]:
        return asdict(self)


@dataclass
class KubectlUsageReport:
    """Comprehensive kubectl usage report"""
    total_usages: int
    by_type: dict[str, int]
    by_file: dict[str, list[KubectlUsage]]
    unique_commands: set[str]
    files_affected: list[str]
    priority_files: list[str]  # Files with most usages

    def to_dict(self) -> dict[str, any]:
        return {
            "total_usages": self.total_usages,
            "by_type": self.by_type,
            "by_file": {k: [u.to_dict() for u in v] for k, v in self.by_file.items()},
            "unique_commands": list(self.unique_commands),
            "files_affected": self.files_affected,
            "priority_files": self.priority_files
        }


class KubectlUsageAuditor:
    """Auditor for finding all kubectl usage in the codebase"""

    def __init__(self, root_dir: str = None):
        self.root_dir = root_dir or Path(__file__).parent.parent.parent
        self.logger = get_logger(self.__class__.__name__)
        self.usages: list[KubectlUsage] = []

        # Patterns to search for
        self.patterns = {
            # Direct kubectl string references
            'direct_string': [
                re.compile(r'["\']kubectl\s+[^"\']+["\']'),
                re.compile(r'`kubectl\s+[^`]+`'),
            ],
            # Subprocess calls
            'subprocess': [
                re.compile(r'subprocess\.(run|call|check_output|Popen)\s*\([^)]*kubectl'),
                re.compile(r'asyncio\.create_subprocess_(exec|shell)\s*\([^)]*kubectl'),
            ],
            # os.system calls
            'os_system': [
                re.compile(r'os\.system\s*\([^)]*kubectl'),
            ],
            # Shell script executions
            'shell_script': [
                re.compile(r'\.sh["\'].*kubectl'),
                re.compile(r'bash.*kubectl'),
            ],
            # Configuration references
            'config': [
                re.compile(r'KUBECTL_[A-Z_]+'),
                re.compile(r'kubectl_path'),
                re.compile(r'kubectl_binary'),
            ]
        }

        # File extensions to search
        self.search_extensions = {'.py', '.sh', '.yaml', '.yml', '.json', '.md', '.txt', '.env'}

        # Directories to skip
        self.skip_dirs = {
            '.git', '__pycache__', '.pytest_cache', 'node_modules',
            '.venv', 'venv', 'env', '.env', 'dist', 'build',
            '.next', 'coverage', '.mypy_cache'
        }

    async def find_all_kubectl_usage(self) -> KubectlUsageReport:
        """
        Search entire codebase for:
        1. Direct 'kubectl' command strings
        2. subprocess calls to kubectl
        3. os.system calls with kubectl
        4. Any shell script executions with kubectl
        5. Configuration references to kubectl paths
        """
        self.logger.info(f"Starting kubectl usage audit in {self.root_dir}")

        # Walk through all files
        for root, dirs, files in os.walk(self.root_dir):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in self.skip_dirs]

            for file in files:
                # Check file extension
                if not any(file.endswith(ext) for ext in self.search_extensions):
                    continue

                file_path = os.path.join(root, file)

                # Skip the audit script itself
                if file_path == __file__:
                    continue

                try:
                    self._analyze_file(file_path)
                except Exception as e:
                    self.logger.warning(f"Error analyzing {file_path}: {e}")

        # Generate report
        report = self._generate_report()

        self.logger.info(f"Audit complete. Found {report.total_usages} kubectl usages in {len(report.files_affected)} files")

        return report

    def _analyze_file(self, file_path: str):
        """Analyze a single file for kubectl usage"""
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
        except Exception as e:
            self.logger.debug(f"Could not read {file_path}: {e}")
            return

        # Check Python files with AST for more accurate detection
        if file_path.endswith('.py'):
            self._analyze_python_file(file_path, content, lines)

        # Check all files with regex patterns
        for line_num, line in enumerate(lines, 1):
            for pattern_type, patterns in self.patterns.items():
                for pattern in patterns:
                    if pattern.search(line):
                        # Extract the kubectl command if possible
                        kubectl_cmd = self._extract_kubectl_command(line)

                        usage = KubectlUsage(
                            file_path=file_path,
                            line_number=line_num,
                            line_content=line.strip(),
                            usage_type=pattern_type,
                            kubectl_command=kubectl_cmd
                        )
                        self.usages.append(usage)
                        break  # Avoid duplicate detection on same line

    def _analyze_python_file(self, file_path: str, content: str, lines: list[str]):
        """Use AST to analyze Python files for more accurate detection"""
        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                # Check for subprocess calls
                if isinstance(node, ast.Call):
                    if hasattr(node.func, 'attr') and hasattr(node.func.value, 'id'):
                        if (node.func.value.id == 'subprocess' and
                            node.func.attr in ['run', 'call', 'check_output', 'Popen']):
                            # Check if kubectl is in the arguments
                            for arg in node.args:
                                if isinstance(arg, ast.List):
                                    for elt in arg.elts:
                                        if isinstance(elt, ast.Str) and 'kubectl' in elt.s:
                                            line_num = node.lineno
                                            usage = KubectlUsage(
                                                file_path=file_path,
                                                line_number=line_num,
                                                line_content=lines[line_num - 1].strip() if line_num <= len(lines) else "",
                                                usage_type='subprocess_ast',
                                                kubectl_command=self._extract_kubectl_from_ast_list(arg)
                                            )
                                            self.usages.append(usage)
                                            break
        except Exception as e:
            # Fall back to regex-based detection
            self.logger.debug(f"AST parsing failed for {file_path}: {e}")

    def _extract_kubectl_command(self, line: str) -> str | None:
        """Extract the kubectl command from a line of code"""
        # Try to extract the command between quotes
        patterns = [
            re.compile(r'["\']([^"\']*kubectl[^"\']*)["\']'),
            re.compile(r'`([^`]*kubectl[^`]*)`'),
        ]

        for pattern in patterns:
            match = pattern.search(line)
            if match:
                return match.group(1).strip()

        # If no quotes, try to extract from subprocess patterns
        if 'kubectl' in line:
            # Simple extraction after 'kubectl'
            kubectl_idx = line.find('kubectl')
            if kubectl_idx != -1:
                # Extract until end of line or closing bracket/quote
                end_idx = len(line)
                for char in ['"', "'", ')', ']', '}', '\n']:
                    idx = line.find(char, kubectl_idx)
                    if idx != -1 and idx < end_idx:
                        end_idx = idx
                return line[kubectl_idx:end_idx].strip()

        return None

    def _extract_kubectl_from_ast_list(self, list_node: ast.List) -> str:
        """Extract kubectl command from AST list node"""
        cmd_parts = []
        for elt in list_node.elts:
            if isinstance(elt, ast.Str):
                cmd_parts.append(elt.s)
            elif isinstance(elt, ast.Constant):
                cmd_parts.append(str(elt.value))
        return ' '.join(cmd_parts)

    def _generate_report(self) -> KubectlUsageReport:
        """Generate comprehensive report from found usages"""
        by_type = {}
        by_file = {}
        unique_commands = set()

        for usage in self.usages:
            # Count by type
            by_type[usage.usage_type] = by_type.get(usage.usage_type, 0) + 1

            # Group by file
            if usage.file_path not in by_file:
                by_file[usage.file_path] = []
            by_file[usage.file_path].append(usage)

            # Collect unique commands
            if usage.kubectl_command:
                # Normalize the command (remove extra spaces, etc.)
                normalized_cmd = ' '.join(usage.kubectl_command.split())
                unique_commands.add(normalized_cmd)

        # Sort files by number of usages
        files_by_usage = sorted(by_file.items(), key=lambda x: len(x[1]), reverse=True)
        priority_files = [f[0] for f in files_by_usage[:10]]  # Top 10 files

        return KubectlUsageReport(
            total_usages=len(self.usages),
            by_type=by_type,
            by_file=by_file,
            unique_commands=unique_commands,
            files_affected=list(by_file.keys()),
            priority_files=priority_files
        )

    def generate_migration_plan(self, report: KubectlUsageReport) -> dict[str, any]:
        """Generate a migration plan from kubectl to MCP"""
        migration_plan = {
            "summary": {
                "total_files_to_update": len(report.files_affected),
                "total_changes_required": report.total_usages,
                "estimated_effort_hours": len(report.files_affected) * 0.5  # Rough estimate
            },
            "priority_order": [],
            "command_mappings": {},
            "risks": []
        }

        # Analyze unique commands and create mappings
        for cmd in report.unique_commands:
            mcp_equivalent = self._suggest_mcp_equivalent(cmd)
            migration_plan["command_mappings"][cmd] = mcp_equivalent

        # Create priority order based on file importance
        for file_path in report.priority_files:
            usages = report.by_file[file_path]
            migration_plan["priority_order"].append({
                "file": file_path,
                "usage_count": len(usages),
                "complexity": self._assess_migration_complexity(usages)
            })

        # Identify risks
        if any('delete' in cmd or 'rm' in cmd for cmd in report.unique_commands):
            migration_plan["risks"].append("Destructive operations detected - ensure MCP server handles these safely")

        if report.by_type.get('shell_script', 0) > 0:
            migration_plan["risks"].append("Shell scripts with kubectl usage may require significant refactoring")

        return migration_plan

    def _suggest_mcp_equivalent(self, kubectl_cmd: str) -> dict[str, str]:
        """Suggest MCP server equivalent for kubectl command"""
        # Parse the kubectl command
        parts = kubectl_cmd.split()

        if 'get' in parts:
            if 'pods' in parts or 'pod' in parts:
                return {
                    "mcp_tool": "kubernetes_get_pods",
                    "parameters": {"namespace": "extracted_from_context"}
                }
            elif 'deployments' in parts or 'deployment' in parts:
                return {
                    "mcp_tool": "kubernetes_list_deployments",
                    "parameters": {"namespace": "extracted_from_context"}
                }
            elif 'services' in parts or 'service' in parts:
                return {
                    "mcp_tool": "kubernetes_list_services",
                    "parameters": {"namespace": "extracted_from_context"}
                }

        elif 'describe' in parts:
            return {
                "mcp_tool": "kubernetes_describe_resource",
                "parameters": {"resource_type": "extracted", "name": "extracted"}
            }

        elif 'logs' in parts:
            return {
                "mcp_tool": "kubernetes_get_logs",
                "parameters": {"pod_name": "extracted", "namespace": "extracted"}
            }

        elif 'delete' in parts:
            return {
                "mcp_tool": "kubernetes_delete_resource",
                "parameters": {"resource_type": "extracted", "name": "extracted"},
                "warning": "Ensure destructive operations are properly guarded"
            }

        elif 'apply' in parts:
            return {
                "mcp_tool": "kubernetes_apply_manifest",
                "parameters": {"manifest": "extracted_from_file_or_stdin"}
            }

        elif 'scale' in parts:
            return {
                "mcp_tool": "kubernetes_scale_deployment",
                "parameters": {"deployment": "extracted", "replicas": "extracted"}
            }

        # Default mapping
        return {
            "mcp_tool": "kubernetes_execute_command",
            "parameters": {"command": kubectl_cmd},
            "note": "Complex command - may need custom MCP tool implementation"
        }

    def _assess_migration_complexity(self, usages: list[KubectlUsage]) -> str:
        """Assess complexity of migrating a file"""
        # High complexity indicators
        high_complexity_indicators = [
            'shell_script',
            'os_system',
            any('|' in u.line_content or '&&' in u.line_content for u in usages),
            any('delete' in u.kubectl_command or 'rm' in u.kubectl_command for u in usages if u.kubectl_command)
        ]

        if sum(high_complexity_indicators) >= 2:
            return "high"
        elif any(high_complexity_indicators):
            return "medium"
        else:
            return "low"


async def main():
    """Main function to run the kubectl usage audit"""
    auditor = KubectlUsageAuditor()

    print(f"\n{'='*60}")
    print("kubectl Usage Audit for DreamOps Codebase")
    print(f"{'='*60}\n")

    # Run the audit
    report = await auditor.find_all_kubectl_usage()

    # Display summary
    print("📊 AUDIT SUMMARY")
    print(f"{'='*40}")
    print(f"Total kubectl usages found: {report.total_usages}")
    print(f"Files affected: {len(report.files_affected)}")
    print(f"Unique kubectl commands: {len(report.unique_commands)}")

    # Display by type
    print("\n📈 Usage by Type:")
    for usage_type, count in sorted(report.by_type.items(), key=lambda x: x[1], reverse=True):
        print(f"   {usage_type}: {count}")

    # Display priority files
    print("\n🎯 Priority Files (most usages):")
    for i, file_path in enumerate(report.priority_files[:5], 1):
        rel_path = os.path.relpath(file_path, auditor.root_dir)
        usage_count = len(report.by_file[file_path])
        print(f"   {i}. {rel_path} ({usage_count} usages)")

    # Display unique commands
    print("\n🔧 Sample kubectl Commands Found:")
    for i, cmd in enumerate(list(report.unique_commands)[:10], 1):
        print(f"   {i}. {cmd[:80]}{'...' if len(cmd) > 80 else ''}")

    # Generate migration plan
    migration_plan = auditor.generate_migration_plan(report)

    print("\n📋 MIGRATION PLAN")
    print(f"{'='*40}")
    print(f"Estimated effort: {migration_plan['summary']['estimated_effort_hours']:.1f} hours")
    print(f"Files to update: {migration_plan['summary']['total_files_to_update']}")

    if migration_plan['risks']:
        print("\n⚠️  Identified Risks:")
        for risk in migration_plan['risks']:
            print(f"   - {risk}")

    # Save detailed reports
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # Save audit report
    audit_file = f"kubectl_audit_report_{timestamp}.json"
    with open(audit_file, 'w') as f:
        json.dump(report.to_dict(), f, indent=2)
    print(f"\n📄 Detailed audit report saved to: {audit_file}")

    # Save migration plan
    migration_file = f"kubectl_migration_plan_{timestamp}.json"
    with open(migration_file, 'w') as f:
        json.dump(migration_plan, f, indent=2)
    print(f"📄 Migration plan saved to: {migration_file}")

    # Generate CSV for easier review
    csv_file = f"kubectl_usages_{timestamp}.csv"
    with open(csv_file, 'w') as f:
        f.write("File,Line,Type,Command,Context\n")
        for usage in report.usages:
            rel_path = os.path.relpath(usage.file_path, auditor.root_dir)
            f.write(f'"{rel_path}",{usage.line_number},"{usage.usage_type}","{usage.kubectl_command or ""}","{usage.line_content}"\n')
    print(f"📄 CSV report saved to: {csv_file}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
