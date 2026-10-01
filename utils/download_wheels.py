"""
Download prebuilt binary wheels and sdist from GitHub Actions workflow runs.

Usage:
    uv run python utils/download_wheels.py
    uv run python utils/download_wheels.py --branch build
    uv run python utils/download_wheels.py --run-id 12345678
"""

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

DEFAULT_REPO = "connor-makowski/type_enforced"
DEFAULT_WORKFLOW = "build_wheels.yml"
DEFAULT_ARTIFACT = "dist"
DEFAULT_OUTPUT_DIR = "dist"


def _get_gh_cli_path() -> str | None:
    return shutil.which("gh")


def _get_auth_token(args_token: str | None) -> str | None:
    return (
        args_token
        or os.environ.get("GITHUB_TOKEN")
        or os.environ.get("GH_TOKEN")
    )


def _api_request(url: str, token: str | None = None) -> bytes:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "type_enforced-wheel-downloader",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise RuntimeError(
                "GitHub API request returned 401 Unauthorized. "
                "Please provide a valid GitHub token via --token or GITHUB_TOKEN."
            ) from e
        if e.code == 403:
            raise RuntimeError(
                "GitHub API request returned 403 Forbidden. "
                "Rate limit exceeded or missing authorization. "
                "Set GITHUB_TOKEN or install the GitHub CLI (`gh auth login`)."
            ) from e
        raise RuntimeError(f"GitHub API error ({e.code}): {e.reason}") from e


def _find_run_with_gh(
    repo: str, workflow: str, branch: str | None, run_id: str | None
) -> str:
    if run_id:
        return run_id

    cmd = [
        "gh",
        "run",
        "list",
        "--repo",
        repo,
        "--workflow",
        workflow,
        "--json",
        "databaseId,status,conclusion,headBranch,createdAt",
        "--limit",
        "10",
    ]
    if branch:
        cmd.extend(["--branch", branch])

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to list workflow runs with gh: {result.stderr}"
        )

    runs = json.loads(result.stdout)
    if not runs:
        branch_msg = f" on branch '{branch}'" if branch else ""
        raise RuntimeError(
            f"No workflow runs found for '{workflow}' in {repo}{branch_msg}."
        )

    for run in runs:
        if run.get("status") != "completed":
            print(
                f"Note: Latest run #{run.get('databaseId')} is still "
                f"'{run.get('status')}'. Looking for latest completed run..."
            )
            continue
        if run.get("conclusion") == "success":
            return str(run.get("databaseId"))

    # If no successful completed run, fallback to the latest run ID
    latest = runs[0]
    return str(latest.get("databaseId"))


def _download_with_gh(
    repo: str, run_id: str, artifact_name: str, output_dir: Path
) -> bool:
    print(
        f"Downloading artifact '{artifact_name}' from run #{run_id} using gh CLI..."
    )
    cmd = [
        "gh",
        "run",
        "download",
        str(run_id),
        "--repo",
        repo,
        "--name",
        artifact_name,
        "--dir",
        str(output_dir),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        # Check if artifact name is not found, attempt downloading all artifacts
        print(
            f"Artifact '{artifact_name}' not found directly. "
            "Downloading all artifacts from run..."
        )
        cmd_all = [
            "gh",
            "run",
            "download",
            str(run_id),
            "--repo",
            repo,
            "--dir",
            str(output_dir),
        ]
        result_all = subprocess.run(
            cmd_all, capture_output=True, text=True, check=False
        )
        if result_all.returncode != 0:
            raise RuntimeError(
                f"Failed to download artifacts with gh: {result_all.stderr}"
            )
    return True


def _download_with_api(
    repo: str,
    workflow: str,
    branch: str | None,
    run_id: str | None,
    artifact_name: str,
    output_dir: Path,
    token: str | None,
) -> None:
    if not token:
        print(
            "Warning: No GitHub token provided. Downloading artifacts from GitHub API "
            "requires authentication. You can set GITHUB_TOKEN or install `gh`."
        )

    if not run_id:
        url = f"https://api.github.com/repos/{repo}/actions/runs?per_page=10"
        if branch:
            url += f"&branch={branch}"
        data = json.loads(_api_request(url, token).decode("utf-8"))
        runs = data.get("workflow_runs", [])
        if not runs:
            branch_msg = f" on branch '{branch}'" if branch else ""
            raise RuntimeError(f"No workflow runs found in {repo}{branch_msg}.")

        target_run = None
        for run in runs:
            if run.get("conclusion") == "success":
                target_run = run
                break
        if not target_run:
            target_run = runs[0]

        run_id = str(target_run["id"])
        print(
            f"Found run #{run_id} ({target_run.get('head_branch')}) - "
            f"status: {target_run.get('status')}, "
            f"conclusion: {target_run.get('conclusion')}"
        )

    artifacts_url = (
        f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts"
    )
    artifacts_data = json.loads(
        _api_request(artifacts_url, token).decode("utf-8")
    )
    artifacts = artifacts_data.get("artifacts", [])

    if not artifacts:
        raise RuntimeError(f"No artifacts found in workflow run #{run_id}.")

    # Look for combined dist artifact first, or download all matching artifacts
    target_artifacts = [a for a in artifacts if a.get("name") == artifact_name]
    if not target_artifacts:
        target_artifacts = [
            a
            for a in artifacts
            if a.get("name", "").startswith("cibw-") or a.get("name") == "dist"
        ]

    if not target_artifacts:
        available = ", ".join(a.get("name", "") for a in artifacts)
        raise RuntimeError(
            f"Artifact '{artifact_name}' not found. Available: {available}"
        )

    for artifact in target_artifacts:
        name = artifact.get("name")
        download_url = artifact.get("archive_download_url")
        print(f"Downloading artifact '{name}' from {download_url}...")
        zip_bytes = _api_request(download_url, token)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            zf.extractall(output_dir)


def _flatten_output_dir(output_dir: Path) -> list[Path]:
    """Flatten any nested subdirectories into the root output directory."""
    files = []
    for item in list(output_dir.rglob("*")):
        if item.is_file() and item.parent != output_dir:
            dest = output_dir / item.name
            if not dest.exists():
                shutil.move(str(item), str(dest))
            files.append(dest)
        elif item.is_file():
            files.append(item)

    # Clean up empty directories
    for item in list(output_dir.glob("*")):
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)

    return sorted(list(output_dir.glob("*")))


def download_wheels(
    repo: str = DEFAULT_REPO,
    workflow: str = DEFAULT_WORKFLOW,
    branch: str | None = None,
    run_id: str | None = None,
    artifact_name: str = DEFAULT_ARTIFACT,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    clean: bool = True,
    token: str | None = None,
) -> None:
    out_path = Path(output_dir).resolve()
    if clean and out_path.exists():
        print(f"Cleaning existing files in {out_path}...")
        for file in out_path.glob("*"):
            if file.is_file():
                file.unlink()
            elif file.is_dir():
                shutil.rmtree(file)

    out_path.mkdir(parents=True, exist_ok=True)

    token = _get_auth_token(token)
    gh_cli = _get_gh_cli_path()

    if gh_cli:
        try:
            target_run_id = _find_run_with_gh(
                repo=repo, workflow=workflow, branch=branch, run_id=run_id
            )
            _download_with_gh(
                repo=repo,
                run_id=target_run_id,
                artifact_name=artifact_name,
                output_dir=out_path,
            )
        except Exception as e:
            print(f"GitHub CLI method encountered an issue: {e}")
            print("Attempting direct GitHub API download...")
            _download_with_api(
                repo=repo,
                workflow=workflow,
                branch=branch,
                run_id=run_id,
                artifact_name=artifact_name,
                output_dir=out_path,
                token=token,
            )
    else:
        _download_with_api(
            repo=repo,
            workflow=workflow,
            branch=branch,
            run_id=run_id,
            artifact_name=artifact_name,
            output_dir=out_path,
            token=token,
        )

    all_files = _flatten_output_dir(out_path)

    wheels = [f for f in all_files if f.name.endswith(".whl")]
    sdists = [f for f in all_files if f.name.endswith(".tar.gz")]

    print("\n" + "=" * 60)
    print(f"Artifacts successfully downloaded to: {out_path}")
    print(f"Total: {len(wheels)} wheel(s), {len(sdists)} sdist(s)")
    print("=" * 60)
    for item in all_files:
        size_kb = item.stat().st_size / 1024
        print(f"  - {item.name:<50} ({size_kb:6.1f} KB)")
    print("=" * 60)
    print("\nNext step to deploy to PyPI:")
    print("  uv run python -m twine upload dist/* --skip-existing")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download prebuilt binary wheels from GitHub Actions."
    )
    parser.add_argument(
        "--repo",
        default=DEFAULT_REPO,
        help=f"GitHub repository owner/repo (default: {DEFAULT_REPO})",
    )
    parser.add_argument(
        "--workflow",
        default=DEFAULT_WORKFLOW,
        help=f"Workflow file name (default: {DEFAULT_WORKFLOW})",
    )
    parser.add_argument(
        "--branch",
        default=None,
        help="Filter by branch name (e.g. build, main)",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Explicit workflow run ID to download from",
    )
    parser.add_argument(
        "--artifact",
        default=DEFAULT_ARTIFACT,
        help=f"Artifact name to download (default: {DEFAULT_ARTIFACT})",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Target directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--no-clean",
        action="store_false",
        dest="clean",
        help="Do not clean output directory before downloading",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="GitHub Personal Access Token (or set GITHUB_TOKEN env var)",
    )

    args = parser.parse_args()
    download_wheels(
        repo=args.repo,
        workflow=args.workflow,
        branch=args.branch,
        run_id=args.run_id,
        artifact_name=args.artifact,
        output_dir=args.output_dir,
        clean=args.clean,
        token=args.token,
    )


if __name__ == "__main__":
    main()
